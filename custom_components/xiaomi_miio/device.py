"""Xiaomi device helper."""
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_MODEL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from miio import Device, DeviceInfo
from miio.descriptors import (
    ActionDescriptor,
    Descriptor,
    SensorDescriptor,
    SettingDescriptor,
)
from miio.identifiers import FanId, StandardIdentifier, VacuumId

_LOGGER = logging.getLogger(__name__)


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
        self._device_info: DeviceInfo | None = None

    @property
    def name(self) -> str:
        return self._config_entry.title

    def _filter_standard(self, descriptors) -> dict[str, Descriptor]:
        """Filter out standard identifiers."""
        identifier_classes = [StandardIdentifier, VacuumId, FanId]
        standard_identifiers = []
        for identifier_class in identifier_classes:
            standard_identifiers.extend(
                [identifier.value for identifier in identifier_class]
            )
        _LOGGER.error("Got standard identifiers: %s", standard_identifiers)
        return {
            key: value
            for key, value in descriptors.items()
            if key not in standard_identifiers
        }

    def settings(self, skip_standard=False) -> dict[str, SettingDescriptor]:
        """Return all available settings, keyed with id."""
        settings = self._device.settings()
        if skip_standard:
            settings = self._filter_standard(settings)
        return {setting.id: setting for name, setting in settings.items()}

    def sensors(self, skip_standard=False) -> dict[str, SensorDescriptor]:
        """Return all available sensors, keyed with id."""
        sensors = self._device.sensors()
        if skip_standard:
            sensors = self._filter_standard(sensors)
        return {sensor.id: sensor for name, sensor in sensors.items()}

    def actions(self, skip_standard=False) -> dict[str, ActionDescriptor]:
        """Return all available actions, keyed with id."""
        actions = self._device.actions()
        if skip_standard:
            actions = self._filter_standard(actions)
        return {action.id: action for name, action in actions.items()}

    def action(self, name: StandardIdentifier | str):
        """Return action callable by name."""
        if isinstance(name, StandardIdentifier):
            name = name.value
        return self._device.actions()[name].method

    @property
    def device(self):
        """Return the class containing all connections to the device."""
        return self._device

    @property
    def device_id(self) -> str:
        """Return the device ID as string."""
        return str(self._device.device_id)

    @property
    def model(self) -> str:
        """Return model as configured in config entry."""
        return self._config_data[CONF_MODEL]

    @property
    def detected_model(self) -> str | None:
        assert self._device_info is not None
        return self._device_info.model

    @property
    def coordinator(self) -> DataUpdateCoordinator:
        return self._coordinator

    @property
    def info(self) -> DeviceInfo:
        """Return the class containing device info."""
        return self._device_info

    def get(self, key: str | StandardIdentifier):
        """Return sensor/setting descriptor."""
        if isinstance(key, StandardIdentifier):
            key = key.value
        if key in self.sensors():
            return self.sensors()[key]
        if key in self.settings():
            return self.settings()[key]

        _LOGGER.debug("Unable to find identifier: %s", key)
        return None

    def fetch_info(self):
        """Fetch device info."""
        self._device.info()

    def __repr__(self):
        """Return pretty device info."""
        return f"<{self.name} ({self.model} @ {self._device.ip}>"
