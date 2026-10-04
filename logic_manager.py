
def rank_recommendations(items, user_inputs):
    """Put stronger matches near the top of the final result."""

    def score(item):
        points = 0

        return points

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

    avoided_terms = [
        term
        for term in user_inputs["avoid_list"]
        if _contains_term(item, term)
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

    # A must-visit can count as a strong preference match
    must_visit_match = any(
        _contains_term(item, term)
        for term in user_inputs["must_visit"]
    )
    
    # Check whether the recommendation matches the user's interests
    preferences = (
        user_inputs["interests"]
        + user_inputs["preferred_activities"]
    )

    if preferences:
        matched_preferences = [
            term
            for term in preferences
            if _contains_term(item, term)
        ]

        passed = bool(matched_preferences) or must_visit_match

        if matched_preferences:
            detail = "Matched: " + ", ".join(matched_preferences)
        elif must_visit_match:
            detail = "Must-visit match"
        else:
            detail = "No preference match"

        checks.append(
            {
                "label": "Interests / preferred activities",
                "passed": passed,
                "detail": detail,
            }
        )
        keep = keep and passed
        
    # Dietary checks only make sense for food recommendations
    dietary = _normalise(user_inputs["dietary"])

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
        user_inputs["preferred_transport"]
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
        "must_visit_match": must_visit_match,
        "checks": checks,
    }

def rank_recommendations(items, user_inputs):
    """Put stronger matches near the top of the final result."""

    def score(item):
        points = 0
        
        # Must-visits get the biggest boost
        for term in user_inputs["must_visit"]:
            if _contains_term(item, term):
                points += 100
        
        # Interests and preferred activities also improve the score        
        for term in user_inputs["interests"]:
            if _contains_term(item, term):
                points += 10

        for term in user_inputs["preferred_activities"]:
            if _contains_term(item, term):
                points += 15
                
        # If two places are similar, the cheaper one comes slightly earlier
        points -= item["estimated_cost_sgd"] / 1000
        return points
                    
    return sorted(items, key=score, reverse=True) 

def build_processed_result(
    destination,
    user_inputs,
    approved_items,
    rejected_items,
):
    """Build the final result used by the terminal and web front end."""
        ranked = rank_recommendations(approved_items, user_inputs)
        categorised = categorise_recommendations(ranked)