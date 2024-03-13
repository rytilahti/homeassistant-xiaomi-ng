import logging
from datetime import timedelta

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from miio import Device, DeviceException, DeviceStatus

from .const import DOMAIN

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

    # TODO: cleanup async_update_data() to allow tries to avoid code duplication
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
        # TODO: catch timeouterror or suppress it, as failure to do so
        #       will cause dataupdatecoordinator to fail fetching updates?!
        # at least the logs are filled with Got unexpected None as response
        # for device status after a timeout..
        async with async_timeout.timeout(POLLING_TIMEOUT_SEC):
            state: DeviceStatus = await self.hass.async_add_executor_job(
                self._device.status
            )
            if state is None:
                _LOGGER.warning(
                    "Got unexpected None as response for device status from %s"
                    % self._device
                )
                raise UpdateFailed(
                    "Received unexpected None for device status from %s" % self._device
                )
                return state
            _LOGGER.info(
                "Got new state for %s:\n%s", self._device, state.__cli_output__
            )

            return state
