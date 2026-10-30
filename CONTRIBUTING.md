# Contributing

## Development setup

```
pip install pytest pytest-homeassistant-custom-component
pip uninstall -y aiodns pycares  # see .forgejo/workflows/ci.yml for why
pytest tests/ -v
```

`aiodns`/`pycares` are pulled in transitively by the `homeassistant`
package but aren't used by this integration. On Python 3.12 they spawn a
background DNS-resolver shutdown thread that trips
`pytest-homeassistant-custom-component`'s no-stray-threads teardown check,
failing tests with an unrelated-looking `AssertionError`. Uninstalling them
locally (CI already does this) avoids it.

No real OpenRouter API key is used in tests — HTTP is mocked via
`tests/conftest.py`'s `aioclient_mock` fixture
(`pytest-homeassistant-custom-component`).

## Branching

The default branch is protected: no direct pushes, changes land via PR with
at least one approval.
