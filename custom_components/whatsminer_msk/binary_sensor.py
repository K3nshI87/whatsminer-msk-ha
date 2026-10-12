from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import WhatsminerCoordinator
from .sensor import _device_info


@dataclass(frozen=True)
class WhatsminerBinarySensorDescription(BinarySensorEntityDescription):
    value_fn: Callable[[dict], bool | None] | None = None


BINARY_SENSORS: tuple[WhatsminerBinarySensorDescription, ...] = (
    WhatsminerBinarySensorDescription(
        key="is_overheat",
        name="Overheat",
        device_class=BinarySensorDeviceClass.HEAT,
        value_fn=lambda d: bool(d.get("is_overheat")),
    ),
    WhatsminerBinarySensorDescription(
        key="tuning",
        name="Tuning",
        icon="mdi:tune",
        value_fn=lambda d: bool(d.get("tuning")),
    ),
    WhatsminerBinarySensorDescription(
        key="cloud_connection",
        name="Cloud Connected",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        value_fn=lambda d: bool(d.get("cloud_connection")),
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
        for desc in BINARY_SENSORS:
            entities.append(WhatsminerBinarySensor(coordinator, entry, desc))
    async_add_entities(entities)


class WhatsminerBinarySensor(CoordinatorEntity[WhatsminerCoordinator], BinarySensorEntity):
    entity_description: WhatsminerBinarySensorDescription

    def __init__(self, coordinator: WhatsminerCoordinator, entry: ConfigEntry, description: WhatsminerBinarySensorDescription) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{coordinator.api.host}_{description.key}"
        self._attr_device_info = _device_info(coordinator, entry)

    @property
    def is_on(self) -> bool | None:
        if not self.coordinator.data or self.entity_description.value_fn is None:
            return None
        try:
            return self.entity_description.value_fn(self.coordinator.data)
        except Exception:
            return None
