"""AIClient: the interface every AI provider must follow."""
from abc import ABC, abstractmethod
from typing import Callable, Optional


class AIClient(ABC):
    """Interface (contract) for an AI provider: it must be able to generate().

    This is a "must be able to do" relationship, not an "is-a" one, so it
    is an interface written as an ABC with only an abstract method (the
    Python approach from the lectures). GeminiClient, GroqClient and
    FallbackClient all implement it, so AIManager can use any of them
    without knowing which one it has (polymorphism).
    """

    @abstractmethod
    def generate(
        self,
        prompt: str,
        notify: Optional[Callable[[str, str], None]] = None,
        validator: Optional[Callable[[list[dict]], bool]] = None,
        category: Optional[str] = None,
    ) -> list[dict]:
        """Return validated recommendations for the prompt.

        Raises RuntimeError if the provider failed, or ValueError if it
        is not set up (for example its API key is missing).
        """