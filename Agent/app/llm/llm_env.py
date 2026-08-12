#
"""Centralised configuration reader for LLM / Embedding / TTS environment variables.

All values are read from environment variables only.  There are **no**
hard-coded Qwen / DashScope provider defaults for the LLM path — Qwen is
merely one possible value for ``LLM_MODEL``.

Embedding and TTS retain conservative defaults (e.g. dimension, voice,
model name) purely so existing demo setups don't break on every restart.
"""

from __future__ import annotations

import os

# ---------------------------------------------------------------------------
# LLM  (OpenAI-compatible chat / agent)
# ---------------------------------------------------------------------------

def get_llm_api_key() -> str:
    value = os.getenv("LLM_API_KEY", "").strip()
    if not value:
        raise ValueError("LLM_API_KEY is not configured")
    return value


def get_llm_base_url() -> str:
    value = os.getenv("LLM_BASE_URL", "").strip()
    if not value:
        raise ValueError("LLM_BASE_URL is not configured")
    return value


def get_llm_model() -> str:
    value = os.getenv("LLM_MODEL", "").strip()
    if not value:
        raise ValueError("LLM_MODEL is not configured")
    return value


# ---------------------------------------------------------------------------
# Embedding  (used by the FAISS vector service)
# ---------------------------------------------------------------------------

def get_embedding_api_key() -> str:
    value = os.getenv("EMBEDDING_API_KEY", "").strip()
    if not value:
        raise ValueError("EMBEDDING_API_KEY is not configured")
    return value


def get_embedding_base_url() -> str:
    return os.getenv("EMBEDDING_BASE_URL", "").strip() or (
        "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )


def get_embedding_model() -> str:
    return os.getenv("EMBEDDING_MODEL", "").strip() or "text-embedding-v4"


def get_embedding_dimensions() -> int:
    raw = os.getenv("EMBEDDING_DIMENSIONS", "").strip()
    if not raw:
        return 1024
    if not raw.isdigit():
        raise ValueError("EMBEDDING_DIMENSIONS must be an integer, got: " + raw)
    return int(raw)


# ---------------------------------------------------------------------------
# TTS  (DashScope speech synthesis)
# ---------------------------------------------------------------------------

def get_tts_api_key() -> str:
    value = os.getenv("TTS_API_KEY", "").strip()
    if not value:
        raise ValueError("TTS_API_KEY is not configured")
    return value


def get_tts_model() -> str:
    return os.getenv("TTS_MODEL", "").strip() or "cosyvoice-v3-flash"


def get_tts_voice() -> str:
    return os.getenv("TTS_VOICE", "").strip() or "longanyang"


def get_tts_websocket_url() -> str:
    return os.getenv("TTS_WEBSOCKET_URL", "").strip() or (
        "wss://dashscope.aliyuncs.com/api-ws/v1/inference"
    )
