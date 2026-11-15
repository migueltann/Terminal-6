"""AIErrorTranslator: turns technical AI errors into messages for users."""


class AIErrorTranslator:
    """Map an AI/API error to a short, friendly message.

    The AI clients raise errors with technical text. Known words in that
    text are looked for (in lowercase) and replaced with a plain message.
    The checks run in order, so the more specific ones go first.
    """

    SERVER_ERRORS = ("http 500", "http 502", "http 503", "http 504")

    @classmethod
    def friendly(cls, err) -> str:
        raw = str(err or "Unknown error")
        low = raw.lower()

        if "gemini_api_key" in low or (
                "api key" in low and ("missing" in low or "invalid" in low)):
            return ("Gemini API key is missing or invalid. "
                    "Add GEMINI_API_KEY=your_key to the project .env file, "
                    "then restart Flask.")

        # Gemini failed and the Groq backup failed (or is not set up).
        if "all ai providers failed" in low:
            if "groq_api_key" in low:
                return ("Gemini is temporarily unavailable and no Groq backup "
                        "is set up. Try again in a little while, or add "
                        "GROQ_API_KEY=your_key to the project .env file "
                        "and restart Flask.")
            return ("Gemini and the Groq backup are both unavailable right now. "
                    "Please try again in a little while.")

        if any(text in low for text in ("http 401", "http 403", "unauthorized", "permission")):
            return ("Gemini rejected the API key or its permissions. "
                    "Check GEMINI_API_KEY and ensure the key can use the Gemini API.")

        if any(text in low for text in ("http 429", "quota", "resource_exhausted")):
            return ("Gemini rate limit or quota reached. "
                    "Wait and try again, or check your API quota.")

        if "timed out" in low or "timeout" in low:
            return "The AI request timed out. Please try again."

        if "connection" in low or "network" in low:
            return ("Could not connect to Gemini. "
                    "Check your internet connection and try again.")

        if any(text in low for text in ("no usable recommendations", "malformed", "invalid json")):
            return ("Gemini returned an answer the app could not use. "
                    "Please try again.")

        if "all gemini models failed" in low or any(code in low for code in cls.SERVER_ERRORS):
            return ("Gemini is temporarily unavailable. "
                    "Please try again in a little while.")

        # Unknown error: show the original text.
        return f"Recommendation generation failed: {raw}"