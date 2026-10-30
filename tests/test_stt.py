"""Tests for the OpenRouter STT platform."""
from __future__ import annotations

import asyncio
import io
import logging
import wave

import pytest
from homeassistant.components.stt import (
    AudioBitRates,
    AudioChannels,
    AudioCodecs,
    AudioFormats,
    AudioSampleRates,
    SpeechMetadata,
    SpeechResultState,
)
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.openrouter_stt.const import (
    CONF_API_KEY,
    CONF_MODEL,
    DOMAIN,
    OPENROUTER_TRANSCRIPTIONS_URL,
)
from custom_components.openrouter_stt.stt import (
    OpenRouterSTTEntity,
    _to_iso639_1,
    _wrap_pcm_as_wav,
)


def _metadata(language: str = "en-ZA") -> SpeechMetadata:
    return SpeechMetadata(
        language=language,
        format=AudioFormats.WAV,
        codec=AudioCodecs.PCM,
        bit_rate=AudioBitRates.BITRATE_16,
        sample_rate=AudioSampleRates.SAMPLERATE_16000,
        channel=AudioChannels.CHANNEL_MONO,
    )


async def _audio_stream(chunks: list[bytes]):
    for chunk in chunks:
        yield chunk


def _make_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_API_KEY: "sk-or-test-key", CONF_MODEL: "openai/whisper-large-v3"},
    )


def test_wrap_pcm_as_wav_roundtrip():
    """Raw PCM bytes come back out of the WAV wrapper unchanged."""
    pcm = b"\x01\x00" * 100

    wav_bytes = _wrap_pcm_as_wav(pcm, sample_rate=16000, sample_width=2, channels=1)

    with wave.open(io.BytesIO(wav_bytes), "rb") as wav_file:
        assert wav_file.getframerate() == 16000
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.readframes(wav_file.getnframes()) == pcm


@pytest.mark.parametrize(
    ("tag", "expected"),
    [("en", "en"), ("en-US", "en"), ("en-ZA", "en"), ("EN-GB", "en")],
)
def test_to_iso639_1(tag: str, expected: str):
    assert _to_iso639_1(tag) == expected


async def test_async_process_audio_stream_success(hass, aioclient_mock):
    """A 200 response yields a SUCCESS result carrying the transcript."""
    aioclient_mock.post(OPENROUTER_TRANSCRIPTIONS_URL, json={"text": "turn on dog mode"})
    entry = _make_entry()
    entry.add_to_hass(hass)
    entity = OpenRouterSTTEntity(hass, entry)

    result = await entity.async_process_audio_stream(_metadata(), _audio_stream([b"\x00\x01" * 800]))

    assert result.result == SpeechResultState.SUCCESS
    assert result.text == "turn on dog mode"


async def test_async_process_audio_stream_http_401(hass, aioclient_mock, caplog):
    """A 401 yields an ERROR result and logs a warning with the status."""
    aioclient_mock.post(OPENROUTER_TRANSCRIPTIONS_URL, status=401, text="invalid api key")
    entry = _make_entry()
    entry.add_to_hass(hass)
    entity = OpenRouterSTTEntity(hass, entry)

    with caplog.at_level(logging.WARNING):
        result = await entity.async_process_audio_stream(
            _metadata(), _audio_stream([b"\x00\x01" * 800])
        )

    assert result.result == SpeechResultState.ERROR
    assert "401" in caplog.text
    assert "sk-or-test-key" not in caplog.text


async def test_debug_log_excludes_transcript_and_body(hass, aioclient_mock, caplog):
    """No log line, even at DEBUG, carries a transcript or a response body."""
    marker = "SENSITIVE-MARKER-DO-NOT-LOG"

    for response_kwargs in (
        {"status": 500, "text": marker},
        {"status": 200, "text": marker},  # non-JSON 200
        {"json": {"text": marker}},  # successful transcript
    ):
        aioclient_mock.clear_requests()
        aioclient_mock.post(OPENROUTER_TRANSCRIPTIONS_URL, **response_kwargs)
        entry = _make_entry()
        entry.add_to_hass(hass)
        entity = OpenRouterSTTEntity(hass, entry)

        with caplog.at_level(logging.DEBUG):
            await entity.async_process_audio_stream(
                _metadata(), _audio_stream([b"\x00\x01" * 800])
            )

        assert marker not in caplog.text
        caplog.clear()


