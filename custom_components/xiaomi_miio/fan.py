"""Support for Xiaomi Philips Lights."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.fan import (
    FanEntity,
    FanEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from miio.descriptors import EnumSettingDescriptor
from miio.identifiers import FanId

from .const import DOMAIN, KEY_DEVICE
from .device import XiaomiDevice
from .entity import XiaomiEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Xiaomi light from a config entry."""
    entities: list[FanEntity] = []

    device: XiaomiDevice = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]
    _LOGGER.info("Setting up fan platform for %s", device)

    entity = XiaomiFan(device)
    entities.append(entity)

    async_add_entities(entities, update_before_add=True)


class XiaomiFan(XiaomiEntity, FanEntity):
    """Representation of Xiaomi Light."""

    def __init__(self, device):
        """Initialize the light device."""
        super().__init__(device)

        self._available = False
        self._state = None

    @property
    def supported_features(self) -> FanEntityFeature:
        """Return supported features."""
        features = FanEntityFeature(0)
        if self._device.get(FanId.Speed):
            features |= FanEntityFeature.SET_SPEED
        if self._device.get(FanId.Oscillate):
            features |= FanEntityFeature.OSCILLATE
        # TODO: disabled in favor of more generic angle option
        # if self._device.get(FanId.Angle):
        #     features |= FanEntityFeature.DIRECTION
        if self._device.get(FanId.Preset):
            features |= FanEntityFeature.PRESET_MODE

        return features

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Turn the fan on."""
        if (
            percentage is not None
            and self.supported_features & FanEntityFeature.SET_SPEED
        ):
            await self._try_command(
                "Turning the fan percentage failed.",
                self.set_setting,
                FanId.Speed,
                percentage,
            )

        if (
            preset_mode is not None
            and self.supported_features & FanEntityFeature.PRESET_MODE
        ):
            await self._try_command(
                "Turning the fan preset mode failed.",
                self.set_setting,
                FanId.Preset,
                preset_mode,
            )

        await self._try_command(
            "Turning the fan on failed.", self.set_setting, FanId.On, True
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the fan off."""
        await self._try_command(
            "Turning the fan off failed.", self.set_setting, FanId.On, False
        )

    async def async_set_percentage(self, percentage: int) -> None:
        """Set fan speed."""
        # TODO: devdocs: Manually setting a speed must disable any set preset mode.
        #  If it is possible to set a percentage speed manually without disabling
        #  the preset mode, create a switch or service to represent the mode.
        if FanEntityFeature.SET_SPEED & self.supported_features:
            return await self._try_command(
                "Setting percentage failed.", self.set_setting, FanId.Speed, percentage
            )

        return None

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set preset mode."""
        if FanEntityFeature.PRESET_MODE & self.supported_features:
            return await self._try_command(
                "Setting preset mode failed.",
                self.set_setting,
                FanId.Preset,
                preset_mode,
            )

        return None

    async def async_set_direction(self, direction: str) -> None:
        """Set direction."""
        if FanEntityFeature.DIRECTION & self.supported_features:
            return await self._try_command(
                "Setting direction failed.", self.set_setting, FanId.Angle, direction
            )

        return None

    async def async_oscillate(self, oscillating: bool) -> None:
        """Set oscillating."""
        if FanEntityFeature.OSCILLATE & self.supported_features:
            return await self._try_command(
                "Setting oscillate failed.",
                self.set_setting,
                FanId.Oscillate,
                oscillating,
            )

        return None

    @callback
    def _handle_coordinator_update(self):
        """Handle updated data from the coordinator."""
        self._attr_is_on = self.get_value(FanId.On)
        self._attr_percentage = self.get_value(FanId.Speed)
        self._attr_oscillating = self.get_value(FanId.Oscillate)
        # TODO: is speed count anymore relevant, shouldn't that be deprecated by now?
        # TODO: update the homeassistant docs accordingly
        # self._attr_speed_count = self.get_value(FanId.SpeedCount)

        # TODO: find a better way to work on enums
        preset = self.get_descriptor(FanId.Preset)
        assert isinstance(preset, EnumSettingDescriptor)

        self._attr_preset_mode = preset.choices(self.get_value(FanId.Preset)).name
        self._attr_preset_modes = list(preset.choices._member_map_.keys())

        # TODO: find a better way to work on enums
        angles = self.get_descriptor(FanId.Angle)
        assert isinstance(angles, EnumSettingDescriptor)
        list(angles.choices._member_map_.keys())
        self._attr_current_direction = angles.choices(self.get_value(FanId.Angle)).name

        super()._handle_coordinator_update()
