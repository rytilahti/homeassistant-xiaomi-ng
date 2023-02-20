"""Diagnostics support for Xiaomi Miio."""
from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_DEVICE_ID, CONF_MAC, CONF_TOKEN, CONF_UNIQUE_ID
from homeassistant.core import HomeAssistant
from miio import DeviceStatus

from .const import CONF_CLOUD_PASSWORD, CONF_CLOUD_USERNAME, DOMAIN, KEY_DEVICE
from .device import XiaomiDevice


TO_REDACT = {
    CONF_CLOUD_PASSWORD,
    CONF_CLOUD_USERNAME,
    CONF_MAC,  # TODO: old unique id
    CONF_TOKEN,
    CONF_UNIQUE_ID,
    CONF_DEVICE_ID,
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    diagnostics_data: dict[str, Any] = {
        "config_entry": async_redact_data(config_entry.as_dict(), TO_REDACT)
    }

    # not every device uses DataUpdateCoordinator
    device: XiaomiDevice = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]
    coordinator = device.coordinator
    data: DeviceStatus = coordinator.data
    raw_data: dict[str, Any] = data.data
    # TODO: raw data is the plain device response, we should probably also include the parsed data
    diagnostics_data["raw_data"] = async_redact_data(raw_data, TO_REDACT)

    return diagnostics_data
