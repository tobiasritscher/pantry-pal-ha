from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import VorratskammerAPI
from .const import (
    DOMAIN,
    CONF_DAYS_AHEAD,
    CONF_SCAN_EXPIRING,
    CONF_SCAN_LOCATIONS,
    CONF_SCAN_SUMMARY,
    DEFAULT_DAYS_AHEAD,
)
from .coordinator import VorratskammerCoordinator

PARALLEL_UPDATES = 0

@dataclass
class SensorDescription:
    key: str
    name: str
    unit: str
    icon: str

SENSORS = [
    SensorDescription("summary", "Pantry Inventory Summary", "items", "mdi:package-variant"),
    SensorDescription("expiring", "Expiring Pantry Items", "items", "mdi:alert-decagram"),
    SensorDescription("locations", "Pantry Locations", "locations", "mdi:home-group"),
]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback):
    api: VorratskammerAPI = hass.data[DOMAIN][entry.entry_id]["api"]
    opts = entry.options

    days_ahead = int(opts.get(CONF_DAYS_AHEAD, DEFAULT_DAYS_AHEAD))
    scan_summary = int(opts.get(CONF_SCAN_SUMMARY, entry.data.get(CONF_SCAN_SUMMARY)))
    scan_expiring = int(opts.get(CONF_SCAN_EXPIRING, entry.data.get(CONF_SCAN_EXPIRING)))
    scan_locations = int(opts.get(CONF_SCAN_LOCATIONS, entry.data.get(CONF_SCAN_LOCATIONS)))

    coord_summary = VorratskammerCoordinator(hass, "Vorratskammer Summary", scan_summary, api.inventory_summary)
    coord_expiring = VorratskammerCoordinator(hass, "Vorratskammer Expiring", scan_expiring, lambda: api.expiring_items(days_ahead))
    coord_locations = VorratskammerCoordinator(hass, "Vorratskammer Locations", scan_locations, api.location_status)

    await coord_summary.async_config_entry_first_refresh()
    await coord_expiring.async_config_entry_first_refresh()
    await coord_locations.async_config_entry_first_refresh()

    entities: list[SensorEntity] = [
        VorratskammerGenericSensor(coord_summary, entry.entry_id, "summary", "Pantry Inventory Summary", "items", "mdi:package-variant"),
        VorratskammerGenericSensor(coord_expiring, entry.entry_id, "expiring", "Expiring Pantry Items", "items", "mdi:alert-decagram"),
        VorratskammerGenericSensor(coord_locations, entry.entry_id, "locations", "Pantry Locations", "locations", "mdi:home-group"),
    ]

    async_add_entities(entities)

class VorratskammerGenericSensor(CoordinatorEntity[VorratskammerCoordinator], SensorEntity):
    _attr_should_poll = False

    def __init__(
        self,
        coordinator: VorratskammerCoordinator,
        entry_id: str,
        key: str,
        name: str,
        unit: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry_id}_{key}"
        self._attr_name = name
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self) -> Optional[int]:
        data = self.coordinator.data or {}
        return data.get("state")

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        data = self.coordinator.data or {}
        attrs = data.get("attributes") or {}
        # Flatten only top-level attributes from your payloads; they’re already in friendly shape.
        return attrs
