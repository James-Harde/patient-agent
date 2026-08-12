# 作者：小红书@人间清醒的李某人
"""TTS speech-synthesis client (DashScope)."""

import base64
from typing import Dict, Optional

from app.llm import llm_env


class SpeechClient:
    """Synthesises speech audio via DashScope TTS."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        websocket_url: Optional[str] = None,
    ) -> None:
        try:
            import dashscope
            from dashscope.audio.tts_v2 import SpeechSynthesizer
            from dashscope.audio.tts_v2.speech_synthesizer import AudioFormat
        except ImportError as exc:
            raise ValueError(
                "dashscope package is required for speech synthesis. "
                "Run: pip install dashscope"
            ) from exc

        dashscope.api_key = api_key or llm_env.get_tts_api_key()
        dashscope.base_websocket_api_url = (
            websocket_url or llm_env.get_tts_websocket_url()
        )

        self.model = model or llm_env.get_tts_model()
        self.voice = llm_env.get_tts_voice()
        self.websocket_url = websocket_url or llm_env.get_tts_websocket_url()
        self._speech_synthesizer_cls = SpeechSynthesizer
        self._audio_format_cls = AudioFormat

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def synthesize(
        self,
        text: str,
        voice: str = "",
        audio_format: str = "mp3",
    ) -> Dict[str, str]:
        """Synthesise *text* and return a dict with ``audio_base64``,
        ``mime_type``, ``model``, and ``voice``."""
        normalized_format = audio_format.lower()
        if normalized_format != "mp3":
            raise ValueError("Only mp3 speech_format is currently supported")

        selected_voice = voice or self.voice

        synthesizer = self._speech_synthesizer_cls(
            model=self.model,
            voice=selected_voice,
            format=self._audio_format_cls.MP3_22050HZ_MONO_256KBPS,
        )
        audio_bytes = synthesizer.call(text)
        if not audio_bytes:
            response = None
            try:
                response = synthesizer.get_response()
            except Exception:
                response = None
            raise ValueError(
                "Speech synthesis returned empty audio: "
                f"model={self.model}, voice={selected_voice}, "
                f"websocket_url={self.websocket_url}, response={response}"
            )

        return {
            "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
            "mime_type": "audio/mp3",
            "model": self.model,
            "voice": selected_voice,
        }
