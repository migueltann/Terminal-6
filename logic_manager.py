"""Checks the AI recommendations against the user's requirements."""

def _normalise(value):
    """Make text easier to compare."""
    return str(value).strip().lower()


def _contains_term(item, term):
    """Check whether a user keyword appears in the recommendation."""

    term = _normalise(term)

    if not term:
        return False

    searchable = " ".join(
        [
            str(item.get("name", "")),
            str(item.get("category", "")),
            str(item.get("description", "")),
            str(item.get("location", "")),
            " ".join(str(tag) for tag in item.get("tags", [])),
        ]
    ).lower()

    return term in searchable

def validate_ai_response(raw_items):
    """Keep only AI recommendations that have the fields we need."""

    if not isinstance(raw_items, list):
        return []

    valid_items = []

    for item in raw_items:
        if not isinstance(item, dict):
            continue

        required = [
            "name",
            "type",
            "category",
            "estimated_cost_sgd",
            "location",
            "description",
            "tags",
            "transport_options",
            "dietary_tags",
        ]

        if not all(key in item for key in required):
            continue

        item_type = _normalise(item["type"])
        if item_type not in {"activity", "food"}:
            continue

        try:
            cost = float(item["estimated_cost_sgd"])
        except (TypeError, ValueError):
            continue

        if cost < 0:
            continue

        if not isinstance(item["tags"], list):
            continue
        if not isinstance(item["transport_options"], list):
            continue
        if not isinstance(item["dietary_tags"], list):
            continue

         # Clean the values before using them in the rest of the program
        cleaned = dict(item)
        cleaned["name"] = str(item["name"]).strip()
        cleaned["type"] = item_type
        cleaned["category"] = str(item["category"]).strip()
        cleaned["estimated_cost_sgd"] = cost
        cleaned["location"] = str(item["location"]).strip()
        cleaned["description"] = str(item["description"]).strip()

        cleaned["tags"] = [
            str(value).strip()
            for value in item["tags"]
            if str(value).strip()
        ]
        cleaned["transport_options"] = [
            _normalise(value)
            for value in item["transport_options"]
            if str(value).strip()
        ]
        cleaned["dietary_tags"] = [
            _normalise(value)
            for value in item["dietary_tags"]
            if str(value).strip()
        ]

        valid_items.append(cleaned)

    return valid_items

def evaluate_recommendation(item, user_inputs):
    """Check one recommendation and record why it is kept or removed."""

    checks = []
    keep = True
    cost = item["estimated_cost_sgd"]

    if item["type"] == "activity":
        limit = user_inputs["max_activity_spend"]
        passed = cost <= limit
        label = "Activity budget"
    else:
        limit = user_inputs["max_meal_spend"]
        passed = cost <= limit
        label = "Meal budget"

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

    return {
        "item": item,
        "keep": keep,
        "checks": checks,
    }