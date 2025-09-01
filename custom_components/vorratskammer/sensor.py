from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import VorratskammerCoordinator

PARALLEL_UPDATES = 0


@dataclass
class SensorDescription:
    key: str
    name: str
    unit: str
    icon: str


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
):
    store = hass.data[DOMAIN][entry.entry_id]
    coords: dict[str, VorratskammerCoordinator] = store["coordinators"]

    entities: list[SensorEntity] = [
        VorratskammerGenericSensor(
            coords["summary"], entry.entry_id, "summary", "Pantry Inventory Summary", "items", "mdi:package-variant"
        ),
        VorratskammerGenericSensor(
            coords["expiring"], entry.entry_id, "expiring", "Expiring Pantry Items", "items", "mdi:alert-decagram"
        ),
        VorratskammerGenericSensor(
            coords["locations"], entry.entry_id, "locations", "Pantry Locations", "locations", "mdi:home-group"
        ),
        VorratskammerGenericSensor(
            coords["location_items"], entry.entry_id, "location_items", "Pantry Location Items", "locations", "mdi:clipboard-list"
        ),
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
        return attrs
