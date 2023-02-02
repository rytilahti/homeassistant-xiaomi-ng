"""Support for Xiaomi humidifiers."""
import logging
import math

from homeassistant.components.humidifier import (
    HumidifierDeviceClass,
    HumidifierEntity,
    HumidifierEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_MODE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.percentage import percentage_to_ranged_value
from miio.integrations.humidifier.deerma.airhumidifier_mjjsq import (
    OperationMode as AirhumidifierMjjsqOperationMode,
)
from miio.integrations.humidifier.zhimi.airhumidifier import (
    OperationMode as AirhumidifierOperationMode,
)
from miio.integrations.humidifier.zhimi.airhumidifier_miot import (
    OperationMode as AirhumidifierMiotOperationMode,
)

from .const import (
    CONF_DEVICE,
    CONF_FLOW_TYPE,
    DOMAIN,
    KEY_COORDINATOR,
    KEY_DEVICE,
)
from .entity import XiaomiEntity

_LOGGER = logging.getLogger(__name__)

# Air Humidifier
ATTR_TARGET_HUMIDITY = "target_humidity"

AVAILABLE_ATTRIBUTES = {
    ATTR_MODE: "mode",
    ATTR_TARGET_HUMIDITY: "target_humidity",
}

AVAILABLE_MODES_CA1_CB1 = [
    mode.name
    for mode in AirhumidifierOperationMode
    if mode is not AirhumidifierOperationMode.Strong
]
AVAILABLE_MODES_CA4 = [mode.name for mode in AirhumidifierMiotOperationMode]
AVAILABLE_MODES_MJJSQ = [
    mode.name
    for mode in AirhumidifierMjjsqOperationMode
    if mode is not AirhumidifierMjjsqOperationMode.WetAndProtect
]
AVAILABLE_MODES_OTHER = [
    mode.name
    for mode in AirhumidifierOperationMode
    if mode is not AirhumidifierOperationMode.Auto
]


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Humidifier from a config entry."""
    if config_entry.data[CONF_FLOW_TYPE] != CONF_DEVICE:
        return

    entities: list[HumidifierEntity] = []
    entity: HumidifierEntity
    unique_id = config_entry.unique_id
    coordinator = hass.data[DOMAIN][config_entry.entry_id][KEY_COORDINATOR]

    air_humidifier = hass.data[DOMAIN][config_entry.entry_id][KEY_DEVICE]
    entity = XiaomiHumidifier(
        air_humidifier,
        config_entry,
        unique_id,
        coordinator,
    )

    entities.append(entity)

    async_add_entities(entities)


class XiaomiHumidifier(XiaomiEntity, HumidifierEntity):
    """Representation of a generic Xiaomi humidifier device."""

    _attr_device_class = HumidifierDeviceClass.HUMIDIFIER
    _attr_supported_features = HumidifierEntityFeature.MODES
    supported_features: int

    def __init__(self, device, entry, unique_id, coordinator):
        """Initialize the generic Xiaomi device."""
        super().__init__(device, entry, unique_id, coordinator=coordinator)

        self._state = None
        self._attributes = {}
        self._mode = None
        self._humidity_steps = 100
        self._target_humidity = None

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    @property
    def mode(self):
        """Get the current mode."""
        return self._mode

    async def async_turn_on(
        self,
        **kwargs,
    ) -> None:
        """Turn the device on."""
        result = await self._try_command(
            "Turning the miio device on failed.", self._device.on
        )
        if result:
            self._state = True
            self.async_write_ha_state()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn the device off."""
        result = await self._try_command(
            "Turning the miio device off failed.", self._device.off
        )

        if result:
            self._state = False
            self.async_write_ha_state()

    def translate_humidity(self, humidity):
        """Translate the target humidity to the first valid step."""
        return (
            math.ceil(percentage_to_ranged_value((1, self._humidity_steps), humidity))
            * 100
            / self._humidity_steps
            if 0 < humidity <= 100
            else None
        )
