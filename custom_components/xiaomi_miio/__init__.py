"""Support for Xiaomi Miio."""
from __future__ import annotations

import logging
from datetime import timedelta

import async_timeout
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from miio import Device as MiioDevice
from miio import DeviceException, DeviceFactory, DeviceStatus

from .const import (
    DOMAIN,
    KEY_COORDINATOR,
    KEY_DEVICE,
)

_LOGGER = logging.getLogger(__name__)

POLLING_TIMEOUT_SEC = 10
UPDATE_INTERVAL = timedelta(seconds=15)

# List of common platforms initialized for all supported devices
COMMON_PLATFORMS = {
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
}

SWITCH_PLATFORMS: set[str] = set()
FAN_PLATFORMS = {
    Platform.FAN,
}
HUMIDIFIER_PLATFORMS = {
    Platform.HUMIDIFIER,
}
VACUUM_PLATFORMS = {
    Platform.VACUUM,
}
AIR_MONITOR_PLATFORMS = {Platform.AIR_QUALITY}


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Xiaomi Miio components from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    return await async_setup_device_entry(hass, entry)


@callback
def get_platforms(hass, config_entry):
    """Return the platforms belonging to a config_entry."""
    model = config_entry.data[CONF_MODEL]
    platforms = COMMON_PLATFORMS

    if "light" in model:
        platforms |= {Platform.LIGHT}
    if "vacuum" in model:
        platforms |= {Platform.VACUUM}
    else:
        _LOGGER.warning("Unhandled device type for: %s", model)

    return platforms


def _async_update_data_default(hass, device):
    async def update():
        """Fetch data from the device using async_add_executor_job."""

        async def _async_fetch_data() -> DeviceStatus:
            """Fetch data from the device."""
            _LOGGER.info("Going to update for %s", device)
            async with async_timeout.timeout(POLLING_TIMEOUT_SEC):
                state: DeviceStatus = await hass.async_add_executor_job(device.status)
                _LOGGER.debug("Got new state: %s", state)

                return state

        try:
            return await _async_fetch_data()
        except DeviceException as ex:
            if getattr(ex, "code", None) != -9999:
                raise UpdateFailed(ex) from ex
            _LOGGER.info("Got exception while fetching the state, trying again: %s", ex)
        # Try to fetch the data a second time after error code -9999
        try:
            return await _async_fetch_data()
        except DeviceException as ex:
            raise UpdateFailed(ex) from ex

    return update


async def async_create_miio_device_and_coordinator(
    hass: HomeAssistant, entry: ConfigEntry
) -> set[Platform]:
    """Set up a data coordinator and one miio device to service multiple entities."""
    model: str = entry.data[CONF_MODEL]
    host = entry.data[CONF_HOST]
    token = entry.data[CONF_TOKEN]
    name = entry.title
    device: MiioDevice | None = None
    update_method = _async_update_data_default
    coordinator_class: type[DataUpdateCoordinator] = DataUpdateCoordinator

    _LOGGER.debug("Initializing with host %s (token %s...)", host, token[:5])

    def _create_dev_instance():
        return DeviceFactory.create(host, token, model=model, force_generic_miot=True)

    try:
        device = await hass.async_add_executor_job(_create_dev_instance)
    except DeviceException:
        _LOGGER.warning("Tried to initialize unsupported %s, skipping", model)
        raise

    if not device.sensors() and not device.settings():
        _LOGGER.error(
            "Device %s exposes no sensors nor settings, "
            "this needs to be fixed in upstream",
            device,
        )
        return set()

    # Create update miio device and coordinator
    coordinator = coordinator_class(
        hass,
        _LOGGER,
        name=name,
        update_method=update_method(hass, device),
        update_interval=UPDATE_INTERVAL,
    )
    _LOGGER.info("Created coordinator %s for %s", coordinator, device)
    hass.data[DOMAIN][entry.entry_id] = {
        KEY_DEVICE: device,
        KEY_COORDINATOR: coordinator,
    }

    # Trigger first data fetch
    await coordinator.async_config_entry_first_refresh()

    return get_platforms(hass, entry)


async def async_setup_device_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up the Xiaomi Miio device component from a config entry."""
    platforms = await async_create_miio_device_and_coordinator(hass, entry)

    if not platforms:
        _LOGGER.error("Got no platforms for %s, bailing out", entry)
        return False

    _LOGGER.info("Going to initialize platforms: %s", platforms)

    entry.async_on_unload(entry.add_update_listener(update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    platforms = get_platforms(hass, config_entry)

    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, platforms
    )

    if unload_ok:
        hass.data[DOMAIN].pop(config_entry.entry_id)

    return unload_ok


async def update_listener(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Handle options update."""
    _LOGGER.debug("on_unload called, reloading config entry")
    await hass.config_entries.async_reload(config_entry.entry_id)
