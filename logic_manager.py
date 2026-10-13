import re
import math
from difflib import SequenceMatcher

"""Filters generic AI recommendations using the user's requirements."""

def _normalise(value):
    """Convert text to lowercase so comparisons are easier."""
    value = str(value or "").strip().lower()
    value = re.sub(r"[_\-]+", " ", value)
    value = re.sub(r"[^\w\s]", " ", value)
    return " ".join(value.split())

def _active_preferences(values):
    """Remove empty answers and placeholder values from a preference list."""
    if not isinstance(values, list):
        return []
    return [
        str(value).strip()
        for value in values
        if _normalise(value) not in {"", "any", "none"}
    ]

def _as_text_list(value):
    """Return a safe list of non-empty strings."""
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]

def _recommendation_text(item):
    """Collect recommendation fields that can describe its relevance."""
    fields = [
        item.get("name", ""),
        item.get("category", ""),
        item.get("description", ""),
        item.get("location", ""),
    ]
    for key in (
        "tags",
        "shopping_types",
        "shopping_interests",
        "interests",
        "activity_types",
        "themes",
        "keywords",
    ):
        fields.extend(_as_text_list(item.get(key, [])))
    return _normalise(" ".join(str(field) for field in fields))


def _preference_matches_text(preference, text):
    """
    Generic text matching:
    1. exact phrase match;
    2. word overlap;
    3. conservative fuzzy matching for short text fields.

    """
    pref = _normalise(preference)
    searchable = _normalise(text)

    if not pref or not searchable:
        return False

    if pref in searchable:
        return True

    pref_words = set(pref.split())
    text_words = set(searchable.split())

    # Word overlap works for multi-word preferences when the recommendation
    # uses some of the same meaningful words.
    if pref_words and pref_words.issubset(text_words):
        return True

    # Fuzzy matching helps with minor spelling/word-form differences only.
    # It is not a substitute for semantic matching.
    if len(pref) >= 5:
        for candidate in re.split(r"[,;|]", searchable):
            candidate = candidate.strip()
            if candidate and SequenceMatcher(None, pref, candidate).ratio() >= 0.88:
                return True

    return False

def matches_shopping_preference(item, preference):
    """Match a shopping preference against generated shopping tags and text."""
    shopping_text = " ".join(
        _as_text_list(item.get("shopping_types", []))
        + _as_text_list(item.get("shopping_interests", []))
        + _as_text_list(item.get("tags", []))
        + [str(item.get("name", "")), str(item.get("category", "")),
           str(item.get("description", ""))]
    )
    return _preference_matches_text(preference, shopping_text)

def _contains_term(item, term):
    """Check whether a term appears in searchable recommendation fields."""
    return _preference_matches_text(term, _recommendation_text(item))


def _matching_field(item, preference, field_names):
    """Return the first field that matches a preference, or None."""
    for field in field_names:
        value = item.get(field, "")

        if isinstance(value, list):
            values = _as_text_list(value)
        else:
            values = [str(value)] if value else []

        for candidate in values:
            if _preference_matches_text(preference, candidate):
                return field

    return None


def validate_ai_response(raw_items):
    """Keep only AI recommendations that have the fields needed downstream."""
    if not isinstance(raw_items, list):
        return []

    valid_items = []
    allowed_types = {"activity", "food", "accommodation", "shopping"}

    required = [
        "name", "type", "category", "estimated_cost_sgd", "location",
        "environment", "description", "tags",
        "transport_options", "dietary_tags",
    ]   

    for item in raw_items:
        if not isinstance(item, dict) or not all(key in item for key in required):
            continue

        item_type = _normalise(item["type"])
        if item_type not in allowed_types:
            continue

        environment = _normalise(item["environment"])

        if environment not in {"indoor", "outdoor"}:
            continue

        try:
            cost = float(item["estimated_cost_sgd"])
        except (TypeError, ValueError):
            continue
        if not math.isfinite(cost) or cost < 0:
            continue

        if not all(isinstance(item[key], list) for key in (
            "tags", "transport_options", "dietary_tags"
        )):
            continue

        if item_type == "shopping":
            if not isinstance(item.get("shopping_types"), list):
                continue
            if not isinstance(item.get("shopping_interests"), list):
                continue
            if not all(isinstance(value, str) for value in (
                item["shopping_types"] + item["shopping_interests"]
            )):
                continue

        cleaned = dict(item)
        cleaned["name"] = str(item["name"]).strip()
        cleaned["type"] = item_type
        cleaned["category"] = str(item["category"]).strip()
        cleaned["estimated_cost_sgd"] = cost
        cleaned["location"] = str(item["location"]).strip()
        cleaned["environment"] = environment.title()
        cleaned["description"] = str(item["description"]).strip()

        for key in ("tags", "transport_options", "dietary_tags",
                    "shopping_types", "shopping_interests",
                    "interests", "activity_types", "themes", "keywords"):
            if key in cleaned:
                if not isinstance(cleaned[key], list):
                    cleaned[key] = []
                else:
                    cleaned[key] = [
                        _normalise(value)
                        for value in cleaned[key]
                        if str(value).strip()
                    ]

        valid_items.append(cleaned)

    return valid_items

def _budget_for_item(item, user_inputs):
    """Select the correct budget for a recommendation type."""

    mapping = {
        "activity": (
            "max_activity_spend",
            "Activity budget",
        ),
        "food": (
            "max_meal_spend",
            "Meal budget",
        ),
        "accommodation": (
            "max_accommodation_spend",
            "Accommodation budget",
        ),
        "shopping": (
            "max_shopping_spend",
            "Shopping budget",
        ),
    }

    key, label = mapping[item["type"]]
    return float(user_inputs[key]), label

