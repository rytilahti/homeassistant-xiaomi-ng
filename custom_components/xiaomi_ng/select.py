"""Support led_brightness for Mi Air Humidifier."""
from __future__ import annotations

import logging

from miio.descriptors import SettingType

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_DEVICE, CONF_FLOW_TYPE, DOMAIN, KEY_COORDINATOR, KEY_DEVICE
from .ng_select import XiaomiSelect

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Selectors from a config entry."""
    if not config_entry.data[CONF_FLOW_TYPE] == CONF_DEVICE:
        return

    entities = []
    device = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]
    coordinator = hass.data[DOMAIN][config_entry.entry_id][KEY_COORDINATOR]

    for setting in device.settings().values():
        if setting.type == SettingType.Enum:
            _LOGGER.debug("Adding new select: %s", setting)
            entities.append(XiaomiSelect(device, setting, config_entry, coordinator))

    async_add_entities(entities)
