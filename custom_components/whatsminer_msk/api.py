from __future__ import annotations

import asyncio
import ipaddress
import logging
from typing import Any

import aiohttp

_LOGGER = logging.getLogger(__name__)

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=15)
LOGIN_TIMEOUT = aiohttp.ClientTimeout(total=10)
CONNECT_TIMEOUT = 5


class CannotConnect(Exception):
    pass


class InvalidAuth(Exception):
    pass


class WhatsminerAPI:
    def __init__(self, host: str, username: str, password: str) -> None:
        self.host = host
        self._username = username
        self._password = password
        self.base_url = f"http://{host}"
        self.api_url = f"{self.base_url}/api"
        self._session: aiohttp.ClientSession | None = None

    def _make_session(self) -> aiohttp.ClientSession:
        jar = aiohttp.CookieJar(unsafe=True)
        return aiohttp.ClientSession(cookie_jar=jar, timeout=REQUEST_TIMEOUT)

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = self._make_session()
        return self._session

    async def _login(self) -> None:
        session = self._get_session()
        boundary = "----FormBoundary" + "x" * 16
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="username"\r\n\r\n'
            f"{self._username}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="password"\r\n\r\n'
            f"{self._password}\r\n"
            f"--{boundary}--\r\n"
        ).encode()

        try:
            async with session.post(
                f"{self.base_url}/admin/login",
                data=body,
                headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
                auth=aiohttp.BasicAuth(self._username, self._password),
                timeout=LOGIN_TIMEOUT,
            ) as resp:
                if resp.status in (401, 403):
                    raise InvalidAuth("Invalid username or password")
                resp.raise_for_status()
        except InvalidAuth:
            raise
        except aiohttp.ClientError as err:
            raise CannotConnect(f"Login failed: {err}") from err

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        session = self._get_session()
        for attempt in range(2):
            try:
                url = f"{self.api_url}/{path.lstrip('/')}"
                async with session.request(method, url, **kwargs) as resp:
                    if resp.status in (401, 403):
                        if attempt == 0:
                            await self._login()
                            continue
                        raise InvalidAuth("Authentication failed")
                    if resp.status == 404:
                        url = f"{self.base_url}/{path.lstrip('/')}"
                        async with session.request(method, url, **kwargs) as r2:
                            r2.raise_for_status()
                            return await r2.json(content_type=None)
                    resp.raise_for_status()
                    return await resp.json(content_type=None)
            except (InvalidAuth, CannotConnect):
                raise
            except aiohttp.ClientError as err:
                if attempt == 0:
                    await self._login()
                    continue
                raise CannotConnect(str(err)) from err
        return {}

    async def _get(self, path: str) -> dict:
        return await self._request("GET", path)

    async def _post(self, path: str, json: dict | None = None) -> dict:
        return await self._request("POST", path, json=json)

    async def _delete(self, path: str) -> dict:
        return await self._request("DELETE", path)

    async def get_info(self) -> dict:
        return await self._get("info_app")

    async def get_summary(self) -> dict:
        return await self._get("summary")

    async def get_pools(self) -> dict:
        return await self._get("pools")

    async def get_power_limit(self) -> dict:
        return await self._get("power_limit")

    async def restart_miner(self) -> None:
        await self._post("restart")

    async def reboot_device(self) -> None:
        await self._post("reboot")

    async def suspend_mining(self) -> None:
        await self._post("suspend")

    async def resume_mining(self) -> None:
        await self._post("resume")

    async def set_led(self, enabled: bool) -> None:
        await self._post("led", json={"enabled": enabled})

    async def clear_errors(self) -> None:
        await self._delete("clear_errors")

    async def set_cool_mode(self, mode: str) -> None:
        await self._post("cool_mode", json={"mode": mode})

    async def close(self) -> None:
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None


async def _probe_host(host: str, username: str, password: str) -> str | None:
    api = WhatsminerAPI(host, username, password)
    try:
        await asyncio.wait_for(api._login(), timeout=CONNECT_TIMEOUT)
        await asyncio.wait_for(api.get_info(), timeout=CONNECT_TIMEOUT + 2)
        return host
    except Exception:
        return None
    finally:
        await api.close()


async def discover_miners(
    ip_range: str,
    username: str,
    password: str,
    concurrency: int = 30,
) -> list[str]:
    try:
        network = ipaddress.ip_network(ip_range, strict=False)
        hosts = [str(h) for h in network.hosts()]
    except ValueError:
        hosts = [ip.strip() for ip in ip_range.split(",") if ip.strip()]

    sem = asyncio.Semaphore(concurrency)

    async def probe(host: str) -> str | None:
        async with sem:
            return await _probe_host(host, username, password)

    results = await asyncio.gather(*[probe(h) for h in hosts])
    return [r for r in results if r is not None]
