from __future__ import annotations

import logging
from typing import Any, Dict

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .api import VorratskammerAPI
from .const import (
    DOMAIN,
    CONF_SUPABASE_URL,
    CONF_ANON_KEY,
    CONF_EMAIL,
    CONF_PASSWORD,
    CONF_DAYS_AHEAD,
    CONF_SCAN_SUMMARY,
    CONF_SCAN_EXPIRING,
    CONF_SCAN_LOCATIONS,
    DEFAULT_DAYS_AHEAD,
    DEFAULT_SCAN_SUMMARY,
    DEFAULT_SCAN_EXPIRING,
    DEFAULT_SCAN_LOCATIONS,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_SUPABASE_URL, default="https://bscdbvbvylwqhkijhnub.supabase.co"): str,
        vol.Required(CONF_ANON_KEY): str,
        vol.Required(CONF_EMAIL): str,
        vol.Required(CONF_PASSWORD): str,
        vol.Optional(CONF_DAYS_AHEAD, default=DEFAULT_DAYS_AHEAD): vol.All(int, vol.Range(min=1, max=60)),
        vol.Optional(CONF_SCAN_SUMMARY, default=DEFAULT_SCAN_SUMMARY): vol.All(int, vol.Range(min=60, max=3600)),
        vol.Optional(CONF_SCAN_EXPIRING, default=DEFAULT_SCAN_EXPIRING): vol.All(int, vol.Range(min=60, max=3600)),
        vol.Optional(CONF_SCAN_LOCATIONS, default=DEFAULT_SCAN_LOCATIONS): vol.All(int, vol.Range(min=60, max=3600)),
    }
)

class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input: Dict[str, Any] | None = None) -> FlowResult:
        if user_input is None:
            return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA)

        # Attempt login
        session = aiohttp_client.async_get_clientsession(self.hass)
        api = VorratskammerAPI(session, user_input[CONF_SUPABASE_URL], user_input[CONF_ANON_KEY])
        try:
            tokens = await api.login_password(user_input[CONF_EMAIL], user_input[CONF_PASSWORD])
        except Exception as err:
            _LOGGER.exception("Login failed: %s", err)
            errors = {"base": "auth"}
            return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA, errors=errors)

        # Unique ID to prevent dupes per Supabase project + email
        await self.async_set_unique_id(f"{user_input[CONF_SUPABASE_URL]}::{user_input[CONF_EMAIL]}")
        self._abort_if_unique_id_configured()

        data = {
            CONF_SUPABASE_URL: user_input[CONF_SUPABASE_URL],
            CONF_ANON_KEY: user_input[CONF_ANON_KEY],
            CONF_EMAIL: user_input[CONF_EMAIL],
            # Do NOT store the plain password after setup
            "access_token": tokens.get("access_token"),
            "refresh_token": tokens.get("refresh_token"),
            CONF_SCAN_SUMMARY: user_input[CONF_SCAN_SUMMARY],
            CONF_SCAN_EXPIRING: user_input[CONF_SCAN_EXPIRING],
            CONF_SCAN_LOCATIONS: user_input[CONF_SCAN_LOCATIONS],
        }
        options = {
            CONF_DAYS_AHEAD: user_input[CONF_DAYS_AHEAD],
        }

        return self.async_create_entry(title="Vorratskammer", data=data, options=options)

    async def async_step_reauth(self, entry_data: dict) -> FlowResult:
        """Handle re-auth (prompt for password again if refresh fails)."""
        # Ask only for password; email/url are known.
        schema = vol.Schema({vol.Required(CONF_PASSWORD): str})
        if (user_input := self._async_current_step_user_input()) is None:
            pass  # noqa

        if self.context.get("reauth_entry"):
            entry = self.hass.config_entries.async_get_entry(self.context["reauth_entry"])
            if entry is None:
                return self.async_abort(reason="unknown")
            if self.hass.data.get(DOMAIN) and self.hass.data[DOMAIN].get(entry.entry_id):
                supabase_url = entry.data[CONF_SUPABASE_URL]
                email = entry.data[CONF_EMAIL]
            else:
                supabase_url = entry.data[CONF_SUPABASE_URL]
                email = entry.data[CONF_EMAIL]

        if not user_input:
            return self.async_show_form(step_id="reauth", data_schema=schema)

        session = aiohttp_client.async_get_clientsession(self.hass)
        api = VorratskammerAPI(session, supabase_url)
        try:
            tokens = await api.login_password(email, user_input[CONF_PASSWORD])
        except Exception:
            return self.async_show_form(step_id="reauth", data_schema=schema, errors={"base": "auth"})

        # Save new tokens
        self.hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, "access_token": tokens.get("access_token"), "refresh_token": tokens.get("refresh_token")},
        )
        await self.hass.config_entries.async_reload(entry.entry_id)
        return self.async_abort(reason="reauth_successful")

class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        schema = vol.Schema(
            {
                vol.Optional(CONF_DAYS_AHEAD, default=self._entry.options.get(CONF_DAYS_AHEAD, DEFAULT_DAYS_AHEAD)):
                    vol.All(int, vol.Range(min=1, max=60)),
                vol.Optional(CONF_SCAN_SUMMARY, default=self._entry.data.get(CONF_SCAN_SUMMARY)):
                    vol.All(int, vol.Range(min=60, max=3600)),
                vol.Optional(CONF_SCAN_EXPIRING, default=self._entry.data.get(CONF_SCAN_EXPIRING)):
                    vol.All(int, vol.Range(min=60, max=3600)),
                vol.Optional(CONF_SCAN_LOCATIONS, default=self._entry.data.get(CONF_SCAN_LOCATIONS)):
                    vol.All(int, vol.Range(min=60, max=3600)),
            }
        )
        if user_input is None:
            return self.async_show_form(step_id="init", data_schema=schema)

        data = {
            **self._entry.data,
            CONF_SCAN_SUMMARY: user_input[CONF_SCAN_SUMMARY],
            CONF_SCAN_EXPIRING: user_input[CONF_SCAN_EXPIRING],
            CONF_SCAN_LOCATIONS: user_input[CONF_SCAN_LOCATIONS],
        }
        self.hass.config_entries.async_update_entry(self._entry, data=data, options={CONF_DAYS_AHEAD: user_input[CONF_DAYS_AHEAD]})
        await self.hass.config_entries.async_reload(self._entry.entry_id)
        return self.async_abort(reason="options_updated")
