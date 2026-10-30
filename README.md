# ha-openrouter-stt

Home Assistant custom integration providing speech-to-text via the
[OpenRouter](https://openrouter.ai) API, distributed through
[HACS](https://hacs.xyz).

- Domain: `openrouter_stt`
- Status: tests run against a mocked HTTP layer only — **no live
  OpenRouter call has been verified**. Verify on your own Home Assistant
  system after install.

## Layout

```
custom_components/openrouter_stt/   HA integration (config flow, stt platform)
tests/                              pytest suite (HA API mocked, no real OpenRouter calls)
.forgejo/workflows/ci.yml           CI: pytest on Python 3.12
```

## Usage

1. Install via HACS (custom repository) or copy `custom_components/openrouter_stt`
   into your Home Assistant `custom_components/` directory, then restart HA.
2. Settings → Devices & Services → Add Integration → **OpenRouter STT**.
   Enter your OpenRouter API key.
3. Options (gear icon on the integration) let you set:
   - **Model** — free-text OpenRouter model ID. Defaults to
     `openai/whisper-large-v3`. This default is **unverified against a live
     API call** (see Acceptance criteria below) — override here if
     OpenRouter rejects it.
   - **Prompt / vocabulary hints** — optional text forwarded as the `prompt`
     field, e.g. to bias recognition of unusual phrases.
   - **Request timeout (seconds)** — default 30.
   - **Request zero data retention (ZDR)** — default on. Sends
     `provider={"data_collection": "deny"}` on every transcription call.
     Whether OpenRouter honours this on the multipart transcription
     endpoint is unverified (see below); the toggle is sent regardless
     because ZDR is a hard requirement.
4. Pick **OpenRouter STT** as the STT engine for your voice assistant
   pipeline (Settings → Voice assistants).

## Acceptance criteria / known gaps

No live OpenRouter key was used during development. The integration and
its test suite were built and verified entirely against **mocked HTTP
responses**, so the following are **not yet confirmed against the real
API**:

- Whether `openai/whisper-large-v3` is accepted as a `model` value.
- Whether the `prompt` field is honoured.
- Whether `provider={"data_collection": "deny"}` is accepted/honoured on
  this multipart endpoint.

Verify these once the integration is installed on your HA system. If
`openai/whisper-large-v3` is rejected, set a working model ID via the
integration's options.

## Development

```
pip install pytest pytest-homeassistant-custom-component
pip uninstall -y aiodns pycares  # see .forgejo/workflows/ci.yml for why
pytest tests/ -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for more on running the test suite
and the branching model.

## License

MIT — see [LICENSE](LICENSE).
