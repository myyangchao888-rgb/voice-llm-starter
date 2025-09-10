from abc import ABC, abstractmethod
from typing import Dict, List, Generator

class LLMProvider(ABC):
    @abstractmethod
    def stream_chat(self, messages: List[Dict[str, str]], model: str, **kwargs) -> Generator[str, None, None]:
        ...

    @abstractmethod
    def name(self) -> str:
        ...
