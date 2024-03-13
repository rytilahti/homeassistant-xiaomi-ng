"""Config flow to configure Xiaomi Miio."""
from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from functools import partial
from re import search
from typing import Any, cast

import voluptuous as vol
from construct.core import ChecksumError
from homeassistant import config_entries
from homeassistant.components import zeroconf
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_NAME, CONF_TOKEN
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from miio import (
    CloudDeviceInfo,
    CloudException,
    CloudInterface,
    Device,
    DeviceFactory,
)

from .const import (
    CONF_CLOUD_COUNTRY,
    CONF_CLOUD_PASSWORD,
    CONF_CLOUD_USERNAME,
    CONF_DEVICE_ID,
    CONF_USE_GENERIC,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

AVAILABLE_LOCALES = CloudInterface.available_locales()

DEVICE_SETTINGS = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_TOKEN): vol.All(str, vol.Length(min=32, max=32)),
        vol.Optional(
            CONF_USE_GENERIC,
            default=False,
        ): bool,
        vol.Optional(CONF_MODEL): str,
    }
)
DEVICE_MODEL_CONFIG = vol.Schema(
    {
        vol.Required(CONF_MODEL): str,
    }
)
DEVICE_CLOUD_CONFIG = vol.Schema(
    {
        vol.Required(CONF_CLOUD_USERNAME): TextSelector(
            TextSelectorConfig(type=TextSelectorType.EMAIL)
        ),
        vol.Required(CONF_CLOUD_PASSWORD): TextSelector(
            TextSelectorConfig(type=TextSelectorType.PASSWORD)
        ),
        vol.Optional(CONF_CLOUD_COUNTRY, default="all"): vol.In(AVAILABLE_LOCALES),
    }
)


