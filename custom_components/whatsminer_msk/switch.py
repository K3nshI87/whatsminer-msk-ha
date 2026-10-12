from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WhatsminerCoordinator
from .sensor import _device_info


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinators: dict[str, WhatsminerCoordinator] = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        MiningSwitchEntity(coordinator, entry) for coordinator in coordinators.values()
    )


class MiningSwitchEntity(CoordinatorEntity[WhatsminerCoordinator], SwitchEntity):
    _attr_name = "Mining"
    _attr_icon = "mdi:pickaxe"

    def __init__(self, coordinator: WhatsminerCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{coordinator.api.host}_mining"
        self._attr_device_info = _device_info(coordinator, entry)

    @property
    def is_on(self) -> bool:
        return (self.coordinator.data or {}).get("miner_stopped") == "started"

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.api.resume_mining()
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.api.suspend_mining()
        await self.coordinator.async_request_refresh()
