
"""OpenAI-compatible LLM API client.

Uses ``llm_env`` for all configuration — no provider-specific defaults.
"""

import json
from typing import Any, Dict, Iterator, List, Optional

from openai import OpenAI

from app.llm import llm_env


class LLMClient:
    """Thin wrapper around the OpenAI-compatible chat-completions endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        resolved_api_key = api_key or llm_env.get_llm_api_key()
        self.model = model or llm_env.get_llm_model()
        self.client = OpenAI(
            api_key=resolved_api_key,
            base_url=base_url or llm_env.get_llm_base_url(),
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def complete_with_tools(
        self,
        messages: List[Dict[str, Any]],
        tools: List[Dict[str, Any]],
        tool_choice: str = "auto",
        temperature: float = 0,
    ) -> Dict[str, Any]:
        """Send a chat-completion request with tool definitions.

        Returns a dict with ``content``, ``assistant_message``,
        ``tool_calls``, and ``raw_response``.
        """
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            tool_choice=tool_choice,
            temperature=temperature,
        )
        message = response.choices[0].message
        return {
            "content": message.content,
            "assistant_message": {
                "role": "assistant",
                "content": message.content or "",
                "tool_calls": [
                    {
                        "id": call.id,
                        "type": "function",
                        "function": {
                            "name": call.function.name,
                            "arguments": call.function.arguments,
                        },
                    }
                    for call in (message.tool_calls or [])
                ],
            },
            "tool_calls": [
                {
                    "id": call.id,
                    "name": call.function.name,
                    "arguments": json.loads(call.function.arguments),
                }
                for call in (message.tool_calls or [])
            ],
            "raw_response": response.model_dump(),
        }

    def complete(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0,
    ) -> Dict[str, Any]:
        """Send a plain chat-completion request (no tools)."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        message = response.choices[0].message
        return {
            "content": message.content or "",
            "raw_response": response.model_dump(),
        }

    def stream_complete(
        self,
        messages: List[Dict[str, Any]],
        temperature: float = 0,
    ) -> Iterator[str]:
        """Stream text deltas from a plain chat-completion request."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        try:
            for chunk in response:
                if not chunk.choices:
                    continue
                content = chunk.choices[0].delta.content
                if content:
                    yield content
        finally:
            close = getattr(response, "close", None)
            if callable(close):
                close()
