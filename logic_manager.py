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

    return valid_items