@dataclass
class DeviceInfo:
    """Container to convert between different device info types for config flow."""

    host: str | None = None
    token: str | None = None
    model: str | None = None
    name: str | None = None

    device_id: int | None = None

    cloud_username: str | None = None
    cloud_password: str | None = None
    use_generic: bool = False

    def to_config_entry(self):
        """Dump config entry data."""
        # If we are not arriving from a zeroconf or manual flows,
        # we don't have a name, so we use model instead
        if self.name is None:
            self.name = f"{self.model} ({self.device_id})"
        return {
            CONF_HOST: self.host,
            CONF_TOKEN: self.token,
            CONF_MODEL: self.model,
            CONF_NAME: self.name,
            CONF_DEVICE_ID: self.device_id,
            CONF_CLOUD_USERNAME: self.cloud_username,
            CONF_CLOUD_PASSWORD: self.cloud_password,
            CONF_USE_GENERIC: self.use_generic,
        }

    @classmethod
    def from_config_entry(cls, entry):
        """Load config entry data."""
        info = cls()
        _LOGGER.info("Reading from entry: %s", entry)
        info.host = entry[CONF_HOST]
        info.token = entry[CONF_TOKEN]
        info.model = entry[CONF_MODEL]

        # These are not available if no cloud connection was made
        info.cloud_username = entry.get(CONF_CLOUD_USERNAME, None)
        info.cloud_password = entry.get(CONF_CLOUD_PASSWORD, None)

        # These are only available on entry v2
        info.use_generic = entry.get(CONF_USE_GENERIC, None)
        info.device_id = entry.get(CONF_DEVICE_ID, None)

        return info

    @classmethod
    def from_yaml_config(cls, conf):
        """For migrating the old yaml configs."""
        info = cls()
        info.host = conf[CONF_HOST]
        info.token = conf[CONF_TOKEN]
        info.name = conf[CONF_NAME]
        info.model = conf[CONF_MODEL]

        return info

    @classmethod
    def from_cloud(cls, cloud_info: CloudDeviceInfo):
        info = cls()
        # TODO: rename upstream did to device_id?
        info.device_id = cloud_info.did
        info.host = cloud_info.ip
        info.token = cloud_info.token
        info.model = cloud_info.model
        info.name = cloud_info.name

        return info


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options for the component."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Init object."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self.hass.config_entries.async_update_entry(
                self.config_entry, data=user_input, options=self.config_entry.options
            )
            # TODO: is it correct to call create entry after an update here?!
            return self.async_create_entry(title="", data=user_input)

        # TODO: this is copy&paste with defaults being set
        DEVICE_SETTINGS_FILLED = vol.Schema(
            {
                vol.Required(CONF_HOST, default=self.config_entry.data[CONF_HOST]): str,
                vol.Required(
                    CONF_TOKEN, default=self.config_entry.data[CONF_TOKEN]
                ): vol.All(str, vol.Length(min=32, max=32)),
                vol.Optional(
                    CONF_USE_GENERIC, default=self.config_entry.data[CONF_USE_GENERIC]
                ): bool,
                vol.Optional(
                    CONF_MODEL, default=self.config_entry.data[CONF_MODEL]
                ): str,
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=DEVICE_SETTINGS_FILLED,
            errors=errors,
        )


class XiaomiMiioFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore[call-arg]  # noqa: E501
    """Handle a Xiaomi Miio config flow."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize."""
        self.device = DeviceInfo()
        # TODO: this should be a ref to the hass data, but it's not yet available here..
        self.cloud_info: dict[str, CloudDeviceInfo] = {}
        self.cloud_info_for_select: dict[str, CloudDeviceInfo] = {}
        self.force_selection = False  # TODO: hack to force selection on duplicate dids

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        """Get the options flow."""
        return OptionsFlowHandler(config_entry)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Perform reauth upon an authentication error or missing cloud credentials."""
        self.device = DeviceInfo.from_config_entry(entry_data)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Dialog that informs the user that reauth is required."""
        if user_input is not None:
            return await self.async_step_user()
        return self.async_show_form(step_id="reauth_confirm")

    async def async_step_import(self, conf: dict[str, Any]) -> FlowResult:
        """Import a configuration from config.yaml."""
        self.device = DeviceInfo.from_yaml_config(conf)

        self.context.update(
            {"title_placeholders": {"name": f"YAML import {self.device.host}"}}
        )
        return await self.async_step_connect()

    async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry):
        """Migrate old entry."""
        _LOGGER.debug("Migrating from version %s", config_entry.version)
        _LOGGER.warning("Contents: %s", config_entry)
        if config_entry.version == 1:
            entry = DeviceInfo.from_config_entry(config_entry)
            # TODO: mac address was the previously used unique id instead of deviceid
            #  need to find a way to get the DeviceInfo ref to update it.
            # new[CONF_DEVICE_ID] = self.device_id
            # config_entry.version = 2
            _LOGGER.info("New config entry: %s", entry)
            # hass.config_entries.async_update_entry(config_entry,
            #                                        data=entry.to_config_entry())

        _LOGGER.info("Migrating to version %s", config_entry.version)
        return False

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        # TODO: could this be initialized in a single central place?
        if DOMAIN not in self.hass.data:
            self.hass.data[DOMAIN] = defaultdict(dict)

        return self.async_show_menu(
            step_id="user",
            menu_options={
                "cloud": "Configure using cloud credentials",
                "manual": "Configure manually",
            },
        )

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle zeroconf discovery."""
        self.device.host = discovery_info.host

        match = search(
            r"(?P<model>.+)_mi(?:(io|bt))(?P<did>\d+)", discovery_info.hostname
        )
        if match is None:
            # TODO: fix parsing of yeelink-light-bslamp1_mibt1234xxxx.local.
            _LOGGER.error(
                "Unable to parse model and device id from hostname: %s",
                discovery_info.hostname,
            )
            return self.async_abort(
                reason="not_xiaomi_miio_device"
            )  # TODO: better error

        self.device.model = match.group("model").replace("-", ".")
        self.device.device_id = int(match.group("did"))

        # Update the host based on the zeroconf data
        await self.async_set_unique_id(self.device.device_id)
        self._abort_if_unique_id_configured(updates={CONF_HOST: self.device.host})

        # TODO: This could be used to abort the flow based on other variables
        #  besides the unique id
        # TODO: document in homeassistant dev docs
        # self._async_abort_entries_match({CONF_HOST: self.host})

        _LOGGER.info(
            "Detected %s (did: %s) at %s",
            self.device.model,
            self.device.device_id,
            self.device.host,
        )

        # TODO: should this just be set as a title already?
        # TODO: context and its usage is undocumented in dev docs
        self.context.update(
            {"title_placeholders": {"name": f"{self.device.model} {self.device.host}"}}
        )

        return await self.async_step_user()

    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step to fetch the information from the cloud.

        This will cache the results inside the hass.data so that subsequent config
        entries do not require the user to re-enter the cloud credentials.
        """
        errors = {}
        # TODO: could this be initialized in a single central place?
        if DOMAIN not in self.hass.data:
            self.hass.data[DOMAIN] = defaultdict(dict)

        if "cloud_info" in self.hass.data[DOMAIN]:
            return await self.async_step_select_device()

        if user_input is not None:
            cloud_username = user_input.get(CONF_CLOUD_USERNAME)
            cloud_password = user_input.get(CONF_CLOUD_PASSWORD)
            cloud_country = user_input.get(CONF_CLOUD_COUNTRY)

            miio_cloud = CloudInterface(cloud_username, cloud_password)
            try:
                get_devices_fn = partial(miio_cloud.get_devices, locale=cloud_country)
                devices = await self.hass.async_add_executor_job(get_devices_fn)
                main_devices = {
                    dev.did: dev for dev in devices.values() if not dev.is_child
                }
                self.hass.data[DOMAIN]["cloud_info"] = cloud_info = main_devices
            except CloudException as ex:
                _LOGGER.warning("Got exception while fetching the devices: %s", ex)
                return self.async_show_form(
                    step_id="cloud",
                    data_schema=DEVICE_CLOUD_CONFIG,
                    errors={"base": "cloud_login_error"},
                )

            if not cloud_info:
                errors["base"] = "cloud_no_devices"
                return self.async_show_form(
                    step_id="cloud", data_schema=DEVICE_CLOUD_CONFIG, errors=errors
                )

            self.cloud_info = cloud_info

            _LOGGER.warning("Got devices: %s", cloud_info.keys())
            _LOGGER.warning("Got devices: %s", cloud_info)

            return await self.async_step_select_device()

        return self.async_show_form(step_id="cloud", data_schema=DEVICE_CLOUD_CONFIG)

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle multiple cloud devices found."""
        _LOGGER.warning("start step_select")
        if self.device.host is None and self.cloud_info is None:
            raise Exception("No host nor cloud info available, this should not happen")

        # 1. If we arrive from the reauth, just retry
        # TODO: fix this mess of reusing the 'select_device' for all possible paths
        if self.context.get("source") == "reauth":
            _LOGGER.info("Got reauth for device selection, try reconnect")
            return await self.async_step_connect()

        self.cloud_info = self.hass.data[DOMAIN]["cloud_info"]

        # 2. If we arrive from the discovery, offer matching devices or connect
        if (
            all((self.device.host, self.device.device_id, self.cloud_info))
            and not self.device.token
            and not self.force_selection
        ):
            devices = {
                k: v
                for k, v in self.cloud_info.items()
                if v.did == self.device.device_id
            }
            if not devices:
                _LOGGER.error(
                    "Did not find the device from cloud data, maybe incorrect locale?",
                    self.cloud_info,
                )
                # TODO: should this display an error step?
                return await self.async_step_cloud()

            # TODO: this might be overkill?
            #  happens only if the device is registered on multiple locales
            if len(devices) > 1:
                _LOGGER.warning(
                    "Got multiple devices with the same device id, retry: %s",
                    devices.keys(),
                )
                self.cloud_info = devices
                self.force_selection = True
                return await self.async_step_select_device()

            dev = next(iter(devices.values()))
            _LOGGER.info("Found discovered device from the cloud data: %s", dev)
            self.device.token = dev.token
            return await self.async_step_connect()

        # 3. Handle the special case where only a single device is available
        if len(self.cloud_info) == 1:
            _LOGGER.info("Got only a single device from cloud, use that.")
            self.device_cloud_info = next(iter(self.cloud_info.values()))
            return await self.async_step_connect()

        if user_input is not None:
            _LOGGER.info(
                "Got user input: %s, create device from cloud info and try to connect",
                user_input,
            )
            self.device_cloud_info = self.cloud_info_for_select[
                user_input["selected_device"]
            ]
            if self.device_cloud_info is not None:
                try:
                    self.device = DeviceInfo.from_cloud(self.device_cloud_info)
                except Exception as ex:
                    _LOGGER.error(
                        "Unable to construct device from the cloud info: %s %s",
                        ex,
                        self.device_cloud_info,
                    )
                    return self.async_abort(reason="unknown")

                return await self.async_step_connect()

        def _select_title(dev: CloudDeviceInfo) -> str:
            return f"{dev.name} ({dev.model}, {dev.locale})"

        configured_devices = {
            entry.unique_id for entry in self._async_current_entries()
        }
        _LOGGER.error("Configured devs: %s", configured_devices)
        _LOGGER.error("Found devices: %s", self.cloud_info)
        available_devices = {
            _select_title(dev): dev
            for key, dev in self.cloud_info.items()
            if dev.did not in configured_devices
        }

        if not available_devices:
            # TODO: better error
            return self.async_abort(reason="not_xiaomi_miio_device")

        self.cloud_info_for_select = {
            label: dev for label, dev in available_devices.items()
        }
        _LOGGER.error("Available devices: %s", self.cloud_info_for_select)

        select_schema = vol.Schema(
            {vol.Required("selected_device"): vol.In(available_devices.keys())}
        )

        return self.async_show_form(step_id="select_device", data_schema=select_schema)

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure a xiaomi miio device Manually."""
        if user_input is not None:
            self.device.token = user_input[CONF_TOKEN]
            self.device.host = user_input[CONF_HOST]

            # TODO: model and use generic should be moved to advanced settings
            self.device.model = user_input.get(CONF_MODEL)
            # TODO: casting to avoid incompatible type, probably not the correct fix.
            self.device.use_generic = cast(bool, user_input.get(CONF_USE_GENERIC))

            return await self.async_step_connect()

        # TODO: show advanced options
        # TODO: show also if the model autodetection fails
        # if self.show_advanced_options:
        #    schema = schema.extend(DEVICE_OPTIONS_SCHEMA)

        # TODO: this is copy&paste with defaults being set from current device
        DEVICE_SETTINGS_FILLED = vol.Schema(
            {
                vol.Required(CONF_HOST, default=self.device.host): str,
                vol.Required(CONF_TOKEN, default=self.device.token): vol.All(
                    str, vol.Length(min=32, max=32)
                ),
                vol.Optional(CONF_USE_GENERIC, default=self.device.use_generic): bool,
                # TODO: hack to fallback to * if model is not set
                vol.Optional(
                    CONF_MODEL,
                    default=self.device.model or "*",
                ): str,
            }
        )

        return self.async_show_form(
            step_id="manual", data_schema=DEVICE_SETTINGS_FILLED
        )

    async def _update_existing_entry(self, existing_entry: ConfigEntry) -> FlowResult:
        """Update existing config entry using current device info."""
        self.hass.config_entries.async_update_entry(
            existing_entry, data=self.device.to_config_entry()
        )
        res = await self.hass.config_entries.async_reload(existing_entry.entry_id)
        if res:
            return self.async_abort(reason="reauth_successful")

        return self.async_abort(reason="reauth_failed")

    async def async_step_connect(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Connect to a xiaomi miio device."""
        _LOGGER.warning("start step_connect")
        errors: dict[str, str] = {}
        if self.device.host is None or self.device.token is None:
            _LOGGER.error("host or token is not set")
            return self.async_abort(reason="incomplete_info")

        if user_input is not None:
            _LOGGER.info("Got user input: %s", user_input)
            assert CONF_MODEL in user_input
            self.device.model = user_input[CONF_MODEL]

        def _create_device() -> Device:
            """Create miio device."""
            model = None
            # TODO: maybe using * as a wildcard/default model is not a good idea..
            if self.device.model != "*":
                model = self.device.model
            return DeviceFactory.create(
                self.device.host,
                self.device.token,
                model=model,
                force_generic_miot=self.device.use_generic,
            )

        # Try to connect and fetch the info.
        try:
            device = await self.hass.async_add_executor_job(_create_device)
            self.device.model = device.model
            self.device.device_id = device.device_id
            _LOGGER.info("Got device object: %s", device)
        except Exception as error:
            _LOGGER.warning("Unable to connect during setup: %s", error)
            # TODO: cleanup this, maybe?
            if self.device.model is None:
                if isinstance(error.__cause__, ChecksumError):
                    errors["base"] = "wrong_token"
                else:
                    errors["base"] = "cannot_connect"
            else:
                errors["base"] = "model_detection_failed"

            return self.async_show_form(
                step_id="connect", data_schema=DEVICE_MODEL_CONFIG, errors=errors
            )

        unique_id = str(self.device.device_id)

        # If we had an entry, update it with new information
        existing_entry = await self.async_set_unique_id(
            unique_id, raise_on_progress=False
        )
        if existing_entry:
            _LOGGER.info("Got existing entry, updating it")
            return await self._update_existing_entry(existing_entry)

        entry_data = self.device.to_config_entry()
        _LOGGER.info("Got config entry data: %s", entry_data)
        return self.async_create_entry(
            title=entry_data["name"],
            data=entry_data,
        )
