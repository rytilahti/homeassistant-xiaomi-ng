from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.core import HomeAssistant
import logging
import async_timeout
from datetime import timedelta


from .const import DOMAIN
from miio import Device, DeviceStatus, DeviceException

UPDATE_INTERVAL = timedelta(seconds=15)

POLLING_TIMEOUT_SEC = 10

_LOGGER = logging.getLogger(__name__)


class XiaomiDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, device: Device) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self._device = device

    async def _async_update_data(self) -> DeviceStatus:
        """Update device."""
        # TODO: handle changed tokens by raising a ConfigEntryAuthFailed here
        try:
            return await self._async_fetch_data()
        except DeviceException as ex:
            if getattr(ex, "code", None) != -9999:
                raise UpdateFailed(ex) from ex
            _LOGGER.info("Got exception while fetching the state, trying again: %s", ex)
        # Try to fetch the data a second time after error code -9999
        try:
            return await self._async_fetch_data()
        except DeviceException as ex:
            raise UpdateFailed(ex) from ex

    async def _async_fetch_data(self) -> DeviceStatus:
        """Fetch data from the device."""
        async with async_timeout.timeout(POLLING_TIMEOUT_SEC):
            state: DeviceStatus = await self.hass.async_add_executor_job(self._device.status)
            _LOGGER.info("Got new state for %s: %s", self._device, state)

            return state
