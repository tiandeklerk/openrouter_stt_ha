"""Tests for the OpenRouter STT config and options flows."""
from __future__ import annotations

from homeassistant import config_entries, data_entry_flow

from custom_components.openrouter_stt.const import (
    CONF_API_KEY,
    CONF_MODEL,
    CONF_PROMPT,
    CONF_TIMEOUT,
    CONF_ZDR,
    DEFAULT_MODEL,
    DOMAIN,
    OPENROUTER_MODELS_URL,
)


async def test_user_step_success(hass, aioclient_mock):
    """A valid key creates an entry with the default model stored."""
    aioclient_mock.get(OPENROUTER_MODELS_URL, json={"data": []})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] == data_entry_flow.FlowResultType.FORM

    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "sk-or-test-key"}
    )
    assert result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert result2["data"][CONF_API_KEY] == "sk-or-test-key"
    assert result2["data"][CONF_MODEL] == DEFAULT_MODEL


async def test_user_step_invalid_auth(hass, aioclient_mock):
    """A 401 from /models surfaces as an invalid_auth form error."""
    aioclient_mock.get(OPENROUTER_MODELS_URL, status=401)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "bad-key"}
    )
    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"] == {"base": "invalid_auth"}


async def test_user_step_cannot_connect(hass, aioclient_mock):
    """A 500 from /models surfaces as a cannot_connect form error."""
    aioclient_mock.get(OPENROUTER_MODELS_URL, status=500)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result2 = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "sk-or-test-key"}
    )
    assert result2["type"] == data_entry_flow.FlowResultType.FORM
    assert result2["errors"] == {"base": "cannot_connect"}


async def test_options_flow_update(hass, aioclient_mock):
    """The options flow persists model/prompt/timeout/ZDR overrides."""
    aioclient_mock.get(OPENROUTER_MODELS_URL, json={"data": []})

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_API_KEY: "sk-or-test-key"}
    )
    entry = result["result"]

    options_result = await hass.config_entries.options.async_init(entry.entry_id)
    assert options_result["type"] == data_entry_flow.FlowResultType.FORM

    options_result2 = await hass.config_entries.options.async_configure(
        options_result["flow_id"],
        {
            CONF_MODEL: "openai/whisper-large-v3",
            CONF_PROMPT: "Smart home vocabulary. Phrases: dog mode.",
            CONF_TIMEOUT: 45,
            CONF_ZDR: False,
        },
    )
    assert options_result2["type"] == data_entry_flow.FlowResultType.CREATE_ENTRY
    assert entry.options[CONF_TIMEOUT] == 45
    assert entry.options[CONF_ZDR] is False
    assert entry.options[CONF_PROMPT] == "Smart home vocabulary. Phrases: dog mode."
