"""Config flow for the OpenRouter STT integration."""
from __future__ import annotations

from typing import Any

import aiohttp
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_API_KEY,
    CONF_MODEL,
    CONF_PROMPT,
    CONF_TIMEOUT,
    CONF_ZDR,
    DEFAULT_MODEL,
    DEFAULT_TIMEOUT,
    DEFAULT_ZDR,
    DOMAIN,
    OPENROUTER_MODELS_URL,
)

STEP_USER_DATA_SCHEMA = vol.Schema({vol.Required(CONF_API_KEY): str})


class CannotConnect(Exception):
    """Error to indicate we cannot reach OpenRouter."""


class InvalidAuth(Exception):
    """Error to indicate the API key was rejected."""


async def _validate_api_key(hass, api_key: str) -> None:
    """Cheap reachability/auth check against the public /models endpoint.

    GET /models is public and unauthenticated, so a 200 here only
    proves OpenRouter is reachable, not that the key is valid. It still
    catches typos/network issues at setup time, and surfaces a real
    InvalidAuth if OpenRouter ever does reject the Authorization header.
    """
    session = async_get_clientsession(hass)
    try:
        response = await session.get(
            OPENROUTER_MODELS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=aiohttp.ClientTimeout(total=10),
        )
        async with response:
            if response.status == 401:
                raise InvalidAuth
            if response.status >= 400:
                raise CannotConnect
    except aiohttp.ClientError as err:
        raise CannotConnect from err


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for OpenRouter STT."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step: collect and validate the API key."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                await _validate_api_key(self.hass, user_input[CONF_API_KEY])
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(
                    title="OpenRouter STT",
                    data={**user_input, CONF_MODEL: DEFAULT_MODEL},
                )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> OptionsFlow:
        """Return the options flow."""
        return OptionsFlow(config_entry)


class OptionsFlow(config_entries.OptionsFlow):
    """Handle OpenRouter STT options: model, prompt, timeout, ZDR."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        options = self._config_entry.options
        data = self._config_entry.data
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_MODEL,
                    default=options.get(CONF_MODEL, data.get(CONF_MODEL, DEFAULT_MODEL)),
                ): str,
                vol.Optional(
                    CONF_PROMPT, default=options.get(CONF_PROMPT, "")
                ): str,
                vol.Optional(
                    CONF_TIMEOUT,
                    default=options.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
                ): vol.All(int, vol.Range(min=5, max=120)),
                vol.Optional(
                    CONF_ZDR, default=options.get(CONF_ZDR, DEFAULT_ZDR)
                ): bool,
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