async def test_async_process_audio_stream_null_text_does_not_crash(hass, aioclient_mock):
    """A 200 response with `{"text": null}` yields SUCCESS with an empty transcript."""
    aioclient_mock.post(OPENROUTER_TRANSCRIPTIONS_URL, json={"text": None})
    entry = _make_entry()
    entry.add_to_hass(hass)
    entity = OpenRouterSTTEntity(hass, entry)

    result = await entity.async_process_audio_stream(_metadata(), _audio_stream([b"\x00\x01" * 800]))

    assert result.result == SpeechResultState.SUCCESS
    assert result.text == ""


async def test_async_process_audio_stream_missing_text_does_not_crash(hass, aioclient_mock):
    """A 200 response with no `text` key yields SUCCESS with an empty transcript."""
    aioclient_mock.post(OPENROUTER_TRANSCRIPTIONS_URL, json={})
    entry = _make_entry()
    entry.add_to_hass(hass)
    entity = OpenRouterSTTEntity(hass, entry)

    result = await entity.async_process_audio_stream(_metadata(), _audio_stream([b"\x00\x01" * 800]))

    assert result.result == SpeechResultState.SUCCESS
    assert result.text == ""


async def test_async_process_audio_stream_json_array_body_does_not_crash(hass, aioclient_mock, caplog):
    """A 200 response with a JSON array body yields ERROR, not AttributeError."""
    aioclient_mock.post(OPENROUTER_TRANSCRIPTIONS_URL, json=["unexpected", "array"])
    entry = _make_entry()
    entry.add_to_hass(hass)
    entity = OpenRouterSTTEntity(hass, entry)

    with caplog.at_level(logging.ERROR):
        result = await entity.async_process_audio_stream(
            _metadata(), _audio_stream([b"\x00\x01" * 800])
        )

    assert result.result == SpeechResultState.ERROR


async def test_async_process_audio_stream_json_string_body_does_not_crash(hass, aioclient_mock, caplog):
    """A 200 response with a bare JSON string body yields ERROR, not AttributeError."""
    aioclient_mock.post(OPENROUTER_TRANSCRIPTIONS_URL, json="unexpected string")
    entry = _make_entry()
    entry.add_to_hass(hass)
    entity = OpenRouterSTTEntity(hass, entry)

    with caplog.at_level(logging.ERROR):
        result = await entity.async_process_audio_stream(
            _metadata(), _audio_stream([b"\x00\x01" * 800])
        )

    assert result.result == SpeechResultState.ERROR


async def test_async_process_audio_stream_non_str_text_does_not_crash(hass, aioclient_mock, caplog):
    """A 200 response with a non-string `text` field yields ERROR, not TypeError."""
    aioclient_mock.post(OPENROUTER_TRANSCRIPTIONS_URL, json={"text": 5})
    entry = _make_entry()
    entry.add_to_hass(hass)
    entity = OpenRouterSTTEntity(hass, entry)

    with caplog.at_level(logging.ERROR):
        result = await entity.async_process_audio_stream(
            _metadata(), _audio_stream([b"\x00\x01" * 800])
        )

    assert result.result == SpeechResultState.ERROR


async def test_async_process_audio_stream_timeout(hass, aioclient_mock, caplog):
    """A network timeout yields an ERROR result and logs the timeout."""
    aioclient_mock.post(OPENROUTER_TRANSCRIPTIONS_URL, exc=asyncio.TimeoutError())
    entry = _make_entry()
    entry.add_to_hass(hass)
    entity = OpenRouterSTTEntity(hass, entry)

    with caplog.at_level(logging.ERROR):
        result = await entity.async_process_audio_stream(
            _metadata(), _audio_stream([b"\x00\x01" * 800])
        )

    assert result.result == SpeechResultState.ERROR
    assert "timed out" in caplog.text.lower()
