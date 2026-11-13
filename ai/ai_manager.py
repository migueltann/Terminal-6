# ThreadPoolExecutor runs functions in a pool of background threads and
# gives back a "future" for each one: a placeholder for its result.
from concurrent.futures import ThreadPoolExecutor
import time
from typing import Any, Callable, Optional

from ai.prompt_builder import PromptBuilder
from ai.fallback_client import AIClient, FallbackClient
from ai.gemini_client import GeminiClient
from ai.groq_client import GroqClient


# The 60 recommendations are split into these four categories of 15.
# One AI request is sent per category, and the results are combined
# in this order.
CATEGORIES = ("activity", "food", "accommodation", "shopping")


class AIManager:
    """Coordinate prompt building and AI recommendation generation."""

    def __init__(
        self,
        prompt_builder: Optional[PromptBuilder] = None,
        ai_client: Optional[AIClient] = None,
        max_workers: int = len(CATEGORIES),
        category_attempts: int = 2,
        retry_delay: float = 5,
    ):
        self._prompt_builder = prompt_builder or PromptBuilder()

        # The AI provider used for every request. By default this is a
        # FallbackClient: Gemini is tried first, and Groq is only used
        # if every Gemini model fails (or the Gemini key is missing).
        # Tests pass in a fake client here so no real API is called.
        self._ai_client = ai_client or FallbackClient([
            ("Gemini", GeminiClient()),
            ("Groq", GroqClient()),
        ])

        if max_workers < 1:
            raise ValueError("max_workers must be at least 1.")

        # How many threads (requests) may run at the same time.
        # 4 = all categories at once. Lower this (e.g. to 2) if the AI
        # often replies HTTP 429 (too many requests).
        self._max_workers = max_workers

        if category_attempts < 1:
            raise ValueError("category_attempts must be at least 1.")

        # When Gemini is overloaded (HTTP 503), one category can run out
        # of models while the others succeed. Going through the models
        # again a little later usually works, instead of failing the trip.
        self._category_attempts = category_attempts
        self._retry_delay = retry_delay

    def generate_recommendations(
        self,
        destination: str,
        user_inputs: Optional[dict] = None,
        notify: Optional[Callable[[str, str], None]] = None,
        validator: Optional[Callable[[list[dict]], Any]] = None,
    ) -> list[dict]:
        """Request each category from the AI at the same time.

        Instead of one large request for all 60 recommendations, four
        smaller requests (15 each) run in separate threads. The threads
        spend almost all their time waiting for the AI to reply, so they
        overlap and the total time is close to the slowest single request.

        Why threads help here: this work is I/O-bound (waiting on the
        network), not CPU-bound. Python releases its Global Interpreter
        Lock (GIL) while a thread waits for a network reply, so the four
        requests really do wait in parallel.

        If any category fails, the error is raised and no partial
        result is returned.
        """

        if not isinstance(destination, str) or not destination.strip():
            raise ValueError("Destination cannot be empty.")

        destination = destination.strip()

        # The job each worker thread runs: generate the 15
        # recommendations for ONE category. It is defined inside this
        # method so it can use destination, user_inputs, notify and
        # validator directly.
        def generate_category(category: str) -> list[dict]:
            # Build a prompt asking for only this category's 15 items.
            prompt = self._prompt_builder.build(
                destination,
                user_inputs,
                category=category,
            )

            # Status messages from this thread get a "[category]" prefix,
            # so the four threads' messages can be told apart.
            labelled_notify = self._label_notify(notify, category)

            # Try the whole provider chain (Gemini -> Groq) up to
            # category_attempts times before giving up on this category.
            for attempt in range(1, self._category_attempts + 1):
                try:
                    return self._ai_client.generate(
                        prompt,
                        notify=labelled_notify,
                        validator=validator,
                        category=category,
                    )
                except RuntimeError:
                    # Last attempt used up: pass the error on, which
                    # makes future.result() below raise it.
                    if attempt == self._category_attempts:
                        raise

                    if labelled_notify is not None:
                        labelled_notify(
                            "warning",
                            "All models failed. Trying again in "
                            f"{self._retry_delay:g} seconds...",
                        )

                    # Only this thread sleeps; the other categories
                    # keep running.
                    time.sleep(self._retry_delay)

        # Create the thread pool. The "with" block waits for every
        # thread to finish before continuing, and then shuts the pool down.
        with ThreadPoolExecutor(
            max_workers=self._max_workers,
            thread_name_prefix="gemini",
        ) as pool:
            # submit() starts generate_category(...) in a worker thread
            # straight away and returns a Future. All four requests are
            # now running at the same time.
            futures = [
                pool.submit(generate_category, category)
                for category in CATEGORIES
            ]

            try:
                # result() waits for each thread and re-raises its error.
                # Reading the futures in list order keeps the results in
                # CATEGORIES order, whichever thread finishes first.
                batches = [future.result() for future in futures]
            except Exception:
                # Do not start categories that are still queued.
                # (Threads that are already running cannot be stopped,
                # so the "with" block still waits for them to finish.)
                for future in futures:
                    future.cancel()
                raise

        # Combine in a fixed order: activity, food, accommodation, shopping.
        # batches is a list of four lists of 15; this flattens it to 60.
        return [item for batch in batches for item in batch]

    @staticmethod
    def _label_notify(
        notify: Optional[Callable[[str, str], None]],
        category: str,
    ) -> Optional[Callable[[str, str], None]]:
        """Prefix status messages with the category of their thread."""

        if notify is None:
            return None

        # A small wrapper function (a closure) that remembers category
        # and adds it to the front of every message before passing it on,
        # e.g. "[food] Trying Gemini model: ...".
        def labelled(level: str, message: str) -> None:
            notify(level, f"[{category}] {message}")

        return labelled
