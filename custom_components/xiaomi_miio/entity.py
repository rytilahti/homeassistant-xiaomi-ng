import datetime
import logging
from enum import Enum
from functools import partial
from typing import Any, TypeVar

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MODEL
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from miio import Device, DeviceException

from .const import DOMAIN

_T = TypeVar("_T", bound=DataUpdateCoordinator[Any])


_LOGGER = logging.getLogger(__name__)


class XiaomiEntity(CoordinatorEntity[_T]):
    """Representation of a base a coordinated Xiaomi Miio Entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        device: Device,
        entry: ConfigEntry,
        unique_id: str,
        coordinator: DataUpdateCoordinator,
    ):
        """Initialize the coordinated Xiaomi Miio Device."""
        super().__init__(coordinator)
        self._device = device
        self._model = entry.data[CONF_MODEL]
        self._entry = entry
        self._device_info = None
        self._device_id = device.device_id
        self._device_name = entry.title
        self._attr_unique_id = unique_id
        self._attr_available = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        extras = {}
        if self._device_info is not None:
            extras["hw_version"] = self._device_info.hardware_version
            extras["sw_version"] = self._device_info.firmware_version

        device_info = DeviceInfo(
            identifiers={(DOMAIN, self._device_id)},
            default_manufacturer="Xiaomi",
            model=self._model,
            name=self._device_name,
            **extras,
        )

        return device_info

    async def _try_command(self, mask_error, func, *args, **kwargs):
        """Call a miio device command handling error messages."""
        try:
            full_func = partial(func, *args, **kwargs)
            result = await self.hass.async_add_executor_job(full_func)

            _LOGGER.debug("Response received from miio device: %s", result)

            return True
        except DeviceException as exc:
            if self.available:
                _LOGGER.error(mask_error, exc)
                self._attr_available = False

            return False

    @classmethod
    def _extract_value_from_attribute(cls, state, attribute):
        """Extract value from state."""
        value = getattr(state, attribute)

        if isinstance(value, Enum):
            return value.value
        if isinstance(value, datetime.timedelta):
            return cls._parse_time_delta(value)
        if isinstance(value, datetime.time):
            return cls._parse_datetime_time(value)
        if isinstance(value, datetime.datetime):
            return cls._parse_datetime_datetime(value)

        if value is None:
            _LOGGER.debug("Attribute %s is None, this is unexpected", attribute)

        return value

    def get_setting(self, name: str):
        """Get setting value."""
        settings = self._device.settings()
        return self._extract_value_from_attribute(
            self.coordinator.data, settings[name].id
        )

    def set_setting(self, name: str, value):
        """Set setting to value."""
        settings = self._device.settings()
        if name not in settings:
            _LOGGER.warning("Device has no '%s'", name)
            return None

        _LOGGER.info("Going to set %s to %s", name, value)
        return settings[name].setter(value)

    @staticmethod
    def _parse_time_delta(timedelta: datetime.timedelta) -> int:
        return int(timedelta.total_seconds())

    @staticmethod
    def _parse_datetime_time(initial_time: datetime.time) -> str:
        time = datetime.datetime.now().replace(
            hour=initial_time.hour, minute=initial_time.minute, second=0, microsecond=0
        )

        if time < datetime.datetime.now():
            time += datetime.timedelta(days=1)

        return time.isoformat()

    @staticmethod
    def _parse_datetime_datetime(time: datetime.datetime) -> str:
        return time.isoformat()
