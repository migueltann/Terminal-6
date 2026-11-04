"""Filters generic AI recommendations using the user's requirements."""

import re
import math
from difflib import SequenceMatcher
from typing import Any, Optional

# number of cheapest options to recommend when no preferences are given
CHEAPEST_TOP_PICK_COUNT = 3

# convert text to lowercase 
def _normalise(value: Any) -> str:
    value = str(value or "").strip().lower() # convert value to string
    value = re.sub(r"[_\-]+", " ", value) # replace _ with -
    value = re.sub(r"[^\w\s]", " ", value) # remove special characters, replace with spaces
    return " ".join(value.split())

# remove empty ans or unnecessary placeholder values
def _active_preferences(values: Any) -> list[str]:
    if not isinstance(values, list): #check whether input is list
        return [] # if not list, return empty list
    return [
        str(value).strip() # convert value to string and remove space at end and beginning
        for value in values
        if _normalise(value) not in {"", "any", "none"} # remove empty ans,any or none frm the list
    ]

# take any type of value and return a list of strings
def _as_text_list(value: Any) -> list[str]:
    if not isinstance(value, list): # check if input is list
        return [] # else return empty list
    return [str(item).strip() for item in value if str(item).strip()] # convert items to string, remove extra spaces at beginning &end, skip if empty

# take in recommendation as dict and return as text
def _recommendation_text(item: dict) -> str:
    fields = [ # collect info abt recommendation
        item.get("name", ""),
        item.get("category", ""),
        item.get("description", ""),
        item.get("location", ""),
    ]
    for key in ( # go thru each fields to collect additional info
        "tags",
        "shopping_types",
        "shopping_interests",
        "interests",
        "activity_types",
        "themes",
        "keywords",
    ):
        fields.extend(_as_text_list(item.get(key, []))) # to clean values & add to fields list
    return _normalise(" ".join(str(field) for field in fields)) # combine all info into 1 txt & clean by removing extra spaces & convert to lowercase

# check whether user preference matches  recommendation text
def _preference_matches_text(preference: str, text: str) -> bool:

    pref = _normalise(preference)  # clean user preference
    searchable = _normalise(text)  # clean recommendation text

    # return False if either text is empty
    if not pref or not searchable:
        return False

    pref_words = pref.split()  # split preference into words
    text_words = searchable.split()  # split recommendation into words

    # check if exact preference appears in text
    if " " + pref + " " in " " + searchable + " ":
        return True

    # check if all preference words appear in recommendation
    if set(pref_words).issubset(text_words):
        return True

    # check for spelling differences if preference has at least 5 characters
    if len(pref) >= 5:
        size = len(pref_words)  # get num of words in preference

        # check each grp of words in recommendation
        for start in range(len(text_words) - size + 1):
            candidate = " ".join(text_words[start:start + size])  # Join selected words

            # returns True if both texts are at least 88% similar
            if SequenceMatcher(None, pref, candidate).ratio() >= 0.88:
                return True

    # False if no match found
    return False


def matches_shopping_preference(item: dict, preference: str) -> bool:
    """Match a shopping preference against generated shopping tags and text."""
    shopping_text = " ".join(
        _as_text_list(item.get("shopping_types", []))
        + _as_text_list(item.get("shopping_interests", []))
        + _as_text_list(item.get("tags", []))
        + [str(item.get("name", "")), str(item.get("category", "")),
           str(item.get("description", ""))]
    )
    return _preference_matches_text(preference, shopping_text)

# check whether search term matches any info in recommendation
def _contains_term(item: dict, term: str) -> bool:
    return _preference_matches_text(term, _recommendation_text(item))

# clean the list by removing empty values & duplicates
def _clean_list(values: list) -> list[str]:
    cleaned = [] # creaye empty list to store cleaned values
    for value in values: # go thru each list
        text = _normalise(value) # clean value and convert lowercase
        if text and text not in cleaned: # check value is not empty or repeated
            cleaned.append(text) # add cleaned value to list
    return cleaned # return cleaned list

