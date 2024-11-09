"""Support for Xiaomi Miio."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_TOKEN, Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from miio import Device as MiioDevice
from miio import DeviceException, DeviceFactory, InvalidTokenException

from .const import (
    CONF_USE_GENERIC,
    DOMAIN,
)
from .coordinator import XiaomiDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


COMMON_PLATFORMS = {
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.SWITCH,
}

type XiaomiConfigEntry = ConfigEntry[XiaomiData]


@dataclass(slots=True)
class XiaomiData:
    """Data for the tplink integration."""

    coordinator: XiaomiDataUpdateCoordinator
    device: MiioDevice
    model: str
    host: str
    token: str
    use_generic: bool


async def async_setup_entry(hass: HomeAssistant, entry: XiaomiConfigEntry) -> bool:
    """Set up the Xiaomi Miio components from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    try:
        return bool(await async_setup_device_entry(hass, entry))
    except InvalidTokenException as ex:
        raise ConfigEntryAuthFailed() from ex
    except DeviceException as ex:
        _LOGGER.error("Unable to setup entry, requesting reauth: %s", ex, exc_info=ex)
        raise ConfigEntryNotReady("Invalid token") from ex


@callback
def get_platforms(hass, config_entry: XiaomiConfigEntry):
    """Return the platforms belonging to a config_entry."""
    model = config_entry.runtime_data.model
    platforms = COMMON_PLATFORMS.copy()

    # TODO: convert to device_type
    if "light" in model:
        _LOGGER.info("Got light for %s", model)
        platforms |= {Platform.LIGHT}
    elif "vacuum" in model:
        platforms |= {Platform.VACUUM}
        _LOGGER.info("Got vacuum for %s", model)
    elif "fan" in model:
        platforms |= {Platform.FAN}
        _LOGGER.info("Got fan for %s", model)
    else:
        _LOGGER.warning("Unhandled device type for: %s", model)

    return platforms


async def async_create_miio_device_and_coordinator(
    hass: HomeAssistant, entry: XiaomiConfigEntry
) -> set[Platform]:
    """Set up a data coordinator and one miio device to service multiple entities."""
    model = entry.data[CONF_MODEL]
    host = entry.data[CONF_HOST]
    token = entry.data[CONF_TOKEN]
    use_generic = entry.data[CONF_USE_GENERIC]

    _LOGGER.debug("Initializing with host %s (token %s...)", host, token[:5])

    def _create_dev_instance() -> MiioDevice:
        return DeviceFactory.create(
            host, token, model=model, force_generic_miot=use_generic
        )

    try:
        device = await hass.async_add_executor_job(_create_dev_instance)
    except DeviceException:
        _LOGGER.warning("Tried to initialize unsupported %s, skipping", model)
        raise

    # TODO: create a device.py that handles all device specific logic
    try:
        info = await hass.async_add_executor_job(device.info)
        _LOGGER.warning("Got device info: %s", info)
    except DeviceException as ex:
        _LOGGER.warning("Unable to fetch device info for %s", device)
        if model is None:
            raise ConfigEntryAuthFailed(
                "Unable to fetch device info, you can force model"
            ) from ex
        # raise ConfigEntryNotReady from ex

    # TODO: this should not require I/O, and should be fixed in python-miio
    descriptors = await hass.async_add_executor_job(device.descriptors)
    if not descriptors:
        _LOGGER.error(
            "Device %s exposes no sensors nor settings, "
            "this needs to be fixed in upstream, open a pull request to python-miio",
            device,
        )
        return set()

    # Import XiaomiDevice here to avoid circular import
    from .device import XiaomiDevice

    # Create update miio device and coordinator
    coordinator = XiaomiDataUpdateCoordinator(hass, device)
    dev = XiaomiDevice(hass, entry, coordinator, device)

    _LOGGER.info("Created coordinator for %s %s", device, entry.entry_id)
    entry.runtime_data = XiaomiData(coordinator, dev, model, host, token, use_generic)

    # Trigger first data fetch
    await coordinator.async_config_entry_first_refresh()

    return get_platforms(hass, entry)


async def async_setup_device_entry(
    hass: HomeAssistant, entry: XiaomiConfigEntry
) -> bool:
    """Set up the Xiaomi Miio device component from a config entry."""
    platforms = await async_create_miio_device_and_coordinator(hass, entry)

    if not platforms:
        _LOGGER.error("Got no platforms for %s, bailing out", entry)
        return False

    _LOGGER.info("Going to initialize platforms for %s: %s", entry.title, platforms)

    entry.async_on_unload(entry.add_update_listener(handle_update_options))

    await hass.config_entries.async_forward_entry_setups(entry, platforms)

    return True


async def async_unload_entry(
    hass: HomeAssistant, config_entry: XiaomiConfigEntry
) -> bool:
    """Unload a config entry."""
    _LOGGER.warning("Unloading entry %s", config_entry)
    platforms = get_platforms(hass, config_entry)

    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, platforms
    )

    return unload_ok


async def handle_update_options(
    hass: HomeAssistant, config_entry: XiaomiConfigEntry
) -> None:
    """Handle options update."""
    _LOGGER.debug("on_unload called, reloading config entry")
    await hass.config_entries.async_reload(config_entry.entry_id)
