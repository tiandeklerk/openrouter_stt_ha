"""Speech-to-text platform for OpenRouter STT."""
from __future__ import annotations

import asyncio
import io
import json
import logging
import time
import wave
from collections.abc import AsyncIterable

import aiohttp

from homeassistant.components.stt import (
    AudioBitRates,
    AudioChannels,
    AudioCodecs,
    AudioFormats,
    AudioSampleRates,
    SpeechMetadata,
    SpeechResult,
    SpeechResultState,
    SpeechToTextEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity_platform import AddEntitiesCallback

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
    HTTP_REFERER,
    HTTP_TITLE,
    OPENROUTER_TRANSCRIPTIONS_URL,
    SUPPORTED_LANGUAGES,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the OpenRouter STT entity."""
    async_add_entities([OpenRouterSTTEntity(hass, entry)])


class OpenRouterSTTEntity(SpeechToTextEntity):
    """OpenRouter speech-to-text entity, backed by the OpenRouter API."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        self._attr_name = "OpenRouter STT"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}"

    def _option(self, key: str, default):
        # Options flow values win once set; fall back to the data recorded
        # at setup, then the hardcoded default.
        return self._entry.options.get(key, self._entry.data.get(key, default))

    @property
    def supported_languages(self) -> list[str]:
        return SUPPORTED_LANGUAGES

    @property
    def supported_formats(self) -> list[AudioFormats]:
        return [AudioFormats.WAV]

    @property
    def supported_codecs(self) -> list[AudioCodecs]:
        return [AudioCodecs.PCM]

    @property
    def supported_bit_rates(self) -> list[AudioBitRates]:
        return [AudioBitRates.BITRATE_16]

    @property
    def supported_sample_rates(self) -> list[AudioSampleRates]:
        return [AudioSampleRates.SAMPLERATE_16000]

    @property
    def supported_channels(self) -> list[AudioChannels]:
        return [AudioChannels.CHANNEL_MONO]

    async def async_process_audio_stream(
        self, metadata: SpeechMetadata, stream: AsyncIterable[bytes]
    ) -> SpeechResult:
        """Process an audio stream via the OpenRouter API."""
        pcm = bytearray()
        async for chunk in stream:
            pcm.extend(chunk)

        wav_bytes = _wrap_pcm_as_wav(
            bytes(pcm),
            sample_rate=int(metadata.sample_rate),
            sample_width=int(metadata.bit_rate) // 8,
            channels=int(metadata.channel),
        )

        api_key = self._entry.data[CONF_API_KEY]
        model = self._option(CONF_MODEL, DEFAULT_MODEL)
        prompt = self._option(CONF_PROMPT, "")
        timeout = self._option(CONF_TIMEOUT, DEFAULT_TIMEOUT)
        zdr = self._option(CONF_ZDR, DEFAULT_ZDR)
        language = _to_iso639_1(metadata.language)

        form = aiohttp.FormData()
        form.add_field("model", model)
        form.add_field("language", language)
        if prompt:
            form.add_field("prompt", prompt)
        if zdr:
            # Unverified whether OpenRouter honours this on a multipart
            # endpoint; sending it is mandatory regardless (zero data
            # retention requirement).
            form.add_field("provider", json.dumps({"data_collection": "deny"}))
        form.add_field("file", wav_bytes, filename="audio.wav", content_type="audio/wav")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": HTTP_REFERER,
            "X-Title": HTTP_TITLE,
        }

        duration = len(pcm) / (int(metadata.sample_rate) * (int(metadata.bit_rate) // 8))
        session = async_get_clientsession(self.hass)
        start = time.monotonic()
        try:
            async with asyncio.timeout(timeout):
                response = await session.post(
                    OPENROUTER_TRANSCRIPTIONS_URL, data=form, headers=headers
                )
                async with response:
                    status = response.status
                    body_text = await response.text()
        except TimeoutError:
            _LOGGER.error(
                "OpenRouter STT request timed out after %ss (model=%s)", timeout, model
            )
            return SpeechResult("", SpeechResultState.ERROR)
        except aiohttp.ClientError as err:
            _LOGGER.error("OpenRouter STT request failed: %s", err)
            return SpeechResult("", SpeechResultState.ERROR)

        elapsed = time.monotonic() - start

        if status != 200:
            _LOGGER.warning(
                "OpenRouter STT returned HTTP %s (model=%s, body_length=%d)",
                status,
                model,
                len(body_text),
            )
            return SpeechResult("", SpeechResultState.ERROR)

        try:
            payload = json.loads(body_text)
        except ValueError:
            _LOGGER.error(
                "OpenRouter STT returned a non-JSON body (model=%s, body_length=%d)",
                model,
                len(body_text),
            )
            return SpeechResult("", SpeechResultState.ERROR)

        if not isinstance(payload, dict):
            _LOGGER.error(
                "OpenRouter STT returned a JSON body that wasn't an object "
                "(model=%s, body_type=%s)",
                model,
                type(payload).__name__,
            )
            return SpeechResult("", SpeechResultState.ERROR)

        text = payload.get("text")
        if text is None:
            text = ""
        elif not isinstance(text, str):
            _LOGGER.error(
                "OpenRouter STT returned a non-string transcript "
                "(model=%s, text_type=%s)",
                model,
                type(text).__name__,
            )
            return SpeechResult("", SpeechResultState.ERROR)

        _LOGGER.debug(
            "OpenRouter STT model=%s duration=%.2fs latency=%.2fs transcript_length=%d",
            model,
            duration,
            elapsed,
            len(text),
        )
        return SpeechResult(text, SpeechResultState.SUCCESS)


def _wrap_pcm_as_wav(pcm_bytes: bytes, *, sample_rate: int, sample_width: int, channels: int) -> bytes:
    """Wrap raw PCM audio in a WAV container OpenRouter can accept."""
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)
    return buffer.getvalue()


def _to_iso639_1(language: str) -> str:
    """Map an HA language tag (e.g. en-ZA) to its ISO 639-1 code (en)."""
    return language.split("-")[0].lower()
