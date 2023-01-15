"""Motor speed support for Xiaomi Mi Air Humidifier."""
from __future__ import annotations

import logging

from miio.descriptors import SettingType

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KEY_COORDINATOR, KEY_DEVICE
from .ng_number import XiaomiNumber

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Selectors from a config entry."""
    entities = []

    device = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]
    coordinator = hass.data[DOMAIN][config_entry.entry_id][KEY_COORDINATOR]

    _LOGGER.info("Going to setup number for %s", device)

    # Handle switches defined by the backing class.
    for setting in device.settings().values():
        if setting.type == SettingType.Number:
            _LOGGER.debug("Adding new number setting: %s", setting)
            entities.append(XiaomiNumber(device, setting, config_entry, coordinator))

    async_add_entities(entities)
