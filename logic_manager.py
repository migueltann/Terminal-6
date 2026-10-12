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

def validate_ai_response(raw_items):
    """Keep only AI recommendations that have the fields needed downstream."""
    if not isinstance(raw_items, list):
        return []

    valid_items = []
    allowed_types = {"activity", "food", "accommodation", "shopping"}

    required = [
        "name", "type", "category", "estimated_cost_sgd", "location",
        "description", "tags", "transport_options", "dietary_tags",
    ]

    for item in raw_items:
        if not isinstance(item, dict) or not all(key in item for key in required):
            continue

        item_type = _normalise(item["type"])
        if item_type not in allowed_types:
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
    limit = float(user_inputs[key])

    return limit, label

def evaluate_recommendation(item, user_inputs):
    """Check one recommendation and record why it is kept or removed."""

    checks = []
    keep = True
    cost = item["estimated_cost_sgd"]

    limit, label = _budget_for_item(
        item,
        user_inputs,
    )   

    passed = cost <= limit

    checks.append(
        {
            "label": label,
            "passed": passed,
            "detail": (
                f"${cost:.2f} <= ${limit:.2f}"
                if passed
                else f"${cost:.2f} > ${limit:.2f}"
            ),
        }
    )

    keep = keep and passed

    avoided_terms = [
        term
        for term in user_inputs.get("avoid_list", [])
        if _normalise(term) not in {"", "any", "none"}
        and _contains_term(item, term)
    ]

    passed = not avoided_terms

    checks.append(
        {
            "label": "Avoid list",
            "passed": passed,
            "detail": (
                "No avoided match"
                if passed
                else "Matched: " + ", ".join(avoided_terms)
            ),
        }
    )

    keep = keep and passed
    
    # Check preferences based on the type of recommendation
    if item["type"] == "accommodation":
        preferences = user_inputs.get(
            "accommodation_preferences",
            [],
        )
        preference_label = "Accommodation preference"

    elif item["type"] == "shopping":
        preferences = user_inputs.get(
            "shopping_preferences",
            [],
        )
        preference_label = "Shopping preference"

    elif item["type"] == "activity":
        preferences = (
            user_inputs.get("interests", [])
            + user_inputs.get("preferred_activities", [])
        )
        preference_label = "Interests / preferred activities"

    else:
        # Food recommendations do not use activity preferences
        preferences = []
        preference_label = "Not applicable"

    # Ignore placeholder answers instead of treating them as keywords.
    preferences = [
        term
        for term in preferences
        if _normalise(term) not in {"", "any", "none"}
    ]

    if preferences:
        if item["type"] == "shopping":
            matched_preferences = [
                term
                for term in preferences
                if matches_shopping_preference(item, term)
            ]
        else:
            matched_preferences = [
                term
                for term in preferences
                if _contains_term(item, term)
            ]

        passed = bool(matched_preferences)

        if matched_preferences:
            detail = "Matched: " + ", ".join(matched_preferences)
        else:
            detail = "No preference match"

        checks.append(
            {
                "label": preference_label,
                "passed": passed,
                "detail": detail,
            }
        )

        keep = keep and passed
        
    # Dietary checks only make sense for food recommendations
    dietary = _normalise(
        user_inputs.get("dietary", "any")
    )

    if item["type"] == "food" and dietary not in {"", "none", "any"}:
        passed = dietary in item.get("dietary_tags", [])
        checks.append(
            {
                "label": "Dietary requirement",
                "passed": passed,
                "detail": (
                    f"{dietary} supported"
                    if passed
                    else f"{dietary} not listed"
                ),
            }
        )
        keep = keep and passed
        
     # Check whether the user's preferred transport is listed
    preferred_transport = _normalise(
        user_inputs.get("preferred_transport", "any")
    )

    if preferred_transport not in {"", "any"}:
        passed = preferred_transport in item.get("transport_options", [])
        checks.append(
            {
                "label": "Transport preference",
                "passed": passed,
                "detail": (
                    f"{preferred_transport} available"
                    if passed
                    else f"{preferred_transport} not listed"
                ),
            }
        )
        keep = keep and passed
        
    return {
        "item": item,
        "keep": keep,
        "checks": checks,
    }


def filter_recommendations(items, user_inputs):
    """Split the recommendations into approved and filtered-out lists."""

    approved = []
    rejected = []
    audit = []

    for item in items:
        decision = evaluate_recommendation(item, user_inputs)
        audit.append(decision)

        if decision["keep"]:
            approved.append(dict(item))
        else:
            rejected.append(item)

    return approved, rejected, audit

def rank_recommendations(items, user_inputs):
    """Put stronger matches near the top of the final result."""

    def score(item):
        points = 0

        # Accommodation has its own preferences
        if item["type"] == "accommodation":
            preferences = user_inputs.get(
                "accommodation_preferences", []
            )

            preferences = [
                term for term in preferences
                if _normalise(term) not in {"", "any", "none"}
            ]

            for term in preferences:
                if _contains_term(item, term):
                    points += 20

        elif item["type"] == "shopping":
            preferences = user_inputs.get(
                "shopping_preferences", []
            )

            preferences = [
                term for term in preferences
                if _normalise(term) not in {"", "any", "none"}
            ]

            for term in preferences:
                if matches_shopping_preference(item, term):
                    points += 20

        else:
            # Interests and preferred activities are for
            # activities and food
            interests = user_inputs.get("interests", [])
            interests = [
                term for term in interests
                if _normalise(term) not in {"", "any", "none"}
            ]

            preferred_activities = user_inputs.get(
                "preferred_activities", []
            )
            preferred_activities = [
                term for term in preferred_activities
                if _normalise(term) not in {"", "any", "none"}
            ]

            for term in interests:
                if _contains_term(item, term):
                    points += 10

            for term in preferred_activities:
                if _contains_term(item, term):
                    points += 15

        # Slightly prefer cheaper options when matches are similar
        points -= item["estimated_cost_sgd"] / 1000

        return points

    return sorted(items, key=score, reverse=True)

def categorise_recommendations(items):
    """Separate the approved results into activities and food."""

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

    ranked = rank_recommendations(approved_items, user_inputs)
    categorised = categorise_recommendations(ranked)

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
    }
