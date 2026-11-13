
import os

import pytest

from ai.ai_manager import AIManager


def notify(level, message):
    print(f"[{level.upper()}] {message}")


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_AI_TESTS") != "1",
    reason="Live AI test disabled. Set RUN_LIVE_AI_TESTS=1 to enable.",
)
def test_live_ai_recommendations():
    """Run real AI generation only when explicitly enabled."""

    if not (os.getenv("GEMINI_API_KEY") or os.getenv("GROQ_API_KEY")):
        pytest.skip("No AI API key configured")

    manager = AIManager()

    print("Generating recommendations for Japan...")

    recommendations = manager.generate_recommendations(
        destination="Japan",
        user_inputs={
            "interests": ["Anime", "Nature"],
            "preferred_activities": ["Sightseeing"],
            "food_preferences": ["Ramen"],
        },
        notify=notify,
    )

    assert len(recommendations) == 60

    for category in ("activity", "food", "accommodation", "shopping"):
        items = [
            item for item in recommendations
            if item.get("type") == category
        ]

        assert len(items) == 15

        print(f"\n{category.upper()} ({len(items)}):")

        for item in items[:3]:
            print(f" - {item.get('name')}")
