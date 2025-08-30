from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Callable, Dict

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

_LOGGER = logging.getLogger(__name__)

class VorratskammerCoordinator(DataUpdateCoordinator[Dict[str, Any]]):
    def __init__(
        self,
        hass: HomeAssistant,
        name: str,
        update_interval_s: int,
        fetcher: Callable[[], Any],
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=name,
            update_interval=timedelta(seconds=update_interval_s),
        )
        self._fetcher = fetcher

    async def _async_update_data(self) -> Dict[str, Any]:
        try:
            data = await self._fetcher()
            if not isinstance(data, dict):
                raise UpdateFailed("Unexpected response type (expected JSON object).")
            return data
        except Exception as err:
            raise UpdateFailed(str(err)) from err
