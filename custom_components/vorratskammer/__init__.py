from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .api import VorratskammerAPI
from .const import DOMAIN, STORAGE_TOKENS

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = aiohttp_client.async_get_clientsession(hass)
    supabase_url: str = entry.data["supabase_url"]

    api = VorratskammerAPI(session, supabase_url)

    tokens: dict[str, Any] | None = hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {}).get(STORAGE_TOKENS)
    if not tokens:
        tokens = {"access_token": entry.data.get("access_token"), "refresh_token": entry.data.get("refresh_token")}
    api.set_tokens(tokens.get("access_token"), tokens.get("refresh_token"))

    # Store for platforms
    hass.data[DOMAIN][entry.entry_id]["api"] = api

    # When tokens refresh, persist them on the entry (so HA restarts keep them)
    async def _save_tokens():
        new_tokens = api.export_tokens()
        hass.data[DOMAIN][entry.entry_id][STORAGE_TOKENS] = new_tokens
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data, "access_token": new_tokens.get("access_token"), "refresh_token": new_tokens.get("refresh_token")},
        )

    # Monkey patch a convenient hook onto the api (not elegant but simple)
    api._on_refresh = _save_tokens  # type: ignore[attr-defined]

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
