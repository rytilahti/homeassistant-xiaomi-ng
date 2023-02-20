import datetime
import logging
from enum import Enum
from functools import partial
from typing import Any, TypeVar, Optional, cast

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from miio import DeviceException
from miio.descriptors import Descriptor, SettingType, EnumSettingDescriptor
from miio.identifiers import StandardIdentifier

from .const import DOMAIN
from .device import XiaomiDevice

_T = TypeVar("_T", bound=DataUpdateCoordinator[Any])


_LOGGER = logging.getLogger(__name__)


class XiaomiEntity(CoordinatorEntity[_T]):
    """Representation of a base a coordinated Xiaomi Miio Entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        device: XiaomiDevice,
        descriptor: Descriptor | None = None,  # main devices have no descriptor
    ):
        """Initialize the coordinated Xiaomi Miio Device."""
        super().__init__(device.coordinator)
        self._device = device
        self._model = device.model
        self._attr_unique_id = device.device_id
        if descriptor is not None:
            self._attr_unique_id += f"_{descriptor.id}"
        self._attr_available = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        extras = {}
        if self._device.info is not None:
            extras["hw_version"] = self._device.info.hardware_version
            extras["sw_version"] = self._device.info.firmware_version

        return DeviceInfo(
            identifiers={(DOMAIN, self._device.device_id)},
            default_manufacturer="Xiaomi",
            model=self._device.model,
            name=self._device.name,
            **extras,
        )

    async def _try_command(self, mask_error, func, *args, **kwargs):
        """Call a miio device command handling error messages."""
        try:
            full_func = partial(func, *args, **kwargs)
            _LOGGER.info("Calling %s with %s %s", full_func, args, kwargs)
            result = await self.hass.async_add_executor_job(full_func)

            _LOGGER.info("Response received from miio device: %s", result)

            return True
        except DeviceException as exc:
            if self.available:
                _LOGGER.error(mask_error, exc)
                self._attr_available = False

            return False

    @classmethod
    def _extract_value_from_attribute(cls, state, attribute):
        """Extract value from state."""
        try:
            value = getattr(state, attribute)
        except:
            _LOGGER.error("Unable to read attribute %s from %s", attribute, state)
            return None

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

    def get_descriptor(self, name: str | StandardIdentifier) -> Optional[Descriptor]:
        """Get python-miio descriptor."""
        if isinstance(name, StandardIdentifier):
            name = name.value

        settings = self._device.settings()
        if name in settings:
            return settings[name]

        sensors = self._device.sensors()
        if name in sensors:
            return sensors[name]

        return None


    def get_value(self, name: str | StandardIdentifier):
        """Get setting/sensor value."""
        descriptor = self.get_descriptor(name)
        if descriptor is None:
            _LOGGER.error("Unable to find descriptor with name %s", name)
            return None

        if Descriptor.Access.Read not in descriptor.access:
            _LOGGER.debug("Tried to read %s, but it is not readable", name)
            return None

        try:
            return self._extract_value_from_attribute(self.coordinator.data, descriptor.property)
        except:
            _LOGGER.error("Device has no '%s'", name)
            return None

    def set_setting(self, name: StandardIdentifier | str, value):
        """Set setting to value."""
        if isinstance(name, StandardIdentifier):
            name = name.value
        settings = self._device.settings()
        if name not in settings:
            _LOGGER.warning("Device has no '%s', available: %s", name, settings.keys())
            breakpoint()
            return None

        descriptor = settings[name]
        # TODO: this is not optimal.
        if descriptor.setting_type == SettingType.Enum:
            descriptor = cast(EnumSettingDescriptor, descriptor)
            value = descriptor.choices[value].value

        _LOGGER.info("Going to set %s to %s", name, value)
        return descriptor.setter(value)

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
