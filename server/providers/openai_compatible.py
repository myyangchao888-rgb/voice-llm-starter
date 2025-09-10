from typing import Dict, List, Generator
from openai import OpenAI
from .base import LLMProvider

class OpenAICompatibleProvider(LLMProvider):
    def __init__(self, base_url: str, api_key: str, provider_name: str):
        self.client = OpenAI(base_url=base_url, api_key=api_key)
        self._name = provider_name

    def name(self) -> str:
        return self._name

    def stream_chat(self, messages: List[Dict[str, str]], model: str, **kwargs) -> Generator[str, None, None]:
        stream = self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            temperature=kwargs.get("temperature", 0.3),
            top_p=kwargs.get("top_p", 1.0),
        )
        for chunk in stream:
            try:
                delta = chunk.choices[0].delta
                if delta and delta.content:
                    yield delta.content
            except Exception:
                continue
