from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    ENDPOINT_LED,
    ENDPOINT_PAUSE,
    ENDPOINT_REBOOT,
    ENDPOINT_RESTART,
    ENDPOINT_RESUME,
)
from .coordinator import WhatsminerCoordinator
from .sensor import _device_info


@dataclass(frozen=True)
class WhatsminerButtonDescription(ButtonEntityDescription):
    endpoint: str = ""
    method: str = "POST"


BUTTONS: tuple[WhatsminerButtonDescription, ...] = (
    WhatsminerButtonDescription(
        key="restart_miner",
        name="Restart Miner",
        icon="mdi:restart",
        endpoint=ENDPOINT_RESTART,
    ),
    WhatsminerButtonDescription(
        key="reboot",
        name="Reboot Device",
        icon="mdi:power-cycle",
        endpoint=ENDPOINT_REBOOT,
    ),
    WhatsminerButtonDescription(
        key="pause_mining",
        name="Pause Mining",
        icon="mdi:pause-circle-outline",
        endpoint=ENDPOINT_PAUSE,
    ),
    WhatsminerButtonDescription(
        key="resume_mining",
        name="Resume Mining",
        icon="mdi:play-circle-outline",
        endpoint=ENDPOINT_RESUME,
    ),
    WhatsminerButtonDescription(
        key="led_on",
        name="LED On",
        icon="mdi:led-on",
        endpoint=ENDPOINT_LED,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: WhatsminerCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        WhatsminerButton(coordinator, entry, desc) for desc in BUTTONS
    )


class WhatsminerButton(CoordinatorEntity[WhatsminerCoordinator], ButtonEntity):
    entity_description: WhatsminerButtonDescription

    def __init__(
        self,
        coordinator: WhatsminerCoordinator,
        entry: ConfigEntry,
        description: WhatsminerButtonDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = _device_info(coordinator, entry)

    async def async_press(self) -> None:
        await self.coordinator.async_action(
            self.entity_description.endpoint,
            self.entity_description.method,
        )
        await self.coordinator.async_request_refresh()
