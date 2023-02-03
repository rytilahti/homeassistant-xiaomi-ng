"""Constants for the Xiaomi Miio component."""

DOMAIN = "xiaomi_miio"

# Config flow
CONF_DEVICE = "device"
CONF_MAC = "mac"
CONF_DEVICE_ID = "device_id"
CONF_CLOUD_USERNAME = "cloud_username"
CONF_CLOUD_PASSWORD = "cloud_password"
CONF_CLOUD_COUNTRY = "cloud_country"
CONF_USE_GENERIC = "use_genericmiot"

# TODO: only used by the custom gateway, remove
CONF_GATEWAY = "gateway"
CONF_CLOUD_SUBDEVICES = "cloud_subdevices"

# Keys
KEY_COORDINATOR = "coordinator"
KEY_DEVICE = "device"

# Attributes
ATTR_AVAILABLE = "available"

# Status
SUCCESS = ["ok"]


# Exceptions
class AuthException(Exception):
    """Exception indicating an authentication error."""


class SetupException(Exception):
    """Exception indicating a failure during setup."""


# Remote Services
SERVICE_LEARN = "remote_learn_command"
SERVICE_SET_REMOTE_LED_ON = "remote_set_led_on"
SERVICE_SET_REMOTE_LED_OFF = "remote_set_led_off"
