"""IO Manager: every terminal input and output shown to the user."""

from typing import Any, Optional

from models import Recommendation, RecommendationSet, UserRequirements
from user_io.destination_validator import DestinationValidator


class IOManager:
    """Collects and validates user input, and displays results in the terminal."""

    EXIT_COMMANDS = {"exit", "e"}
    BACK_COMMANDS = {"back", "b"}
    LINE = "=" * 70
    DIVIDER = "-" * 70

    # Returned by the ask methods when the user types 'back'
    _BACK = object()

    # Order the questions are asked in.
    # (data key, label in the edit menu, kind of question, heading shown before it)
    _STEPS = [
        ("destination", "Destination", "destination", "DESTINATION"),
        ("preferred_activities", "Activity preferences", "list", "ACTIVITIES"),
        ("max_activity_spend", "Activity budget", "money", None),
        ("activity_environment", "Activity environment", "environment", None),
        ("food_preferences", "Cuisine preferences", "list", "FOOD"),
        ("max_meal_spend", "Meal budget", "money", None),
        ("food_environment", "Food environment", "environment", None),
        ("dietary", "Dietary requirement", "dietary", None),
        ("accommodation_preferences", "Accommodation preferences", "list", "ACCOMMODATION"),
        ("max_accommodation_spend", "Accommodation budget", "money", None),
        ("shopping_preferences", "Shopping preferences", "list", "SHOPPING"),
        ("max_shopping_spend", "Shopping budget", "money", None),
        ("shopping_environment", "Shopping environment", "environment", None),
        ("preferred_transport", "Universal transport", "transport", "UNIVERSAL RESTRICTIONS"),
        ("avoid_list", "Places to avoid", "list", None),
    ]

    # Prompt text and hint lines for each question
    _PROMPTS = {
        "preferred_activities": ("Preferred activities (comma-separated) [Any]: ", [
            "Preferred activities are specific activity types.",
            "Examples: museums, hiking, theme parks, water activities, nightlife, food tours."]),
        "food_preferences": ("Cuisine preferences (comma-separated) [Any]: ", [
            "What types of food do you enjoy?",
            "Examples: Japanese, Korean, Italian, Thai, Local food."]),
        "accommodation_preferences": ("Accommodation preferences (comma-separated) [Any]: ", [
            "Accommodation preferences are the type of stay you want.",
            "Examples: hotel, hostel, budget motel, guesthouse, serviced apartment, near MRT."]),
        "shopping_preferences": ("Shopping preferences (comma-separated) [Any]: ", [
            "Shopping preferences are the things or places you like to shop.",
            "Examples: fashion, electronics, souvenirs, malls, street markets, local crafts."]),
        "avoid_list": ("Avoid list (comma-separated) [None]: ", [
            "The avoid list is types of activities or places you do not want recommended.",
            "Examples: nightlife, theme parks, water activities, shopping malls, hiking."]),
        "max_activity_spend": ("Max spend per activity (SGD): ", []),
        "max_meal_spend": ("Max spend per meal (SGD): ", []),
        "max_accommodation_spend": ("Max spend per night for accommodation (SGD): ", []),
        "max_shopping_spend": ("Max shopping spend (SGD): ", []),
        "activity_environment": ("Activity environment (Indoor/Outdoor/Any) [Any]: ", []),
        "food_environment": ("Food environment (Indoor/Outdoor/Any) [Any]: ", []),
        "shopping_environment": ("Shopping environment (Indoor/Outdoor/Any) [Any]: ", []),
    }

    _LIST_DEFAULTS = {
        "preferred_activities": "Any", "food_preferences": "Any",
        "accommodation_preferences": "Any", "shopping_preferences": "Any",
        "avoid_list": "None",
    }

    def __init__(self) -> None:
        # Composition: the IOManager creates and owns its validator
        self.__validator = DestinationValidator()