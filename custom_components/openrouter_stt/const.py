"""Constants for the OpenRouter STT integration."""

DOMAIN = "openrouter_stt"

CONF_API_KEY = "api_key"
CONF_MODEL = "model"
CONF_PROMPT = "prompt"
CONF_TIMEOUT = "timeout"
CONF_ZDR = "zero_data_retention"

# openai/whisper-large-v3 does not appear in the public /models catalog,
# but that endpoint only lists chat/completions-capable models, not
# transcription-only ones — inconclusive on its own. No live key was
# available during development to confirm the endpoint accepts it; verify
# once installed and override via options if OpenRouter rejects it.
DEFAULT_MODEL = "openai/whisper-large-v3"
DEFAULT_TIMEOUT = 30
DEFAULT_ZDR = True

OPENROUTER_MODELS_URL = "https://openrouter.ai/api/v1/models"
OPENROUTER_TRANSCRIPTIONS_URL = "https://openrouter.ai/api/v1/audio/transcriptions"

HTTP_REFERER = "https://github.com/tiandeklerk/openrouter_stt_ha"
HTTP_TITLE = "Home Assistant OpenRouter STT"

# Explicit language list — no wildcard (["*"]), since the OpenRouter/Whisper
# endpoint needs an ISO 639-1 code, not an HA region tag.
SUPPORTED_LANGUAGES = [
    "en",
    "en-US",
    "en-GB",
    "en-ZA",
    "en-AU",
    "en-CA",
    "en-NZ",
]
