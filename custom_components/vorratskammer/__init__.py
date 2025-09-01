from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client

from .api import VorratskammerAPI
from .const import (
    DOMAIN,
    STORAGE_TOKENS,
    CONF_SUPABASE_URL,
    CONF_ANON_KEY,
    CONF_DAYS_AHEAD,
    CONF_SCAN_SUMMARY,
    CONF_SCAN_EXPIRING,
    CONF_SCAN_LOCATIONS,
    DEFAULT_DAYS_AHEAD,
)
from .coordinator import VorratskammerCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    session = aiohttp_client.async_get_clientsession(hass)
    supabase_url: str = entry.data[CONF_SUPABASE_URL]
    anon_key: str = entry.data[CONF_ANON_KEY]

    api = VorratskammerAPI(session, supabase_url, anon_key)

    store = hass.data.setdefault(DOMAIN, {}).setdefault(entry.entry_id, {})
    tokens: dict[str, Any] | None = store.get(STORAGE_TOKENS)
    if not tokens:
        tokens = {
            "access_token": entry.data.get("access_token"),
            "refresh_token": entry.data.get("refresh_token"),
        }
    api.set_tokens(tokens.get("access_token"), tokens.get("refresh_token"))
    store["api"] = api

    async def _save_tokens():
        new_tokens = api.export_tokens()
        store[STORAGE_TOKENS] = new_tokens
        hass.config_entries.async_update_entry(
            entry,
            data={
                **entry.data,
                "access_token": new_tokens.get("access_token"),
                "refresh_token": new_tokens.get("refresh_token"),
            },
        )

    api._on_refresh = _save_tokens  # type: ignore[attr-defined]

    # Build coordinators here (so we can do the first refresh BEFORE forwarding platforms)
    opts = entry.options
    days_ahead = int(opts.get(CONF_DAYS_AHEAD, DEFAULT_DAYS_AHEAD))

    scan_summary = int(entry.data.get(CONF_SCAN_SUMMARY))
    scan_expiring = int(entry.data.get(CONF_SCAN_EXPIRING))
    scan_locations = int(entry.data.get(CONF_SCAN_LOCATIONS))
    scan_location_items = scan_locations  # Use same interval as locations by default

    coord_summary = VorratskammerCoordinator(
        hass, "Vorratskammer Summary", scan_summary, api.inventory_summary
    )
    coord_expiring = VorratskammerCoordinator(
        hass, "Vorratskammer Expiring", scan_expiring, lambda: api.expiring_items(days_ahead)
    )
    coord_locations = VorratskammerCoordinator(
        hass, "Vorratskammer Locations", scan_locations, api.location_status
    )
    coord_location_items = VorratskammerCoordinator(
        hass, "Vorratskammer Location Items", scan_location_items, api.location_items
    )

    # First refresh BEFORE platform forward — if this fails, raise ConfigEntryNotReady here
    try:
        await asyncio.gather(
            coord_summary.async_config_entry_first_refresh(),
            coord_expiring.async_config_entry_first_refresh(),
            coord_locations.async_config_entry_first_refresh(),
            coord_location_items.async_config_entry_first_refresh(),
        )
    except Exception as err:
        # Any network/auth/function issue will be retried by HA
        raise ConfigEntryNotReady(f"Initial data update failed: {err}") from err

    store["coordinators"] = {
        "summary": coord_summary,
        "expiring": coord_expiring,
        "locations": coord_locations,
        "location_items": coord_location_items,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
