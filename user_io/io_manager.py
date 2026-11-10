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

    def show_welcome(self) -> None:
        """Show the title when the program starts."""
        print(self.LINE)
        print("              TRAVEL RECOMMENDATION ASSISTANT")
        print("     AI discovers places; Python checks your requirements")
        print(self.LINE)
        print("Press Enter to use the default shown in [ ] at the end of a prompt.\n")
        print("Type 'back' or 'b' at an input prompt to return to the previous input.\n")
        print("Type 'exit' or 'e' at an input prompt to return to the main menu.\n")

    def show_menu(self) -> str:
        """Show the main menu and return the user's choice: '1', '2' or '3'."""
        print("\nMAIN MENU")
        print("1. Generate Recommendations")
        print("2. View / Delete Saved Recommendation Sets")
        print("3. Exit")
        while True:
            choice = input("\nEnter choice (1-3): ").strip().lower()
            if choice in {"1", "2", "3"}:
                return choice
            if choice in self.EXIT_COMMANDS:
                return "3"
            print("Invalid choice. Please enter 1, 2, or 3.")

    def show_message(self, message: str) -> None:
        """Show a normal information message."""
        print(f"\n[INFO] {message}")

    def show_error(self, message: str) -> None:
        """Show an error message."""
        print(f"\n[ERROR] {message}")

    def show_status(self, level: str, message: str) -> None:
        """Show an INFO or WARNING line sent by another manager (used as the AI notifier)."""
        print(f"\n[{str(level).upper()}] {message}")

    @classmethod
    def _is_exit(cls, value: str) -> bool:
        return str(value).strip().lower() in cls.EXIT_COMMANDS

    @classmethod
    def _is_back(cls, value: str) -> bool:
        return str(value).strip().lower() in cls.BACK_COMMANDS

    def _ask_text(self, prompt: str, default: str = "", allow_back: bool = False) -> Any:
        """Ask for optional text. Returns the default if blank, None on exit, _BACK on back."""
        value = input(prompt).strip()
        if self._is_exit(value):
            return None
        if allow_back and self._is_back(value):
            return self._BACK
        return value if value else default

    def _ask_positive_float(self, prompt: str, allow_back: bool = False) -> Any:
        """Ask for an amount greater than 0. Keeps asking until it is valid."""
        while True:
            value = input(prompt).strip()
            if self._is_exit(value):
                return None
            if allow_back and self._is_back(value):
                return self._BACK
            try:
                number = float(value)
                if number > 0 and number != float("inf"):
                    return number
            except ValueError:
                pass
            print("Please enter a valid positive amount.")

    def _ask_choice(self, prompt: str, choices: list[str], default: str, allow_back: bool = False) -> Any:
        """Ask the user to pick from a fixed list. Blank uses the default."""
        lowered = [choice.lower() for choice in choices]
        while True:
            value = input(prompt).strip()
            if self._is_exit(value):
                return None
            if allow_back and self._is_back(value):
                return self._BACK
            if not value:
                return default
            if value.lower() in lowered:
                return choices[lowered.index(value.lower())]
            print("Invalid choice. Options: " + ", ".join(choices))

    def _ask_list(self, prompt: str, hints: list[str], allow_back: bool = False) -> Any:
        """Show the hint lines, then ask for a comma-separated list."""
        for line in hints:
            print(line)
        value = self._ask_text(prompt, allow_back=allow_back)
        if value is None or value is self._BACK:
            return value
        return [part.strip() for part in value.split(",") if part.strip()]

    def ask_yes_no(self, prompt: str) -> Optional[bool]:
        """Ask a yes/no question. Returns None if the user types exit."""
        while True:
            value = input(prompt).strip().lower()
            if self._is_exit(value):
                return None
            if value in {"y", "yes"}:
                return True
            if value in {"n", "no"}:
                return False
            print("Please enter y or n.")

