"""Config flow to configure Xiaomi Miio."""
from __future__ import annotations

import logging
from collections.abc import Mapping
from re import search
from typing import Any

import voluptuous as vol
from construct.core import ChecksumError
from homeassistant import config_entries
from homeassistant.components import zeroconf
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_MODEL, CONF_NAME, CONF_TOKEN
from homeassistant.core import callback
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
    CONF_DEVICE,
    CONF_DEVICE_ID,
    CONF_FLOW_TYPE,
    CONF_USE_GENERIC,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

AVAILABLE_LOCALES = CloudInterface.available_locales()

DEVICE_SETTINGS = {
    vol.Required(CONF_TOKEN): vol.All(str, vol.Length(min=32, max=32)),
    vol.Optional(
        CONF_USE_GENERIC,
        default=False,
    ): bool,
    vol.Optional(CONF_MODEL): vol.In(DeviceFactory.supported_models().keys()),
}
DEVICE_CONFIG = vol.Schema({vol.Required(CONF_HOST): str}).extend(DEVICE_SETTINGS)
DEVICE_MODEL_CONFIG = vol.Schema(
    {vol.Required(CONF_MODEL): vol.In(DeviceFactory.supported_models().keys())}
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


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Options for the component."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Init object."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        errors = {}

        if user_input is not None:
            user_input.get(CONF_USE_GENERIC, False)
            # TODO: how to trigger the setting update?
            if not errors:
                return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="device_options",
            data_schema=vol.Schema(DEVICE_SETTINGS),
            errors=errors,
        )


class XiaomiMiioFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Xiaomi Miio config flow."""

    VERSION = 2

    def __init__(self) -> None:
        """Initialize."""
        self.host: str | None = None
        self.token = None
        self.model = None
        self.name = None
        self.device_id = None
        self.cloud_username = None
        self.cloud_password = None
        self.cloud_devices = {}

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlowHandler:
        """Get the options flow."""
        return OptionsFlowHandler(config_entry)

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> FlowResult:
        """Perform reauth upon an authentication error or missing cloud credentials."""
        self.host = entry_data[CONF_HOST]
        self.token = entry_data[CONF_TOKEN]
        self.device_id = entry_data[CONF_DEVICE_ID]
        self.model = entry_data.get(CONF_MODEL)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Dialog that informs the user that reauth is required."""
        if user_input is not None:
            return await self.async_step_cloud()
        return self.async_show_form(step_id="reauth_confirm")

    async def async_step_import(self, conf: dict[str, Any]) -> FlowResult:
        """Import a configuration from config.yaml."""
        # TODO: need to migrate the yaml-only configs
        self.host = conf[CONF_HOST]
        self.token = conf[CONF_TOKEN]
        self.name = conf.get(CONF_NAME)
        self.model = conf.get(CONF_MODEL)

        self.context.update(
            {"title_placeholders": {"name": f"YAML import {self.host}"}}
        )
        return await self.async_step_connect()

    async def async_migrate_entry(hass, config_entry: ConfigEntry):
        """Migrate old entry."""
        # TODO: add support to migrate from v1
        # TODO: mac address was the previously used unique id, now it's the device id
        _LOGGER.debug("Migrating from version %s", config_entry.version)

        return True

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user."""
        return self.async_show_menu(
            step_id="user",
            menu_options={
                "cloud": "Configure using cloud",
                "manual": "Configure manually",
            },
        )

    async def async_step_zeroconf(
        self, discovery_info: zeroconf.ZeroconfServiceInfo
    ) -> FlowResult:
        """Handle zeroconf discovery."""
        self.host = discovery_info.host

        match = search(r"(?P<model>.+)_miio(?P<did>\d+)", discovery_info.hostname)
        if match is None:
            _LOGGER.error(
                "Unable to parse model and device id from hostname %s",
                discovery_info.hostname,
            )
            return self.async_abort(
                reason="not_xiaomi_miio_device"
            )  # TODO: better error
        self.model = match.group("model").replace("-", ".")
        self.device_id = match.group("did")

        await self.async_set_unique_id(self.device_id)
        self._abort_if_unique_id_configured({CONF_HOST: self.host})

        _LOGGER.info(
            "Detected %s with host %s and device id %s",
            self.model,
            self.host,
            self.device_id,
        )

        self.context.update(
            {"title_placeholders": {"name": f"{self.model} {self.host}"}}
        )

        return await self.async_step_cloud()

    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure a xiaomi miio device through the Miio Cloud."""
        errors = {}
        if self.cloud_devices:
            return await self.async_step_select_device()

        if user_input is not None:
            cloud_username = user_input.get(CONF_CLOUD_USERNAME)
            cloud_password = user_input.get(CONF_CLOUD_PASSWORD)
            cloud_country = user_input.get(CONF_CLOUD_COUNTRY)

            miio_cloud = CloudInterface(cloud_username, cloud_password)
            try:
                from functools import partial

                get_devices = partial(miio_cloud.get_devices, locale=cloud_country)
                devices: dict[
                    str, CloudDeviceInfo
                ] = await self.hass.async_add_executor_job(get_devices)
            except CloudException as ex:
                _LOGGER.warning("Got exception while fetching the devices: %s", ex)
                return self.async_show_form(
                    step_id="cloud",
                    data_schema=DEVICE_CLOUD_CONFIG,
                    errors={"base": "cloud_login_error"},
                )

            if not devices:
                errors["base"] = "cloud_no_devices"
                return self.async_show_form(
                    step_id="cloud", data_schema=DEVICE_CLOUD_CONFIG, errors=errors
                )

            _LOGGER.warning("Got devices: %s", devices)

            main_devices = [dev for dev in devices.values() if not dev.is_child]

            def select_title(dev: CloudDeviceInfo) -> str:
                return f"{dev.name} ({dev.model}, {dev.locale})"

            self.cloud_devices = {select_title(dev): dev for dev in main_devices}

            return await self.async_step_select_device()

        return self.async_show_form(step_id="cloud", data_schema=DEVICE_CLOUD_CONFIG)

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle multiple cloud devices found."""
        _LOGGER.warning("start step_select")
        if user_input is not None:
            self.cloud_device: CloudDeviceInfo = self.cloud_devices[
                user_input["selected_device"]
            ]
            # TODO: rename upstream did to device_id
            self.device_id = self.cloud_device.did
            self.host = self.cloud_device.ip
            self.token = self.cloud_device.token
            self.model = self.cloud_device.model
            return await self.async_step_connect()

        select_schema = vol.Schema(
            {vol.Required("selected_device"): vol.In(list(self.cloud_devices))}
        )

        return self.async_show_form(step_id="select_device", data_schema=select_schema)

    async def async_step_select_model(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select model when autodetection fails."""
        if user_input is None:
            return self.async_show_form(
                step_id="select_model",
                data_schema=DEVICE_MODEL_CONFIG,
            )

        self.model = user_input[CONF_MODEL]

        return await self.async_step_connect()

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure a xiaomi miio device Manually."""
        _LOGGER.warning("start step_manual")
        if user_input is not None:
            self.token = user_input[CONF_TOKEN]
            self.host = user_input[CONF_HOST]
            self.model = user_input.get(CONF_MODEL)

            return await self.async_step_connect()

        schema = vol.Schema(DEVICE_SETTINGS) if self.host else DEVICE_CONFIG
        # TODO: show advanced options
        # TODO: show also if the model autodetection fails
        # if self.show_advanced_options:
        #    schema = schema.extend(DEVICE_OPTIONS_SCHEMA)

        return self.async_show_form(step_id="manual", data_schema=schema)

    async def _update_existing_entry(self, existing_entry: ConfigEntry) -> FlowResult:
        data = existing_entry.data.copy()
        data[CONF_HOST] = self.host
        data[CONF_TOKEN] = self.token
        if self.cloud_username is not None and self.cloud_password is not None:
            data[CONF_CLOUD_USERNAME] = self.cloud_username
            data[CONF_CLOUD_PASSWORD] = self.cloud_password

        self.hass.config_entries.async_update_entry(existing_entry, data=data)
        await self.hass.config_entries.async_reload(existing_entry.entry_id)

        return self.async_abort(reason="reauth_successful")

    async def async_step_connect(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Connect to a xiaomi miio device."""
        _LOGGER.warning("start step_connect")
        errors: dict[str, str] = {}
        if (self.host is None or self.token is None) and self.cloud_device is None:
            _LOGGER.error("host or token is not set")
            return self.async_abort(reason="incomplete_info")

        if user_input is not None:
            _LOGGER.info("Got user defined model %s", user_input[CONF_MODEL])
            self.model = user_input[CONF_MODEL]

        def _create_device() -> Device:
            return DeviceFactory.create(self.host, self.token, model=self.model)

        # Try to connect and fetch the info.
        try:
            device = await self.hass.async_add_executor_job(_create_device)
            _LOGGER.info("Got device object: %s", device)
        except Exception as error:
            _LOGGER.warning("Unable to connect during setup: %s", error)
            # TODO: cleanup this, maybe?
            if self.model is None:
                if isinstance(error.__cause__, ChecksumError):
                    errors["base"] = "wrong_token"
                else:
                    errors["base"] = "cannot_connect"

        if errors:
            return self.async_show_form(
                step_id="connect", data_schema=DEVICE_MODEL_CONFIG, errors=errors
            )

        if self.model is None:
            _LOGGER.info("No model selected, performing autodetect")
            try:
                device_info = await self.hass.async_add_executor_job(device.info)
                _LOGGER.info(
                    "Detected %s %s %s",
                    device_info.model,
                    device_info.firmware_version,
                    device_info.hardware_version,
                )
                self.model = device_info.model
            except Exception as ex:
                _LOGGER.warning("Unable to fetch the device info: %s", ex)
                return self.async_show_form(
                    step_id="select_model", errors={"base": "model_detection_failed"}
                )

        if self.device_id is None:
            _LOGGER.error("Got no device id, abort abort")
            return self.async_abort(reason="no_device_id")

        unique_id = self.device_id

        # If we had an entry, update it with new information
        existing_entry = await self.async_set_unique_id(
            unique_id, raise_on_progress=False
        )
        if existing_entry:
            _LOGGER.info("Got existing entry, updating it")
            return await self._update_existing_entry(existing_entry)

        # If we are not arriving from a zeroconf flow, we may not have a name
        if self.name is None:
            self.name = self.model

        return self.async_create_entry(
            title=self.name,
            data={
                CONF_FLOW_TYPE: CONF_DEVICE,
                CONF_HOST: self.host,
                CONF_TOKEN: self.token,
                CONF_MODEL: self.model,
                CONF_DEVICE_ID: self.device_id,
                CONF_CLOUD_USERNAME: self.cloud_username,
                CONF_CLOUD_PASSWORD: self.cloud_password,
            },
        )
