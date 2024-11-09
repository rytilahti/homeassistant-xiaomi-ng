"""Update coordinator."""

import logging
import math
from datetime import timedelta

import async_timeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from miio import Device, DeviceException, DeviceStatus

from .const import DOMAIN

UPDATE_INTERVAL = timedelta(seconds=15)

RETRY_INTERVAL = timedelta(seconds=60)
ALLOWED_RETRY_COUNT = math.ceil((RETRY_INTERVAL - UPDATE_INTERVAL) / UPDATE_INTERVAL)

POLLING_TIMEOUT_SEC = 10

_LOGGER = logging.getLogger(__name__)


class XiaomiDataUpdateCoordinator(DataUpdateCoordinator):
    """Update coordinator for xiaomi_miio."""

    retries_available = -1
    last_known_state: DeviceStatus

    def __init__(self, hass: HomeAssistant, device: Device) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass=hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=UPDATE_INTERVAL,
        )
        self._device = device

    def _defer_or_raise(self, ex: Exception):
        """Return the last known state of a method or raise if ran out of retries.

        By returning the last known state, the method will defer to the next
        fetch poll.
        """
        self.retries_available -= 1
        if self.retries_available <= 0:
            # Passtru exception to hass
            raise ex
        _LOGGER.info(
            "%s: Deferring update. Using last known state. Retries left: %s",
            self._device,
            self.retries_available,
        )
        return self.last_known_state

    async def _async_update_data(self) -> DeviceStatus:
        """Update device."""
        # TODO: handle changed tokens by raising a ConfigEntryAuthFailed here
        for i in range(10):
            try:
                self.last_known_state = await self._async_fetch_data()
                self.retries_available = ALLOWED_RETRY_COUNT
                return self.last_known_state
            except DeviceException as ex:
                if getattr(ex, "code", None) == -9999:
                    # Try to fetch the data a second time after error code -9999
                    self._defer_or_raise(ex) if i >= 1 else None
                    continue
                _LOGGER.info(
                    "%s: Got exception while fetching the state: %s", self._device, ex
                )
                return self._defer_or_raise(ex)
            except TimeoutError as ex:
                _LOGGER.info("%s: Got timeout while fetching the state", self._device)
                return self._defer_or_raise(ex)
            # Defer on all exceptions
            except Exception as ex:
                return self._defer_or_raise(ex)
        self._defer_or_raise(UpdateFailed("%s: Too many iterations", self._device))

    async def _async_fetch_data(self) -> DeviceStatus:
        """Fetch data from the device."""
        async with async_timeout.timeout(POLLING_TIMEOUT_SEC):
            state: DeviceStatus = await self.hass.async_add_executor_job(
                self._device.status
            )
            if state is None:
                msg = f"{self._device}: Received unexpected None for device status"
                _LOGGER.warning(msg)
                raise UpdateFailed(msg)
            _LOGGER.info("%s: Got new state:\n%s", self._device, state.__cli_output__)
            return state
