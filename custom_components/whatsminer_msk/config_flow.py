from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

from .api import CannotConnect, InvalidAuth, discover_miners
from .const import (
    CONF_IP_RANGE,
    CONF_MINERS,
    CONF_PASSWORD,
    CONF_SCAN_INTERVAL,
    CONF_USERNAME,
    DEFAULT_PASSWORD,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_USERNAME,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

STEP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_IP_RANGE, default="192.168.1.0/24"): str,
        vol.Optional(CONF_USERNAME, default=DEFAULT_USERNAME): str,
        vol.Optional(CONF_PASSWORD, default=DEFAULT_PASSWORD): str,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): int,
    }
)


class WhatsminerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            ip_range = user_input[CONF_IP_RANGE].strip()
            username = user_input[CONF_USERNAME]
            password = user_input[CONF_PASSWORD]

            try:
                miners = await discover_miners(ip_range, username, password)
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                if not miners:
                    errors["base"] = "no_miners_found"
                else:
                    await self.async_set_unique_id(f"whatsminer_{ip_range}")
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"WhatsMiner ({', '.join(miners)})",
                        data={
                            CONF_IP_RANGE: ip_range,
                            CONF_USERNAME: username,
                            CONF_PASSWORD: password,
                            CONF_SCAN_INTERVAL: user_input.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
                            CONF_MINERS: miners,
                        },
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_SCHEMA,
            errors=errors,
        )
