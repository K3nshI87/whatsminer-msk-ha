from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import COOLING_MODES, DOMAIN
from .coordinator import WhatsminerCoordinator
from .sensor import _device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinators: dict[str, WhatsminerCoordinator] = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        CoolingModeSelect(coordinator, entry) for coordinator in coordinators.values()
    )


class CoolingModeSelect(CoordinatorEntity[WhatsminerCoordinator], SelectEntity):
    _attr_name = "Cooling Mode"
    _attr_icon = "mdi:fan"
    _attr_options = COOLING_MODES

    def __init__(self, coordinator: WhatsminerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{coordinator.api.host}_cooling_mode"
        self._attr_device_info = _device_info(coordinator, entry)

    @property
    def current_option(self) -> str | None:
        return (self.coordinator.data or {}).get("cooling_mode")

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.api.set_cool_mode(option)
        await self.coordinator.async_request_refresh()
