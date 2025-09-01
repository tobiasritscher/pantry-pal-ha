from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

import aiohttp

_LOGGER = logging.getLogger(__name__)

class VorratskammerAPI:
    """Thin client for Supabase auth + Edge Functions."""

    def __init__(self, session: aiohttp.ClientSession, supabase_url: str, anon_key: str):
        self._session = session
        self._base = supabase_url.rstrip("/")
        self._gotrue = f"{self._base}/auth/v1"
        self._functions = f"{self._base}/functions/v1"
        self._anon_key = anon_key
        self._access_token = None
        self._refresh_token = None
        self._lock = asyncio.Lock()

    def _auth_headers(self) -> dict:
        # For GoTrue endpoints
        return {
            "apikey": self._anon_key,
            "Authorization": f"Bearer {self._anon_key}",
            "Content-Type": "application/json",
        }
    
    def _function_headers(self) -> dict:
        # For Edge Functions with user JWT
        if not self._access_token:
            raise RuntimeError("Not authenticated.")
        return {
            "apikey": self._anon_key,
            "Authorization": f"Bearer {self._access_token}",
            "Content-Type": "application/json",
        }

    # ---------- Tokens ----------
    def set_tokens(self, access_token: str, refresh_token: Optional[str]):
        self._access_token = access_token
        self._refresh_token = refresh_token

    def export_tokens(self) -> Dict[str, Optional[str]]:
        return {"access_token": self._access_token, "refresh_token": self._refresh_token}

    async def login_password(self, email: str, password: str) -> Dict[str, str]:
        url = f"{self._gotrue}/token?grant_type=password"
        payload = {"email": email, "password": password}
        async with self._session.post(url, json=payload, headers=self._auth_headers(), raise_for_status=True) as resp:
            data = await resp.json()
        self._access_token = data.get("access_token")
        self._refresh_token = data.get("refresh_token")
        if not self._access_token:
            raise RuntimeError(f"Supabase login returned no access_token: {data}")
        return {"access_token": self._access_token, "refresh_token": self._refresh_token}

    async def refresh(self) -> str:
        if not self._refresh_token:
            raise RuntimeError("No refresh_token available.")
        url = f"{self._gotrue}/token?grant_type=refresh_token"
        payload = {"refresh_token": self._refresh_token}
        async with self._session.post(url, json=payload, headers=self._auth_headers(), raise_for_status=True) as resp:
            data = await resp.json()
        self._access_token = data.get("access_token")
        self._refresh_token = data.get("refresh_token", self._refresh_token)
        if not self._access_token:
            raise RuntimeError(f"Failed to refresh access token: {data}")
        # Optional: notify __init__ to persist tokens
        if hasattr(self, "_on_refresh"):
            await self._on_refresh()  # type: ignore
        return self._access_token

    async def _call(self, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        url = f"{self._functions}/{path.lstrip('/')}"
        async with self._lock:
            async with self._session.get(url, headers=self._function_headers(), params=params) as resp:
                if resp.status == 401:
                    await self.refresh()
                    async with self._session.get(url, headers=self._function_headers(), params=params, raise_for_status=True) as r2:
                        return await r2.json()
                resp.raise_for_status()
                return await resp.json()

        async with self._lock:
            # First try
            async with self._session.get(url, headers=headers, params=params) as resp:
                if resp.status == 401:
                    _LOGGER.info("401 from %s — attempting token refresh", path)
                    await self.refresh()
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    # Retry once
                    async with self._session.get(url, headers=headers, params=params, raise_for_status=True) as r2:
                        return await r2.json()
                resp.raise_for_status()
                return await resp.json()

    async def inventory_summary(self) -> Dict[str, Any]:
        return await self._call("ha-inventory-summary")

    async def expiring_items(self, days: int) -> Dict[str, Any]:
        return await self._call("ha-expiring-items", params={"days": days})

    async def location_status(self, location_id: Optional[str] = None) -> Dict[str, Any]:
        params = {"location_id": location_id} if location_id else None
        return await self._call("ha-location-status", params=params)

    async def location_items(self, location_id: Optional[str] = None) -> Dict[str, Any]:
        params = {"location_id": location_id} if location_id else None
        return await self._call("ha-location-items", params=params)
