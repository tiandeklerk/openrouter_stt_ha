"""Shared fixtures for OpenRouter STT tests."""
import pytest

pytest_plugins = "pytest_homeassistant_custom_component"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Let Home Assistant discover custom_components/openrouter_stt in tests."""
    yield


@pytest.fixture
def mock_openrouter_api_key() -> str:
    """Return a fake OpenRouter API key so no real network calls are made."""
    return "sk-or-mock-key-for-tests"
