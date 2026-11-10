
from ai.ai_manager import AIManager


def notify(level, message):
    print(f"[{level.upper()}] {message}")


manager = AIManager()

print("Generating recommendations for Japan...")

try:
    recommendations = manager.generate_recommendations(
        destination="Japan",
        user_inputs={
            "interests": ["Anime", "Nature"],
            "preferred_activities": ["Sightseeing"],
            "food_preferences": ["Ramen"],
        },
        notify=notify,
    )

    print("\nSUCCESS!")
    print(f"Total recommendations: {len(recommendations)}")

    for category in ["activity", "food", "accommodation", "shopping"]:
        items = [
            item for item in recommendations
            if item.get("type") == category
        ]

        print(f"\n{category.upper()} ({len(items)}):")

        for item in items[:3]:
            print(f" - {item.get('name')}")

except (ValueError, RuntimeError) as error:
    print(f"\nFAILED: {error}")
