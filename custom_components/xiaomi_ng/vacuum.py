"""Support for the Xiaomi vacuum cleaner robot."""
from __future__ import annotations

from enum import Enum
import logging
from typing import Any

from miio.interfaces.vacuuminterface import VacuumState

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
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, KEY_COORDINATOR, KEY_DEVICE
from .device import XiaomiMiioEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Xiaomi vacuum cleaner robot from a config entry."""
    entities = []

    unique_id = config_entry.unique_id

    vacuum = XiaomiVacuum(
        hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE],
        config_entry,
        unique_id,
        hass.data[DOMAIN][config_entry.entry_id][KEY_COORDINATOR],
    )
    entities.append(vacuum)

    # TODO: add support for custom services (based on actions taking inputs) when implemented in python-miio

    async_add_entities(entities, update_before_add=True)


class XiaomiVacuum(
    XiaomiMiioEntity,
    StateVacuumEntity,
):
    """Representation of a Xiaomi Vacuum cleaner robot."""

    _attr_supported_features = (
        VacuumEntityFeature.STATE
        | VacuumEntityFeature.PAUSE
        | VacuumEntityFeature.STOP
        | VacuumEntityFeature.RETURN_HOME
        | VacuumEntityFeature.FAN_SPEED
        | VacuumEntityFeature.SEND_COMMAND
        | VacuumEntityFeature.LOCATE
        | VacuumEntityFeature.BATTERY
        | VacuumEntityFeature.CLEAN_SPOT
        | VacuumEntityFeature.START
    )

    def __init__(
        self,
        device,
        entry,
        unique_id,
        coordinator: DataUpdateCoordinator,
    ):
        """Initialize the Xiaomi vacuum cleaner robot handler."""
        super().__init__(device, entry, unique_id, coordinator)
        self._fan_speed_presets = device.fan_speed_presets()
        self._fan_speed_presets_reverse = {
            speed: name for name, speed in self._fan_speed_presets.items()
        }
        self._state: str | None = None

    async def async_added_to_hass(self) -> None:
        """Run when entity is about to be added to hass."""
        await super().async_added_to_hass()
        self._handle_coordinator_update()

    @property
    def state(self) -> str | None:
        """Return the status of the vacuum cleaner."""
        return self._state

    @property
    def battery_level(self) -> int:
        """Return the battery level of the vacuum cleaner."""
        return self.coordinator.data.battery

    @property
    def fan_speed(self) -> str:
        """Return the fan speed of the vacuum cleaner."""
        speed = self.coordinator.data.fanspeed
        if isinstance(speed, Enum):
            speed = speed.value
        _LOGGER.debug(
            "Got fan speed %s, looking for value from %s",
            speed,
            self._fan_speed_presets_reverse,
        )
        return self._fan_speed_presets_reverse.get(speed, "Custom")

    @property
    def fan_speed_list(self) -> list[str]:
        """Get the list of available fan speed steps of the vacuum cleaner."""
        return list(self._fan_speed_presets)

    async def async_start(self) -> None:
        """Start or resume the cleaning task."""
        await self._try_command("Unable to start the vacuum: %s", self._device.start)

    async def async_pause(self) -> None:
        """Pause the cleaning task."""
        await self._try_command("Unable to set start/pause: %s", self._device.pause)

    async def async_stop(self, **kwargs: Any) -> None:
        """Stop the vacuum cleaner."""
        await self._try_command("Unable to stop: %s", self._device.stop)

    async def async_set_fan_speed(self, fan_speed: str, **kwargs: Any) -> None:
        """Set fan speed."""
        # TODO: I don't see any reason this not being simply the following
        # fan_speed = self._fan_speed_presets.get(fan_speed, int(fan_speed))

        _LOGGER.info("Trying to set fan speed to %s", fan_speed)
        if fan_speed in self._fan_speed_presets:
            _LOGGER.info("Found fan speed from presets")
            fan_speed_int = self._fan_speed_presets[fan_speed]
        else:
            _LOGGER.info(
                "Fan speed not found in presets, trying to convert to int and use it"
            )
            try:
                fan_speed_int = int(fan_speed)
            except ValueError as exc:
                _LOGGER.error(
                    "Fan speed step not recognized (%s). Valid speeds are: %s",
                    exc,
                    self.fan_speed_list,
                )
                return
        await self._try_command(
            "Unable to set fan speed: %s", self._device.set_fan_speed, fan_speed_int
        )

    async def async_return_to_base(self, **kwargs: Any) -> None:
        """Set the vacuum cleaner to return to the dock."""
        await self._try_command("Unable to return home: %s", self._device.home)

    async def async_clean_spot(self, **kwargs: Any) -> None:
        """Perform a spot clean-up."""
        await self._try_command(
            "Unable to start the vacuum for a spot clean-up: %s", self._device.spot
        )

    async def async_locate(self, **kwargs: Any) -> None:
        """Locate the vacuum cleaner."""
        await self._try_command("Unable to locate the botvac: %s", self._device.find)

    async def async_send_command(
        self, command: str, params: dict | list | None = None, **kwargs: Any
    ) -> None:
        """Send raw command."""
        await self._try_command(
            "Unable to send command to the vacuum: %s",
            self._device.raw_command,
            command,
            params,
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle coordinator update.

        This will convert upstream state to homeassistant constant.
        """
        vacstate = self.coordinator.data.vacuum_state
        VACUUMSTATE_TO_HASS = {
            VacuumState.Error: STATE_ERROR,
            VacuumState.Cleaning: STATE_CLEANING,
            VacuumState.Idle: STATE_IDLE,
            VacuumState.Docked: STATE_DOCKED,
            VacuumState.Returning: STATE_RETURNING,
            VacuumState.Paused: STATE_PAUSED,
        }
        try:
            self._state = VACUUMSTATE_TO_HASS.get(vacstate)
        except KeyError:
            _LOGGER.error("Unknown vacuum state: %s", vacstate)
            self._state = None

        super()._handle_coordinator_update()
