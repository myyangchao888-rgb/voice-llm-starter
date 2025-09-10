from abc import ABC, abstractmethod
from typing import Dict, List, Generator, Any

class LLMProvider(ABC):
    @abstractmethod
    def stream_chat(self, messages: List[Dict[str, str]], model: str, **kwargs) -> Generator[str, None, None]:
        """
        Yield partial text segments (tokens) as they arrive.
        """
        ...

    @abstractmethod
    def name(self) -> str:
        ...
