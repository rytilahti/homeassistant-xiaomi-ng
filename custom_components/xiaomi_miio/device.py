# TODO: this file is not used anymore.
"""Code to handle a Xiaomi Device."""
import logging

from miio import Device, DeviceException

_LOGGER = logging.getLogger(__name__)


class ConnectXiaomiDevice:
    """Class to async connect to a Xiaomi Device."""

    # TODO: is this still relevant?

    def __init__(self, hass):
        """Initialize the entity."""
        self._hass = hass
        self._device = None
        self._device_info = None

    @property
    def device(self):
        """Return the class containing all connections to the device."""
        return self._device

    @property
    def device_info(self):
        """Return the class containing device info."""
        return self._device_info

    async def async_connect_device(self, host, token):
        """Connect to the Xiaomi Device."""
        _LOGGER.debug("Initializing with host %s (token %s...)", host, token[:5])

        try:
            self._device = Device(host, token)
            # get the device info
            self._device_info = None
        except DeviceException:
            pass

        _LOGGER.debug(
            "%s %s %s detected",
            self._device_info.model,
            self._device_info.firmware_version,
            self._device_info.hardware_version,
        )
