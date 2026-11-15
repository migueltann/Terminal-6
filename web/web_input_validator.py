"""WebInputValidator: checks the web form the same way IOManager checks the terminal."""

import math
from typing import Optional

from user_io.destination_validator import DestinationValidator


class WebInputValidator:
    """Validate and clean the requirements form sent by the browser.

    The page only offers valid choices, but a request can be edited by
    hand, so the server checks everything again before the AI is called.
    """

    # Form fields typed as comma-separated lists
    LIST_FIELDS = ("preferred_activities", "food_preferences",
                   "accommodation_preferences", "shopping_preferences", "avoid_list")

    # (form field name, label used in error messages)
    BUDGET_FIELDS = (
        ("max_activity_spend", "Max spend per activity"),
        ("max_meal_spend", "Max spend per meal"),
        ("max_accommodation_spend", "Max spend per night for accommodation"),
        ("max_shopping_spend", "Max shopping spend"),
    )

    ENVIRONMENT_FIELDS = (
        ("activity_environment", "Activity environment"),
        ("food_environment", "Food environment"),
        ("shopping_environment", "Shopping environment"),
    )

    ENVIRONMENTS = ("Indoor", "Outdoor", "Any")
    TRANSPORTS = ("Walk", "Transit", "Taxi", "Any")

    def __init__(self, destination_validator: Optional[DestinationValidator] = None) -> None:
        # Loading the country/city lists takes a moment, so it is done once
        # here instead of on every request.
        self.__destinations = destination_validator or DestinationValidator()

    def check_destination(self, text: str) -> tuple[Optional[str], Optional[str]]:
        """(clean destination, None) if valid, otherwise (None, error)."""
        return self.__destinations.validate(text)

    @staticmethod
    def _split_list(value) -> list[str]:
        """Convert comma-separated form input into a clean list."""
        values = [part.strip() for part in (value or "").split(",") if part.strip()]
        # "Any" or "None" anywhere means no preference at all.
        if any(part.lower() in {"any", "none"} for part in values):
            return []
        return values

    @staticmethod
    def _optional_text(value) -> Optional[str]:
        """Blank, "Any" and "None" become None."""
        text = str(value or "").strip()
        return None if text.lower() in {"", "any", "none"} else text

    def collect(self, form) -> tuple[dict, list[str], dict[str, str]]:
        """Validate and normalise the same requirements as the terminal.

        Returns (data, errors, field_errors):
        - data: the cleaned inputs, ready for UserRequirements.from_dict()
        - errors: a list of every error message (empty if all is valid)
        - field_errors: field name -> its error, so the page can highlight it
        """
        errors: list[str] = []
        field_errors: dict[str, str] = {}

        destination_raw = (form.get("destination") or "").strip()
        destination, destination_error = self.check_destination(destination_raw)
        if destination_error:
            errors.append(destination_error)
            field_errors["destination"] = destination_error

        data: dict = {"destination": destination or destination_raw}

        for key in self.LIST_FIELDS:
            data[key] = self._split_list(form.get(key, ""))

        # Budgets must be finite numbers greater than zero.
        for key, label in self.BUDGET_FIELDS:
            raw = (form.get(key) or "").strip()
            try:
                number = float(raw)
                if not math.isfinite(number) or number <= 0:
                    raise ValueError
                data[key] = number
            except (ValueError, TypeError):
                message = "Please enter a valid positive amount."
                errors.append(f"{label}: {message}")
                field_errors[key] = message
                data[key] = None

        for key, label in self.ENVIRONMENT_FIELDS:
            # .title() turns "indoor" into "Indoor" to match ENVIRONMENTS.
            value = (form.get(key) or "Any").strip().title()
            if value not in self.ENVIRONMENTS:
                message = f"{label} must be Indoor, Outdoor, or Any."
                errors.append(message)
                field_errors[key] = message
                value = "Any"
            data[key] = value

        transport = (form.get("preferred_transport") or "Any").strip().title()
        if transport not in self.TRANSPORTS:
            message = "Transport must be Walk, Transit, Taxi, or Any."
            errors.append(message)
            field_errors["preferred_transport"] = message
            transport = "Any"
        data["preferred_transport"] = transport

        # "Other" in the dropdown means the user typed their own diet in a
        # separate text box.
        dietary = self._optional_text(form.get("dietary")) or "None"
        if dietary == "Other":
            dietary = self._optional_text(form.get("dietary_custom")) or "None"
        data["dietary"] = dietary

        return data, errors, field_errors