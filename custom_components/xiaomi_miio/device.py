"""Xiaomi device helper."""
import logging
from typing import TypeVar

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MODEL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from miio import (
    ActionDescriptor,
    Descriptor,
    DescriptorCollection,
    Device,
    DeviceException,
    DeviceInfo,
    PropertyDescriptor,
)
from miio.identifiers import FanId, LightId, StandardIdentifier, VacuumId

_LOGGER = logging.getLogger(__name__)


T = TypeVar("T", bound=Descriptor)


class XiaomiDevice:
    """Helper container for device accesses."""

    def __init__(
        self,
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        coordinator: DataUpdateCoordinator,
        device: Device,
    ):
        """Initialize the entity."""
        self._hass = hass
        self._config_entry = config_entry
        self._config_data = config_entry.data
        self._device: Device = device
        self._coordinator: DataUpdateCoordinator = coordinator
        self._device_info = None

    @property
    def name(self) -> str:
        return self._config_entry.title

    def _filter_standard(
        self, descriptors: DescriptorCollection[T]
    ) -> DescriptorCollection[T]:
        """Filter out standard identifiers."""
        identifier_classes = [StandardIdentifier, VacuumId, FanId, LightId]
        standard_identifiers = []
        for identifier_class in identifier_classes:
            standard_identifiers.extend(
                [identifier.value for identifier in identifier_class]
            )
        _LOGGER.debug("Got standard identifiers: %s", standard_identifiers)
        # TODO: avoid constructing a new devicecollection
        return DescriptorCollection(
            {
                descriptor.id: descriptor
                for descriptor in descriptors.values()
                if descriptor.id not in standard_identifiers
            },
            device=self._device,
        )

    def descriptors(self, skip_standard=False) -> DescriptorCollection[Descriptor]:
        """Return all available descriptors, keyed with id."""
        descriptors = self._device.descriptors()
        if skip_standard:
            descriptors = self._filter_standard(descriptors)

        return descriptors  # noqa: RET504

    def settings(self, skip_standard=False) -> DescriptorCollection[PropertyDescriptor]:
        """Return all available settings, keyed with id."""
        settings = self._device.settings()
        if skip_standard:
            settings = self._filter_standard(settings)

        return settings  # noqa: RET504

    def sensors(self, skip_standard=False) -> DescriptorCollection[PropertyDescriptor]:
        """Return all available sensors, keyed with id."""
        sensors = self._device.sensors()
        if skip_standard:
            sensors = self._filter_standard(sensors)

        return sensors  # noqa: RET504

    def actions(self, skip_standard=False) -> DescriptorCollection[ActionDescriptor]:
        """Return all available actions, keyed with id."""
        actions = self._device.actions()
        if skip_standard:
            actions = self._filter_standard(actions)

        return actions  # noqa: RET504

    def get_method_for_action(self, name: StandardIdentifier | str):
        """Return action callable by name."""
        if isinstance(name, StandardIdentifier):
            name = name.value
        return self._device.actions()[name].method

    @property
    def device(self):
        """Return the class containing all connections to the device."""
        return self._device

    @property
    def device_id(self) -> int:
        """Return the device ID as string."""
        return self._device.device_id

    @property
    def model(self) -> str:
        """Return model as configured in config entry."""
        return self._config_data[CONF_MODEL]

    @property
    def coordinator(self) -> DataUpdateCoordinator:
        return self._coordinator

    @property
    def info(self) -> DeviceInfo:
        """Return the class containing device info.

        TODO: This is misplaced and will request miIO.info from the device...
        """
        if self._device_info is None:
            try:
                self._device_info = self._device.info()
            except DeviceException:
                _LOGGER.error(
                    "Unable to query info from device, returning dummy information"
                )
                assert self.model is not None

                did_mac = f"ca:fe:{self.device_id:08x}"
                self._device_info = DeviceInfo(
                    {
                        "model": self.model,
                        "hw_ver": "dummy",
                        "fw_ver": "dummy",
                        "mac": did_mac.lower(),
                    }
                )

        return self._device_info

    def get(self, key: str | StandardIdentifier) -> PropertyDescriptor | None:
        """Return sensor/setting descriptor."""
        if isinstance(key, StandardIdentifier):
            key = key.value

        props = self._device.descriptors()
        try:
            descriptor = props[key]
        except KeyError:
            _LOGGER.error("Unable to find descriptor '%s' for %s", key, self._device)
            return None

        return descriptor

    def fetch_info(self):
        """Fetch device info."""
        self._device.info()

    def __repr__(self):
        """Return pretty device info."""
        return f"<{self.name} ({self.model} @ {self._device.ip}>"
