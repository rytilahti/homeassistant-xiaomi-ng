"""Support for the Xiaomi vacuum cleaner robot."""

from __future__ import annotations

import logging
from functools import partial
from typing import Any, cast

from homeassistant.components.vacuum import (
    STATE_CLEANING,
    STATE_DOCKED,
    STATE_ERROR,
    STATE_IDLE,
    STATE_PAUSED,
    STATE_RETURNING,
    StateVacuumEntity,
    VacuumEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from miio.descriptors import Descriptor, EnumDescriptor
from miio.identifiers import VacuumId, VacuumState

from .const import DOMAIN, KEY_DEVICE
from .device import XiaomiDevice
from .entity import XiaomiEntity

_LOGGER = logging.getLogger(__name__)

VACUUMSTATE_TO_HASS = {
    VacuumState.Error: STATE_ERROR,
    VacuumState.Cleaning: STATE_CLEANING,
    VacuumState.Idle: STATE_IDLE,
    VacuumState.Docked: STATE_DOCKED,
    VacuumState.Returning: STATE_RETURNING,
    VacuumState.Paused: STATE_PAUSED,
    VacuumState.Unknown: STATE_ERROR,  # assume unknowns are errors
}


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Xiaomi vacuum cleaner robot from a config entry."""
    entities = []

    vacuum = XiaomiVacuum(hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE])
    entities.append(vacuum)

    async_add_entities(entities, update_before_add=True)


class XiaomiVacuum(
    XiaomiEntity,
    StateVacuumEntity,
):
    """Representation of a Xiaomi Vacuum cleaner robot."""

    def __init__(
        self,
        device: XiaomiDevice,
        descriptor: Descriptor | None = None,  # main devices have no descriptor
    ):
        """Initialize the Xiaomi vacuum cleaner robot handler."""
        super().__init__(device)
        self._features: VacuumEntityFeature | None = None
        # TODO: ugly hack
        self._fan_speeds = self._fan_speeds_name_to_enum = {}
        if self.supported_features & VacuumEntityFeature.FAN_SPEED:
            fanspeeds_desc = cast(
                EnumDescriptor, self._device.get(VacuumId.FanSpeedPreset)
            )
            fanspeeds = fanspeeds_desc.choices
            self._fan_speeds = {choice.value: choice.name for choice in fanspeeds}
            self._attr_fan_speed_list = list(self._fan_speeds.values())
            self._fan_speeds_name_to_enum = {
                choice.name: choice for choice in fanspeeds
            }

    @property
    def supported_features(self) -> VacuumEntityFeature:
        """Flag supported features."""
        if self._features is not None:
            return self._features

        features: VacuumEntityFeature = VacuumEntityFeature(0)
        if self._device.get(VacuumId.State):
            features |= VacuumEntityFeature.STATE
        if self._device.get(VacuumId.Start):
            features |= VacuumEntityFeature.START
        if self._device.get(VacuumId.Stop):
            features |= VacuumEntityFeature.STOP
        if self._device.get(VacuumId.Pause):
            features |= VacuumEntityFeature.PAUSE
        if self._device.get(VacuumId.ReturnHome):
            features |= VacuumEntityFeature.RETURN_HOME
        if self._device.get(VacuumId.Spot):
            features |= VacuumEntityFeature.CLEAN_SPOT
        if self._device.get(VacuumId.FanSpeedPreset):
            features |= VacuumEntityFeature.FAN_SPEED
        if self._device.get(VacuumId.Locate):
            features |= VacuumEntityFeature.LOCATE
        if self._device.get(VacuumId.Battery):
            features |= VacuumEntityFeature.BATTERY

        self._features = features

        return features

    async def async_added_to_hass(self) -> None:
        """Run when entity is about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    async def async_start(self) -> None:
        """Start or resume the cleaning task."""
        await self._try_command(
            "Unable to start the vacuum: %s",
            self._device.get_method_for_action(VacuumId.Start),
        )

    async def async_pause(self) -> None:
        """Pause the cleaning task."""
        await self._try_command(
            "Unable to set start/pause: %s",
            self._device.get_method_for_action(VacuumId.Pause),
        )

    async def async_stop(self, **kwargs: Any) -> None:
        """Stop the vacuum cleaner."""
        await self._try_command(
            "Unable to stop: %s", self._device.get_method_for_action(VacuumId.Stop)
        )

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """Set fan speed."""
        await self._try_command(
            "Unable to set fan speed: %s",
            partial(self.set_property, VacuumId.FanSpeedPreset),
            fan_speed,
        )

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Set the vacuum cleaner to return to the dock."""
        await self._try_command(
            "Unable to return home: %s",
            self._device.get_method_for_action(VacuumId.ReturnHome),
        )

    async def async_clean_spot(self, **kwargs: Any) -> None:
        """Perform a spot clean-up."""
        await self._try_command(
            "Unable to start the vacuum for a spot clean-up: %s",
            self._device.get_method_for_action(VacuumId.Spot),
        )

    async def async_locate(self, **kwargs: Any) -> None:
        """Locate the vacuum cleaner."""
        await self._try_command(
            "Unable to locate the botvac: %s",
            self._device.get_method_for_action(VacuumId.Locate),
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle coordinator update.

        This will convert upstream state to homeassistant constant.
        """
        if self.supported_features & VacuumEntityFeature.BATTERY:
            self._attr_battery_level = self.get_value(VacuumId.Battery)
        if self.supported_features & VacuumEntityFeature.FAN_SPEED:
            self._attr_fan_speed = self._fan_speeds.get(
                self.get_value(VacuumId.FanSpeedPreset), "Custom"
            )
        if self.supported_features & VacuumEntityFeature.STATE:
            # TODO: Sensor is using type instead of choices for enum types.
            # TODO: device.get to access the descriptor should be renamed.
            state_desc = self._device.get(VacuumId.State)
            # TODO: hack below to make mypy happy until this gets cleaned up
            assert state_desc is not None  # noqa: S101
            vacstate = state_desc.type(self.get_value(VacuumId.State))

            try:
                self._attr_state = VACUUMSTATE_TO_HASS.get(vacstate)
            except KeyError:
                _LOGGER.error("Unknown vacuum state: %s", vacstate)
                self._attr_state = None

        super()._handle_coordinator_update()
