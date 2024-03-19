"""Common entity base for xiaomi_miio."""

import datetime
import logging
from enum import Enum
from functools import partial
from typing import Any, TypeVar, cast

from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from miio import DeviceException
from miio.descriptors import AccessFlags, Descriptor, EnumDescriptor, PropertyConstraint
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
        self._attr_unique_id = str(device.device_id)

        self._status_attribute = None
        self._name = None

        self._descriptor = descriptor
        if descriptor is not None:
            self._attr_unique_id += f"_{descriptor.id}"
            self._name = descriptor.name
            self._access: AccessFlags = descriptor.access
            self._status_attribute = descriptor.status_attribute

            _LOGGER.debug(
                f"Creating entity: {self._attr_unique_id=} {self._name=} "
                f"{self._access=} {self._status_attribute=} (for: {self._descriptor=})"
            )

        self._attr_available = True

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        extras = {}
        if self._device.info is not None:
            extras["hw_version"] = self._device.info.hardware_version
            extras["sw_version"] = self._device.info.firmware_version
            extras["connections"] = {
                (dr.CONNECTION_NETWORK_MAC, self._device.info.mac_address)
            }

        return DeviceInfo(
            identifiers={(DOMAIN, self._device.device_id)},
            manufacturer="Xiaomi",
            model=self._device.model,
            name=self._device.name,
            **extras,
        )

    async def _try_command(self, mask_error, func, *args, **kwargs):
        """Call a miio device command and handle error messages."""
        try:
            full_func = partial(func, *args, **kwargs)
            _LOGGER.info("Calling %s with %s %s", func, args, kwargs)
            result = await self.hass.async_add_executor_job(full_func)

            _LOGGER.info("Device responded with: %s", result)

            return True
        except DeviceException as exc:
            if self.available:
                _LOGGER.error(mask_error, exc)
                self._attr_available = False

            return False

    def _extract_value_from_attribute(self, state, attribute):
        """Extract value from state."""
        # Write-only properties cannot be read, but not all entities have a descriptor
        if (
            self._descriptor is not None
            and AccessFlags.Read not in self._descriptor.access
        ):
            return None

        try:
            value = getattr(state, attribute)
        except KeyError:
            _LOGGER.error(
                "Unable to find '%s' from %r, this is a bug", attribute, dir(state)
            )
            return None

        if isinstance(value, Enum):
            return value.value
        if isinstance(value, datetime.timedelta):
            return XiaomiEntity._parse_time_delta(value)
        if isinstance(value, datetime.time):
            return XiaomiEntity._parse_datetime_time(value)
        if isinstance(value, datetime.datetime):
            return XiaomiEntity._parse_datetime_datetime(value)

        if value is None:
            _LOGGER.debug("Attribute %s is None, this is unexpected", attribute)

        return value

    def get_descriptor(self, name: str | StandardIdentifier) -> Descriptor | None:
        """Get python-miio descriptor."""
        if isinstance(name, StandardIdentifier):
            name = name.value

        return self._device.descriptors().get(name, None)

    def get_value(self, name: str | StandardIdentifier):
        """Get setting/sensor value."""
        descriptor = self.get_descriptor(name)

        if descriptor is None:
            _LOGGER.error(
                "Unable to find descriptor with name %s for %s", name, self._device
            )
            return None

        if AccessFlags.Read not in descriptor.access:
            _LOGGER.debug("Tried to read %s, but it is not readable", descriptor)
            return None

        try:
            return self._extract_value_from_attribute(
                self.coordinator.data, descriptor.status_attribute
            )
        except Exception:  # noqa: E722
            _LOGGER.error("Device has no '%s': %s", name)
            return None

    def set_property(self, name: StandardIdentifier | str, value):
        """Set setting to value."""
        if isinstance(name, StandardIdentifier):
            name = name.value
        settings = self._device.settings()
        if name not in settings:
            _LOGGER.warning("Device has no '%s', available: %s", name, settings.keys())
            return None

        descriptor = settings[name]
        if descriptor.constraint == PropertyConstraint.Choice:
            descriptor = cast(EnumDescriptor, descriptor)
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
