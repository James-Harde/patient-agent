# 作者：小红书@人间清醒的李某人

import base64
import os
from typing import Dict, Optional


DEFAULT_SPEECH_MODEL = "cosyvoice-v3-flash"
DEFAULT_SPEECH_VOICE = "longanyang"
DEFAULT_WEBSOCKET_URL = "wss://dashscope.aliyuncs.com/api-ws/v1/inference"


class QwenSpeechClient:
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

        resolved_api_key = (
            api_key
            or os.getenv("TTS_API_KEY")
            or os.getenv("DASHSCOPE_API_KEY")
            or os.getenv("QWEN_API_KEY")
        )
        if not resolved_api_key:
            raise ValueError(
                "TTS_API_KEY, DASHSCOPE_API_KEY, or QWEN_API_KEY is not configured"
            )

        dashscope.api_key = resolved_api_key
        dashscope.base_websocket_api_url = (
            websocket_url
            or os.getenv("TTS_WEBSOCKET_URL")
            or os.getenv("DASHSCOPE_WEBSOCKET_URL")
            or DEFAULT_WEBSOCKET_URL
        )

        self.model = (
            model
            or os.getenv("TTS_MODEL")
            or os.getenv("QWEN_TTS_MODEL")
            or DEFAULT_SPEECH_MODEL
        )
        self.voice = (
            os.getenv("TTS_VOICE")
            or os.getenv("QWEN_TTS_VOICE")
            or DEFAULT_SPEECH_VOICE
        )
        self.websocket_url = (
            websocket_url
            or os.getenv("TTS_WEBSOCKET_URL")
            or os.getenv("DASHSCOPE_WEBSOCKET_URL")
            or DEFAULT_WEBSOCKET_URL
        )
        self._speech_synthesizer_cls = SpeechSynthesizer
        self._audio_format_cls = AudioFormat

    def synthesize(
        self,
        text: str,
        voice: str = DEFAULT_SPEECH_VOICE,
        audio_format: str = "mp3",
    ) -> Dict[str, str]:
        normalized_format = audio_format.lower()
        if normalized_format != "mp3":
            raise ValueError("Only mp3 speech_format is currently supported")

        synthesizer = self._speech_synthesizer_cls(
            model=self.model,
            voice=voice or self.voice,
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
                f"model={self.model}, voice={voice or self.voice}, "
                f"websocket_url={self.websocket_url}, response={response}"
            )

        return {
            "audio_base64": base64.b64encode(audio_bytes).decode("utf-8"),
            "mime_type": "audio/mp3",
            "model": self.model,
            "voice": voice or self.voice,
        }
