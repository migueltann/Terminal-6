import threading
import time

import pytest

from ai.ai_manager import AIManager, CATEGORIES
from ai.prompt_builder import PromptBuilder


class FakePromptBuilder:
    """Return the category as the prompt so calls are easy to check."""

    def build(self, destination, user_inputs=None, category=None):
        return f"{destination}:{category}"


class FakeAIClient:
    """Return 15 fake items per category, optionally after a delay."""

    def __init__(self, delay=0.0, fail_category=None, fail_times=None):
        self.delay = delay
        self.fail_category = fail_category
        # How many times fail_category fails; None means always.
        self.fail_times = fail_times
        self.calls = []
        self.thread_names = set()
        self._lock = threading.Lock()

    def generate(self, prompt, notify=None, validator=None, category=None):
        with self._lock:
            self.calls.append((prompt, category))
            self.thread_names.add(threading.current_thread().name)

        if notify is not None:
            notify("info", "working")

        time.sleep(self.delay)

        if category == self.fail_category and self.fail_times != 0:
            if self.fail_times is not None:
                self.fail_times -= 1
            raise RuntimeError(f"{category} failed")

        return [
            {"name": f"{category}-{i}", "type": category}
            for i in range(15)
        ]


def make_manager(client, **kwargs):
    kwargs.setdefault("retry_delay", 0)
    return AIManager(
        prompt_builder=FakePromptBuilder(),
        ai_client=client,
        **kwargs,
    )


def test_requests_every_category_once():
    client = FakeAIClient()

    make_manager(client).generate_recommendations("Japan")

    assert sorted(category for _, category in client.calls) == sorted(CATEGORIES)
    assert sorted(prompt for prompt, _ in client.calls) == sorted(
        f"Japan:{category}" for category in CATEGORIES
    )


def test_combines_results_in_category_order():
    result = make_manager(FakeAIClient()).generate_recommendations("Japan")

    assert len(result) == 60
    assert [item["type"] for item in result[::15]] == list(CATEGORIES)


def test_categories_run_in_parallel():
    """Four 0.5s requests should take about 0.5s, not 2s."""
    client = FakeAIClient(delay=0.5)

    start = time.perf_counter()
    make_manager(client).generate_recommendations("Japan")
    elapsed = time.perf_counter() - start

    assert elapsed < 1.5
    assert len(client.thread_names) == len(CATEGORIES)


def test_max_workers_one_runs_one_at_a_time():
    client = FakeAIClient()

    make_manager(client, max_workers=1).generate_recommendations("Japan")

    assert len(client.thread_names) == 1
    assert len(client.calls) == len(CATEGORIES)


def test_failure_in_one_category_is_raised():
    client = FakeAIClient(fail_category="food")

    with pytest.raises(RuntimeError, match="food failed"):
        make_manager(client).generate_recommendations("Japan")


def test_status_messages_are_labelled_with_category():
    messages = []
    lock = threading.Lock()

    def notify(level, message):
        with lock:
            messages.append(message)

    make_manager(FakeAIClient()).generate_recommendations(
        "Japan", notify=notify
    )

    assert sorted(messages) == sorted(
        f"[{category}] working" for category in CATEGORIES
    )


def test_empty_destination_is_rejected():
    client = FakeAIClient()

    with pytest.raises(ValueError):
        make_manager(client).generate_recommendations("  ")

    assert client.calls == []


def test_invalid_max_workers_is_rejected():
    with pytest.raises(ValueError):
        make_manager(FakeAIClient(), max_workers=0)


def test_category_prompt_only_mentions_that_category():
    prompt = PromptBuilder().build(
        "Japan",
        {
            "food_preferences": ["ramen"],
            "shopping_preferences": ["anime figures"],
        },
        category="food",
    )

    assert "exactly 15 food recommendation" in prompt
    assert '"ramen"' in prompt
    assert "anime figures" not in prompt
    assert "exactly 60" not in prompt


def test_prompt_without_category_still_asks_for_60():
    prompt = PromptBuilder().build("Japan")

    assert "exactly 60" in prompt


def test_unknown_category_prompt_is_rejected():
    with pytest.raises(ValueError):
        PromptBuilder().build("Japan", category="nightlife")


def test_failed_category_is_retried_once():
    client = FakeAIClient(fail_category="food", fail_times=1)
    messages = []

    result = make_manager(client).generate_recommendations(
        "Japan", notify=lambda level, message: messages.append(message)
    )

    assert len(result) == 60
    assert [category for _, category in client.calls].count("food") == 2
    assert any(
        message.startswith("[food] All models failed")
        for message in messages
    )


def test_category_that_keeps_failing_stops_after_attempts():
    client = FakeAIClient(fail_category="food")

    with pytest.raises(RuntimeError, match="food failed"):
        make_manager(client, category_attempts=3).generate_recommendations(
            "Japan"
        )

    assert [category for _, category in client.calls].count("food") == 3


def test_invalid_category_attempts_is_rejected():
    with pytest.raises(ValueError):
        make_manager(FakeAIClient(), category_attempts=0)
