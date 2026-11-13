from typing import Callable, Optional, Protocol


# A Protocol describes the methods a class must have, without making it
# inherit from anything ("duck typing"). GeminiClient, GroqClient and
# FallbackClient all have this generate() method, so AIManager can use
# any of them interchangeably.
class AIClient(Protocol):
    """Anything with this generate() method can be used as a provider."""

    def generate(
        self,
        prompt: str,
        notify: Optional[Callable[[str, str], None]] = None,
        validator: Optional[Callable[[list[dict]], bool]] = None,
        category: Optional[str] = None,
    ) -> list[dict]:
        ...


class FallbackClient:
    """Try AI providers in order until one of them succeeds.

    Used as Gemini first, then Groq as a backup when every Gemini model
    is busy or the Gemini key is missing.

    Each of the four category threads in AIManager calls generate()
    separately, so one category can switch to Groq while the others
    still succeed on Gemini.
    """

    def __init__(self, providers: list[tuple[str, AIClient]]):
        # providers is an ordered list of (display name, client) pairs,
        # e.g. [("Gemini", GeminiClient()), ("Groq", GroqClient())].
        if not providers:
            raise ValueError("At least one AI provider is required.")

        self._providers = providers

    def generate(
        self,
        prompt: str,
        notify: Optional[Callable[[str, str], None]] = None,
        validator: Optional[Callable[[list[dict]], bool]] = None,
        category: Optional[str] = None,
    ) -> list[dict]:
        """Return the first provider's successful result."""

        # Keep every provider's error so the final message explains
        # why each one failed.
        errors = []

        for index, (name, client) in enumerate(self._providers):
            try:
                # The first provider that succeeds ends the loop here.
                return client.generate(
                    prompt,
                    notify=notify,
                    validator=validator,
                    category=category,
                )

            # RuntimeError: the provider failed.
            # ValueError: the provider is not set up (e.g. missing key).
            except (RuntimeError, ValueError) as err:
                errors.append(f"{name}: {err}")

                # Tell the user we are moving on, if there is a next one.
                if index + 1 < len(self._providers) and notify is not None:
                    next_name = self._providers[index + 1][0]
                    notify(
                        "warning",
                        f"{name} failed. Switching to {next_name}...",
                    )

        # Every provider failed. web_app.py looks for the text
        # "All AI providers failed" to show a friendly error message.
        raise RuntimeError(
            "All AI providers failed. " + " | ".join(errors)
        )
