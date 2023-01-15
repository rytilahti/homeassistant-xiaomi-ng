"""Support for Xiaomi Miio number entities."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberEntityDescription
from .device import XiaomiMiioEntity
from homeassistant.core import callback
from homeassistant.helpers.entity import EntityCategory


class XiaomiNumber(XiaomiMiioEntity, NumberEntity):
    """Representation of a generic Xiaomi attribute selector."""

    def __init__(self, device, setting, entry, coordinator):
        """Initialize the generic Xiaomi attribute selector."""
        self._name = setting.name
        unique_id = f"{entry.unique_id}_number_{setting.id}"
        self._setter = setting.setter

        super().__init__(device, entry, unique_id, coordinator)

        self._attr_native_value = self._extract_value_from_attribute(
            coordinator.data, setting.id
        )

        # TODO: This should always be CONFIG for settables and non-configurable?
        category = EntityCategory(setting.extras.get("entity_category", "config"))
        description = NumberEntityDescription(
            key=setting.id,
            name=setting.name,
            icon=setting.extras.get("icon"),
            device_class=setting.extras.get("device_class"),
            entity_category=category,
            native_unit_of_measurement=setting.unit,
            native_min_value=setting.min_value,
            native_max_value=setting.max_value,
            native_step=setting.step,
        )

        self.entity_description = description

    async def async_set_native_value(self, value):
        """Set an option of the miio device."""
        if await self._try_command(
            "Turning %s on failed", self._setter, value=int(value)
        ):
            self._attr_native_value = value
            self.async_write_ha_state()

    @callback
    def _handle_coordinator_update(self):
        """Fetch state from the device."""
        # On state change the device doesn't provide the new state immediately.
        self._attr_native_value = self._extract_value_from_attribute(
            self.coordinator.data, self.entity_description.key
        )
        self.async_write_ha_state()
