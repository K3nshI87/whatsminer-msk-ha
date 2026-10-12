from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .api import WhatsminerAPI
from .const import DOMAIN
from .coordinator import WhatsminerCoordinator
from .sensor import _device_info


@dataclass(frozen=True)
class WhatsminerButtonDescription(ButtonEntityDescription):
    action_fn: Callable[[WhatsminerAPI], Awaitable[None]] | None = None


BUTTONS: tuple[WhatsminerButtonDescription, ...] = (
    WhatsminerButtonDescription(
        key="restart_miner",
        name="Restart Miner",
        icon="mdi:restart",
        action_fn=lambda api: api.restart_miner(),
    ),
    WhatsminerButtonDescription(
        key="reboot_device",
        name="Reboot Device",
        icon="mdi:power-cycle",
        action_fn=lambda api: api.reboot_device(),
    ),
    WhatsminerButtonDescription(
        key="blink_led",
        name="Blink LED",
        icon="mdi:led-on",
        action_fn=lambda api: api.set_led(True),
    ),
    WhatsminerButtonDescription(
        key="clear_errors",
        name="Clear Errors",
        icon="mdi:broom",
        action_fn=lambda api: api.clear_errors(),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinators: dict[str, WhatsminerCoordinator] = hass.data[DOMAIN][entry.entry_id]
    entities = []
    for coordinator in coordinators.values():
        for desc in BUTTONS:
            entities.append(WhatsminerButton(coordinator, entry, desc))
    async_add_entities(entities)


class WhatsminerButton(CoordinatorEntity[WhatsminerCoordinator], ButtonEntity):
    entity_description: WhatsminerButtonDescription

    def __init__(self, coordinator: WhatsminerCoordinator, entry: ConfigEntry, description: WhatsminerButtonDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{coordinator.api.host}_{description.key}"
        self._attr_device_info = _device_info(coordinator, entry)

    async def async_press(self) -> None:
        if self.entity_description.action_fn:
            await self.entity_description.action_fn(self.coordinator.api)