# checks and cleans the ai recommendations
def validate_ai_response(raw_items: Any) -> list[dict]:
    """keeps only valid recommendations and removes duplicates"""

    # checks if the ai response is a list
    if not isinstance(raw_items, list):
        return []

    valid_items = []  # stores valid recommendations
    seen = []  # keeps track of recommendations already added
    allowed_types = {"activity", "food", "accommodation", "shopping"}  # lists the allowed types

    # lists the fields needed for each recommendation
    required = [
        "name", "type", "category", "estimated_cost_sgd", "location",
        "environment", "description", "tags",
        "transport_options", "dietary_tags",
    ]

    # checks each recommendation one by one
    for item in raw_items:

        # skips items that are missing required fields or are not dictionaries
        if not isinstance(item, dict) or not all(key in item for key in required):
            continue

        item_type = _normalise(item["type"])  # cleans the recommendation type

        # skips items with types that are not allowed
        if item_type not in allowed_types:
            continue

        environment = _normalise(item["environment"])  # cleans the environment value

        # only allows indoor or outdoor
        if environment not in {"indoor", "outdoor"}:
            continue

        # converts the estimated cost into a number
        try:
            cost = float(item["estimated_cost_sgd"])
        except (TypeError, ValueError):
            continue

        # skips invalid or negative costs
        if not math.isfinite(cost) or cost < 0:
            continue

        # checks if the required fields are lists
        if not all(isinstance(item[key], list) for key in (
            "tags", "transport_options", "dietary_tags"
        )):
            continue

        # checks extra fields for shopping recommendations
        if item_type == "shopping":

            # makes sure shopping types and interests are lists
            if not isinstance(item.get("shopping_types"), list):
                continue
            if not isinstance(item.get("shopping_interests"), list):
                continue

            # checks that all shopping values are text
            if not all(isinstance(value, str) for value in (
                item["shopping_types"] + item["shopping_interests"]
            )):
                continue

        # creates an identity to check for duplicates
        identity = (item_type, _normalise(item["name"]), _normalise(item["location"]))

        # skips the item if it has already been added
        if identity in seen:
            continue
        seen.append(identity)  # records the item to avoid duplicates

        cleaned = dict(item)  # makes a copy of the original item

        # cleans the main recommendation details
        cleaned["name"] = str(item["name"]).strip()
        cleaned["type"] = item_type
        cleaned["category"] = str(item["category"]).strip()
        cleaned["estimated_cost_sgd"] = cost
        cleaned["location"] = str(item["location"]).strip()
        cleaned["environment"] = environment.title()
        cleaned["description"] = str(item["description"]).strip()

        # cleans the list fields and removes empty or repeated values
        for key in ("tags", "transport_options", "dietary_tags",
                    "shopping_types", "shopping_interests",
                    "interests", "activity_types", "themes", "keywords"):

            # checks if the field contains a list
            if key in cleaned:
                if isinstance(cleaned[key], list):
                    cleaned[key] = _clean_list(cleaned[key])
                else:
                    cleaned[key] = []

        valid_items.append(cleaned)  # add cleaned item to the final list

    # returns all valid recommendations
    return valid_items


# gets the budget limit based on the recommendation type
def _budget_for_item(item: dict, user_inputs: dict) -> tuple[float, str]:

    # matches each recommendation type to its budget field
    mapping = {
        "activity": ("max_activity_spend", "Activity budget"),
        "food": ("max_meal_spend", "Meal budget"),
        "accommodation": ("max_accommodation_spend", "Accommodation budget"),
        "shopping": ("max_shopping_spend", "Shopping budget"),
    }

    # gets the correct budget field and label
    key, label = mapping[item["type"]]

    # tries to convert the user's budget into a number
    try:
        limit = float(user_inputs.get(key))
    except (TypeError, ValueError):
        limit = math.inf  # uses no budget limit if the value is invalid

    # uses no budget limit if the value is invalid or negative
    if math.isnan(limit) or limit < 0:
        limit = math.inf

    # returns the budget limit and its label
    return limit, label


