"""Constants for the Xiaomi Miio component."""

DOMAIN = "xiaomi_ng"

# Config flow
CONF_FLOW_TYPE = "config_flow_device"
CONF_GATEWAY = "gateway"
CONF_DEVICE = "device"
CONF_MAC = "mac"
CONF_CLOUD_USERNAME = "cloud_username"
CONF_CLOUD_PASSWORD = "cloud_password"
CONF_CLOUD_COUNTRY = "cloud_country"
CONF_MANUAL = "manual"

# Options flow
CONF_CLOUD_SUBDEVICES = "cloud_subdevices"

# Keys
KEY_COORDINATOR = "coordinator"
KEY_DEVICE = "device"

# Attributes
ATTR_AVAILABLE = "available"

# Status
SUCCESS = ["ok"]

# Cloud
SERVER_COUNTRY_CODES = ["cn", "de", "i2", "ru", "sg", "us"]
DEFAULT_CLOUD_COUNTRY = "cn"


# Exceptions
class AuthException(Exception):
    """Exception indicating an authentication error."""


class SetupException(Exception):
    """Exception indicating a failure during setup."""


# Fan Models
MODEL_AIRPURIFIER_4 = "zhimi.airp.mb5"
MODEL_AIRPURIFIER_4_PRO = "zhimi.airp.vb4"
MODEL_AIRPURIFIER_2H = "zhimi.airpurifier.mc2"
MODEL_AIRPURIFIER_2S = "zhimi.airpurifier.mc1"
MODEL_AIRPURIFIER_3 = "zhimi.airpurifier.ma4"
MODEL_AIRPURIFIER_3C = "zhimi.airpurifier.mb4"
MODEL_AIRPURIFIER_3H = "zhimi.airpurifier.mb3"
MODEL_AIRPURIFIER_M1 = "zhimi.airpurifier.m1"
MODEL_AIRPURIFIER_M2 = "zhimi.airpurifier.m2"
MODEL_AIRPURIFIER_MA1 = "zhimi.airpurifier.ma1"
MODEL_AIRPURIFIER_MA2 = "zhimi.airpurifier.ma2"
MODEL_AIRPURIFIER_PRO = "zhimi.airpurifier.v6"
MODEL_AIRPURIFIER_PROH = "zhimi.airpurifier.va1"
MODEL_AIRPURIFIER_PRO_V7 = "zhimi.airpurifier.v7"
MODEL_AIRPURIFIER_SA1 = "zhimi.airpurifier.sa1"
MODEL_AIRPURIFIER_SA2 = "zhimi.airpurifier.sa2"
MODEL_AIRPURIFIER_V1 = "zhimi.airpurifier.v1"
MODEL_AIRPURIFIER_V2 = "zhimi.airpurifier.v2"
MODEL_AIRPURIFIER_V3 = "zhimi.airpurifier.v3"
MODEL_AIRPURIFIER_V5 = "zhimi.airpurifier.v5"

MODEL_AIRHUMIDIFIER_V1 = "zhimi.humidifier.v1"
MODEL_AIRHUMIDIFIER_CA1 = "zhimi.humidifier.ca1"
MODEL_AIRHUMIDIFIER_CA4 = "zhimi.humidifier.ca4"
MODEL_AIRHUMIDIFIER_CB1 = "zhimi.humidifier.cb1"
MODEL_AIRHUMIDIFIER_JSQ = "deerma.humidifier.jsq"
MODEL_AIRHUMIDIFIER_JSQ1 = "deerma.humidifier.jsq1"
MODEL_AIRHUMIDIFIER_MJJSQ = "deerma.humidifier.mjjsq"

MODEL_AIRFRESH_A1 = "dmaker.airfresh.a1"
MODEL_AIRFRESH_VA2 = "zhimi.airfresh.va2"
MODEL_AIRFRESH_T2017 = "dmaker.airfresh.t2017"

MODEL_FAN_1C = "dmaker.fan.1c"
MODEL_FAN_P10 = "dmaker.fan.p10"
MODEL_FAN_P11 = "dmaker.fan.p11"
MODEL_FAN_P5 = "dmaker.fan.p5"
MODEL_FAN_P9 = "dmaker.fan.p9"
MODEL_FAN_SA1 = "zhimi.fan.sa1"
MODEL_FAN_V2 = "zhimi.fan.v2"
MODEL_FAN_V3 = "zhimi.fan.v3"
MODEL_FAN_ZA1 = "zhimi.fan.za1"
MODEL_FAN_ZA3 = "zhimi.fan.za3"
MODEL_FAN_ZA4 = "zhimi.fan.za4"
MODEL_FAN_ZA5 = "zhimi.fan.za5"