def _preferences_for_item(item, user_inputs):
    """Return the user's preferences for the item's category."""

    keys = {
        "activity": "preferred_activities",
        "food": "food_preferences",
        "accommodation": "accommodation_preferences",
        "shopping": "shopping_preferences",
    }
    return _active_preferences(user_inputs.get(keys[item["type"]], []))


def is_top_pick(item, user_inputs, passed_all_checks):
    """Multi-condition rule using AI output fields.

    A recommendation is a top pick only when ALL three are true:
    1. it passed every hard restriction,
    2. its AI-generated tags/text match one of the user's preferences,
    3. its AI-estimated cost is at most half of the category budget.
    """

    if not passed_all_checks:
        return False

    limit, _ = _budget_for_item(item, user_inputs)
    within_half_budget = item["estimated_cost_sgd"] <= 0.5 * limit

    matches_preference = any(
        _contains_term(item, preference)
        for preference in _preferences_for_item(item, user_inputs)
    )

    return within_half_budget and matches_preference

def evaluate_recommendation(item, user_inputs):
    """Apply hard restrictions and record pass/fail explanations."""
    checks = []
    keep = True

    # 1. Category-specific budget restriction
    cost = item["estimated_cost_sgd"]
    limit, label = _budget_for_item(item, user_inputs)

    passed = cost <= limit

    checks.append({
        "label": label,
        "passed": passed,
        "detail": (
            f"${cost:.2f} <= ${limit:.2f}"
            if passed else
            f"${cost:.2f} > ${limit:.2f}"
        ),
    })

    keep = keep and passed

    # 2. Category-specific environment restriction
    environment_keys = {
        "activity": "activity_environment",
        "food": "food_environment",
        "shopping": "shopping_environment",
    }

    environment_key = environment_keys.get(item["type"])

    required_environment = (
        _normalise(user_inputs.get(environment_key, "Any"))
        if environment_key else "any"
    )

    actual_environment = _normalise(item["environment"])

    if required_environment not in {"", "any", "none"}:
        passed = actual_environment == required_environment

        checks.append({
            "label": "Environment",
            "passed": passed,
            "detail": (
                f"{actual_environment.title()} matches "
                f"{required_environment.title()}"
                if passed else
                f"{actual_environment.title()} does not match "
                f"{required_environment.title()}"
            ),
        })

        keep = keep and passed

    # 3. Universal avoid-list restriction
    avoided_terms = [
        term
        for term in _active_preferences(
            user_inputs.get("avoid_list", [])
        )
        if _contains_term(item, term)
    ]

    passed = not avoided_terms

    checks.append({
        "label": "Avoid list",
        "passed": passed,
        "detail": (
            "No avoided match"
            if passed else
            "Matched: " + ", ".join(avoided_terms)
        ),
    })

    keep = keep and passed

    # 4. Dietary restriction (food only)
    dietary = _normalise(
        user_inputs.get("dietary", "Any")
    )

    if item["type"] == "food" and dietary not in {"", "none", "any"}:
        passed = dietary in item.get("dietary_tags", [])

        checks.append({
            "label": "Dietary requirement",
            "passed": passed,
            "detail": (
                f"{dietary} supported"
                if passed else
                f"{dietary} not listed"
            ),
        })

        keep = keep and passed

    # 5. Universal transport restriction
    preferred_transport = _normalise(
        user_inputs.get("preferred_transport", "Any")
    )

    if preferred_transport not in {"", "any", "none"}:
        passed = preferred_transport in item.get(
            "transport_options", []
        )

        checks.append({
            "label": "Transport preference",
            "passed": passed,
            "detail": (
                f"{preferred_transport} available"
                if passed else
                f"{preferred_transport} not listed"
            ),
        })

        keep = keep and passed

    # 6. Return final decision and audit details
    return {
        "item": item,
        "keep": keep,
        "eligible": keep,
        "top_pick": is_top_pick(item, user_inputs, keep),
        "checks": checks,
        "passed_rules": [
            check["label"]
            for check in checks
            if check["passed"]
        ],
        "failed_rules": [
            check["label"]
            for check in checks
            if not check["passed"]
        ],
    }


def filter_recommendations(items, user_inputs):
    """Split recommendations into eligible and rejected lists with audit details."""
    approved, rejected, audit = [], [], []

    for item in items:
        decision = evaluate_recommendation(item, user_inputs)
        audit.append(decision)
        result_item = dict(item)

        for key in (
            "eligible",
            "top_pick",
            "checks",
            "passed_rules",
            "failed_rules",
        ):
            result_item[key] = decision[key]

        if decision["keep"]:
            approved.append(result_item)
        else:
            rejected.append(result_item)

    return approved, rejected, audit

def categorise_recommendations(items):
    """Separate approved recommendations into the four categories."""

    return {
        "activities": [
            item for item in items if item["type"] == "activity"
        ],
        "food": [
            item for item in items if item["type"] == "food"
        ],
        "accommodation": [
            item for item in items
            if item["type"] == "accommodation"
        ],
        "shopping": [
            item
            for item in items
            if item["type"] == "shopping"
        ],
    }

def build_processed_result(
    destination,
    user_inputs,
    approved_items,
    rejected_items,
):
    """Build the final result used by the terminal and web front end."""

    categorised = categorise_recommendations(approved_items)

    return {
        "destination": destination,
        "requirements": user_inputs,
        "summary": {
            "approved_count": len(approved_items),
            "filtered_out_count": len(rejected_items),
        },
        "activities": categorised["activities"],
        "food": categorised["food"],
        "accommodation": categorised["accommodation"],
        "shopping": categorised["shopping"],
        "filtered_out": rejected_items,
    }
