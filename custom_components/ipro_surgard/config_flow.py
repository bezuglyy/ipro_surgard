from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult

from .const import (
    DOMAIN,
    NAME,
    CONF_LISTEN_HOST,
    CONF_LISTEN_PORT,
    CONF_MAX_ZONES,
    CONF_OFFLINE_TIMEOUT,
    CONF_SMS_ENABLE,
    CONF_SMS_LINE,
    CONF_SMS_PHONE,
    CONF_SMS_MSG_ARM,
    CONF_SMS_MSG_DISARM,
    CONF_SMS_COOLDOWN,
    CONF_SMS_OBJECT_FILTER,
    DEFAULT_LISTEN_HOST,
    DEFAULT_LISTEN_PORT,
    DEFAULT_MAX_ZONES,
    DEFAULT_OFFLINE_TIMEOUT,
    DEFAULT_SMS_ENABLE,
    DEFAULT_SMS_LINE,
    DEFAULT_SMS_PHONE,
    DEFAULT_SMS_MSG_ARM,
    DEFAULT_SMS_MSG_DISARM,
    DEFAULT_SMS_COOLDOWN,
    DEFAULT_SMS_OBJECT_FILTER,
)

def _schema(defaults: dict) -> vol.Schema:
    return vol.Schema(
        {
            vol.Required(CONF_LISTEN_HOST, default=defaults.get(CONF_LISTEN_HOST, DEFAULT_LISTEN_HOST)): str,
            vol.Required(CONF_LISTEN_PORT, default=int(defaults.get(CONF_LISTEN_PORT, DEFAULT_LISTEN_PORT))): vol.Coerce(int),
            vol.Required(CONF_MAX_ZONES, default=int(defaults.get(CONF_MAX_ZONES, DEFAULT_MAX_ZONES))): vol.Coerce(int),
            vol.Required(CONF_OFFLINE_TIMEOUT, default=int(defaults.get(CONF_OFFLINE_TIMEOUT, DEFAULT_OFFLINE_TIMEOUT))): vol.Coerce(int),

            # SMS (GOIP4) notifications
            vol.Required(CONF_SMS_ENABLE, default=bool(defaults.get(CONF_SMS_ENABLE, DEFAULT_SMS_ENABLE))): bool,
            vol.Optional(CONF_SMS_LINE, default=int(defaults.get(CONF_SMS_LINE, DEFAULT_SMS_LINE))): vol.Coerce(int),
            vol.Optional(CONF_SMS_PHONE, default=str(defaults.get(CONF_SMS_PHONE, DEFAULT_SMS_PHONE))): str,
            vol.Optional(CONF_SMS_MSG_ARM, default=str(defaults.get(CONF_SMS_MSG_ARM, DEFAULT_SMS_MSG_ARM))): str,
            vol.Optional(CONF_SMS_MSG_DISARM, default=str(defaults.get(CONF_SMS_MSG_DISARM, DEFAULT_SMS_MSG_DISARM))): str,
            vol.Optional(CONF_SMS_COOLDOWN, default=int(defaults.get(CONF_SMS_COOLDOWN, DEFAULT_SMS_COOLDOWN))): vol.Coerce(int),
            vol.Optional(CONF_SMS_OBJECT_FILTER, default=str(defaults.get(CONF_SMS_OBJECT_FILTER, DEFAULT_SMS_OBJECT_FILTER))): str,
        }
    )

class IproSurgardConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=_schema({}))

        # single instance
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(title=NAME, data=user_input)

    @staticmethod
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return IproSurgardOptionsFlow(config_entry)

class IproSurgardOptionsFlow(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        if user_input is None:
            defaults = {**dict(self.config_entry.data), **dict(self.config_entry.options)}
            return self.async_show_form(step_id="init", data_schema=_schema(defaults))

        return self.async_create_entry(title="", data=user_input)