MODELS_FAN_MIIO = [
    MODEL_FAN_P5,
    MODEL_FAN_SA1,
    MODEL_FAN_V2,
    MODEL_FAN_V3,
    MODEL_FAN_ZA1,
    MODEL_FAN_ZA3,
    MODEL_FAN_ZA4,
]

MODELS_FAN_MIOT = [
    MODEL_FAN_1C,
    MODEL_FAN_P10,
    MODEL_FAN_P11,
    MODEL_FAN_P9,
    MODEL_FAN_ZA5,
]

MODELS_PURIFIER_MIOT = [
    MODEL_AIRPURIFIER_3,
    MODEL_AIRPURIFIER_3C,
    MODEL_AIRPURIFIER_3H,
    MODEL_AIRPURIFIER_PROH,
    MODEL_AIRPURIFIER_4,
    MODEL_AIRPURIFIER_4_PRO,
]
MODELS_PURIFIER_MIIO = [
    MODEL_AIRPURIFIER_V1,
    MODEL_AIRPURIFIER_V2,
    MODEL_AIRPURIFIER_V3,
    MODEL_AIRPURIFIER_V5,
    MODEL_AIRPURIFIER_PRO,
    MODEL_AIRPURIFIER_PRO_V7,
    MODEL_AIRPURIFIER_M1,
    MODEL_AIRPURIFIER_M2,
    MODEL_AIRPURIFIER_MA1,
    MODEL_AIRPURIFIER_MA2,
    MODEL_AIRPURIFIER_SA1,
    MODEL_AIRPURIFIER_SA2,
    MODEL_AIRPURIFIER_2S,
    MODEL_AIRPURIFIER_2H,
    MODEL_AIRFRESH_A1,
    MODEL_AIRFRESH_VA2,
    MODEL_AIRFRESH_T2017,
]
MODELS_HUMIDIFIER_MIIO = [
    MODEL_AIRHUMIDIFIER_V1,
    MODEL_AIRHUMIDIFIER_CA1,
    MODEL_AIRHUMIDIFIER_CB1,
]
MODELS_HUMIDIFIER_MIOT = [MODEL_AIRHUMIDIFIER_CA4]
MODELS_HUMIDIFIER_MJJSQ = [
    MODEL_AIRHUMIDIFIER_JSQ,
    MODEL_AIRHUMIDIFIER_JSQ1,
    MODEL_AIRHUMIDIFIER_MJJSQ,
]

# AirQuality Models
MODEL_AIRQUALITYMONITOR_V1 = "zhimi.airmonitor.v1"
MODEL_AIRQUALITYMONITOR_B1 = "cgllc.airmonitor.b1"
MODEL_AIRQUALITYMONITOR_S1 = "cgllc.airmonitor.s1"
MODEL_AIRQUALITYMONITOR_CGDN1 = "cgllc.airm.cgdn1"

MODELS_AIR_QUALITY_MONITOR = [
    MODEL_AIRQUALITYMONITOR_V1,
    MODEL_AIRQUALITYMONITOR_B1,
    MODEL_AIRQUALITYMONITOR_S1,
    MODEL_AIRQUALITYMONITOR_CGDN1,
]

# Model lists
MODELS_GATEWAY = ["lumi.gateway", "lumi.acpartner"]
MODELS_FAN = (
    MODELS_PURIFIER_MIIO + MODELS_PURIFIER_MIOT + MODELS_FAN_MIIO + MODELS_FAN_MIOT
)
MODELS_HUMIDIFIER = (
    MODELS_HUMIDIFIER_MIOT + MODELS_HUMIDIFIER_MIIO + MODELS_HUMIDIFIER_MJJSQ
)

MODELS_AIR_MONITOR = [
    MODEL_AIRQUALITYMONITOR_V1,
    MODEL_AIRQUALITYMONITOR_B1,
    MODEL_AIRQUALITYMONITOR_S1,
    MODEL_AIRQUALITYMONITOR_CGDN1,
]

# Fan/Humidifier Services
SERVICE_SET_FAVORITE_LEVEL = "fan_set_favorite_level"
SERVICE_SET_FAN_LEVEL = "fan_set_fan_level"
SERVICE_SET_VOLUME = "fan_set_volume"
SERVICE_RESET_FILTER = "fan_reset_filter"
SERVICE_SET_EXTRA_FEATURES = "fan_set_extra_features"
SERVICE_SET_DRY = "set_dry"
SERVICE_SET_MOTOR_SPEED = "fan_set_motor_speed"

# Remote Services
SERVICE_LEARN = "remote_learn_command"
SERVICE_SET_REMOTE_LED_ON = "remote_set_led_on"
SERVICE_SET_REMOTE_LED_OFF = "remote_set_led_off"
