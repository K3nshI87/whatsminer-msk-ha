from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import aiohttp
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import API_PATH, DEFAULT_SCAN_INTERVAL, DOMAIN, ENDPOINT_INFO

_LOGGER = logging.getLogger(__name__)


class WhatsminerCoordinator(DataUpdateCoordinator):
    def __init__(self, hass: HomeAssistant, host: str, port: int, scan_interval: int = DEFAULT_SCAN_INTERVAL) -> None:
        self.host = host
        self.port = port
        self._base_url = f"http://{host}:{port}{API_PATH}"
        self._session: aiohttp.ClientSession | None = None

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{host}",
            update_interval=timedelta(seconds=scan_interval),
        )

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=10)
            )
        return self._session

    async def _async_update_data(self) -> dict:
        try:
            session = self._get_session()
            async with session.get(f"{self._base_url}{ENDPOINT_INFO}") as resp:
                resp.raise_for_status()
                return await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with miner {self.host}: {err}") from err
        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout connecting to miner {self.host}") from err

    async def async_action(self, endpoint: str, method: str = "POST") -> bool:
        try:
            session = self._get_session()
            async with session.request(method, f"{self._base_url}{endpoint}") as resp:
                resp.raise_for_status()
                return True
        except Exception as err:
            _LOGGER.error("Action %s failed on %s: %s", endpoint, self.host, err)
            return False

    async def async_close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
