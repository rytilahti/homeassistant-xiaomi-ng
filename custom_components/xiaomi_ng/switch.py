"""Support for Xiaomi Smart WiFi Socket and Smart Power Strip."""
from __future__ import annotations

import logging

from miio.descriptors import SettingType

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, KEY_COORDINATOR, KEY_DEVICE
from .ng_switch import XiaomiSwitch

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = "Xiaomi Miio Switch"
DATA_KEY = "switch.xiaomi_ng"


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the switch from a config entry."""

    entities = []
    device = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]
    coordinator = hass.data[DOMAIN][config_entry.entry_id][KEY_COORDINATOR]

    if DATA_KEY not in hass.data:
        hass.data[DATA_KEY] = {}

    # TODO: special handling for switch devices

    switches = filter(
        lambda x: x.type == SettingType.Boolean, device.settings().values()
    )
    for switch in switches:
        _LOGGER.info("Adding switch: %s", switch)
        entities.append(XiaomiSwitch(device, switch, config_entry, coordinator))

    async_add_entities(entities)
