"""Smoke test for the integration's constants."""
from custom_components.openrouter_stt.const import DOMAIN


def test_domain() -> None:
    """The domain must match the directory name HACS expects."""
    assert DOMAIN == "openrouter_stt"
