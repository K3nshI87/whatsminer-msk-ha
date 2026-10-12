from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import CannotConnect, WhatsminerAPI
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class WhatsminerCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, api: WhatsminerAPI, scan_interval: int = DEFAULT_SCAN_INTERVAL) -> None:
        self.api = api
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{api.host}",
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> dict:
        try:
            return await self.api.get_info()
        except CannotConnect as err:
            raise UpdateFailed(f"Cannot reach miner {self.api.host}: {err}") from err