# gets the user's preferences based on the recommendation type
def _preferences_for_item(item: dict, user_inputs: dict) -> list[str]:

    # matches each recommendation type to its preference field
    keys = {
        "activity": "preferred_activities",
        "food": "food_preferences",
        "accommodation": "accommodation_preferences",
        "shopping": "shopping_preferences",
    }

    # returns the user's preferences after removing empty answers
    return _active_preferences(user_inputs.get(keys[item["type"]], []))


# marks a recommendation as a top pick if it meets all the conditions
def is_top_pick(item: dict, user_inputs: dict, passed_all_checks: bool) -> bool:

    # skips the item if it did not pass all checks
    if not passed_all_checks:
        return False

    # gets the budget limit for the recommendation
    limit, _ = _budget_for_item(item, user_inputs)

    # checks if the cost is within half of the budget
    within_half_budget = item["estimated_cost_sgd"] <= 0.5 * limit

    # checks if the recommendation matches any user preference
    matches_preference = any(
        _contains_term(item, preference)
        for preference in _preferences_for_item(item, user_inputs)
    )

    # returns true only if both conditions are met
    return within_half_budget and matches_preference


# marks the cheapest options as top picks when no preferences are given
def mark_cheapest_top_picks(approved: list[dict], user_inputs: dict) -> None:

    # checks each recommendation category
    for item_type in ("activity", "food", "accommodation", "shopping"):

        # gets all approved recommendations in the current category
        in_category = [item for item in approved if item["type"] == item_type]

        # skips the category if there are no recommendations
        if not in_category:
            continue

        # skips categories that already have user preferences
        if _preferences_for_item(in_category[0], user_inputs):
            continue

        # gets the budget limit for the category
        limit, _ = _budget_for_item(in_category[0], user_inputs)

        # keeps only options that cost half or less of the budget
        affordable = [
            item for item in in_category
            if item["estimated_cost_sgd"] <= 0.5 * limit
        ]

        # sorts the options from cheapest to most expensive
        affordable.sort(key=lambda item: item["estimated_cost_sgd"])

        # selects the three cheapest options
        for item in affordable[:CHEAPEST_TOP_PICK_COUNT]:

            # marks the item as a top pick
            item["top_pick"] = True

            # explains why the item was selected
            item["top_pick_reason"] = (
                "one of the cheapest options and within half of your budget"
            )

def _add_check(checks: list, label: str, passed: bool, pass_text: str, fail_text: str) -> None:
    """Add one pass/fail result to the list of checks."""
    checks.append({
        "label": label,
        "passed": passed,
        "detail": pass_text if passed else fail_text,
    })


