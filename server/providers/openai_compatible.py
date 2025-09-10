import os
from typing import Dict, List, Generator, Any, Optional
from openai import OpenAI
from .base import LLMProvider

class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, provider_name: str):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self._name = provider_name

    def name(self) -> str:
        return self._name

    def stream_chat(self, messages: List[Dict[str, str]], model: str, **kwargs) -> Generator[str, None, None]:
        # kwargs may include temperature, top_p, etc.
        # The OpenAI Python SDK v1+ supports streaming via iterating over the response.
        # We normalize messages (role/content) into the format Chat Completions expects.
        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=kwargs.get("temperature", 0.7),
            top_p=kwargs.get("top_p", 1.0),
        )
        for chunk in stream:
            try:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
            except Exception:
                continue