def evaluate_recommendation(item: dict, user_inputs: dict) -> dict:
    """Apply hard restrictions and record pass/fail explanations."""
    checks = []

    # 1. Category-specific budget restriction
    cost = item["estimated_cost_sgd"]
    limit, label = _budget_for_item(item, user_inputs)

    if math.isinf(limit):
        pass_text = "No budget limit set"
    else:
        pass_text = f"${cost:.2f} <= ${limit:.2f}"

    _add_check(checks, label, cost <= limit, pass_text, f"${cost:.2f} > ${limit:.2f}")

    # 2. Category-specific environment restriction
    environment_keys = {
        "activity": "activity_environment",
        "food": "food_environment",
        "shopping": "shopping_environment",
    }

    environment_key = environment_keys.get(item["type"])

    if environment_key:
        required_environment = _normalise(user_inputs.get(environment_key, "Any"))
    else:
        required_environment = "any"

    actual_environment = _normalise(item["environment"])

    if required_environment not in {"", "any", "none"}:
        _add_check(
            checks,
            "Environment",
            actual_environment == required_environment,
            f"{actual_environment.title()} matches {required_environment.title()}",
            f"{actual_environment.title()} does not match {required_environment.title()}",
        )

    # 3. Universal avoid-list restriction
    avoided_terms = []
    for term in _active_preferences(user_inputs.get("avoid_list", [])):
        if _contains_term(item, term):
            avoided_terms.append(term)

    _add_check(
        checks,
        "Avoid list",
        len(avoided_terms) == 0,
        "No avoided match",
        "Matched: " + ", ".join(avoided_terms),
    )

    # 4. Dietary restriction (food only)
    dietary = _normalise(user_inputs.get("dietary", "Any"))

    if item["type"] == "food" and dietary not in {"", "none", "any"}:
        _add_check(
            checks,
            "Dietary requirement",
            dietary in item.get("dietary_tags", []),
            f"{dietary} supported",
            f"{dietary} not listed",
        )

    # 5. Universal transport restriction
    preferred_transport = _normalise(user_inputs.get("preferred_transport", "Any"))

    if preferred_transport not in {"", "any", "none"}:
        _add_check(
            checks,
            "Transport preference",
            preferred_transport in item.get("transport_options", []),
            f"{preferred_transport} available",
            f"{preferred_transport} not listed",
        )

    # 6. The item is kept only if every check passed
    keep = all(check["passed"] for check in checks)

    return {
        "item": item,
        "keep": keep,
        "eligible": keep,
        "top_pick": is_top_pick(item, user_inputs, keep),
        "checks": checks,
        "passed_rules": [check["label"] for check in checks if check["passed"]],
        "failed_rules": [check["label"] for check in checks if not check["passed"]],
    }


def filter_recommendations(items: list[dict], user_inputs: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Split recommendations into eligible and rejected lists with audit details."""
    approved, rejected, audit = [], [], []
    pairs = []  # keeps each audit entry together with its result item

    for item in items:
        decision = evaluate_recommendation(item, user_inputs)
        audit.append(decision)
        result_item = dict(item)
        pairs.append((decision, result_item))

        for key in ("eligible", "top_pick", "checks", "passed_rules", "failed_rules"):
            result_item[key] = decision[key]

        if result_item["top_pick"]:
            result_item["top_pick_reason"] = (
                "matches your preferences and costs no more than "
                "half of your budget"
            )

        if decision["keep"]:
            approved.append(result_item)
        else:
            rejected.append(result_item)

    # Categories without preferences: the cheapest eligible items are picked
    mark_cheapest_top_picks(approved, user_inputs)

    # The line above only changes the result items, so update the audit too
    for decision, result_item in pairs:
        decision["top_pick"] = result_item["top_pick"]

    return approved, rejected, audit

# separates approved recommendations into four categories
def categorise_recommendations(items: list[dict]) -> dict[str, list[dict]]:

    # groups recommendations based on their type
    return {
        "activities": [item for item in items if item["type"] == "activity"],
        "food": [item for item in items if item["type"] == "food"],
        "accommodation": [item for item in items if item["type"] == "accommodation"],
        "shopping": [item for item in items if item["type"] == "shopping"],
    }


# prepares the final results for the terminal and web page
def build_processed_result(
    destination: str,
    user_inputs: dict,
    approved_items: list[dict],
    rejected_items: list[dict],
) -> dict:

    # separates the approved recommendations into categories
    categorised = categorise_recommendations(approved_items)

    # returns the final results with all recommendation details
    return {
        "destination": destination,
        "requirements": user_inputs,
        "summary": {
            "approved_count": len(approved_items),  # counts approved recommendations
            "filtered_out_count": len(rejected_items),  # counts rejected recommendations
        },
        "activities": categorised["activities"],
        "food": categorised["food"],
        "accommodation": categorised["accommodation"],
        "shopping": categorised["shopping"],
        "filtered_out": rejected_items,
    }