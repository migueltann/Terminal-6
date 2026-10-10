# Handles the terminal inputs and outputs shown to the user

import difflib
import re
import unicodedata

try:
    import geonamescache
except ImportError:  # keeps the program running if the library is missing
    geonamescache = None

EXIT_COMMANDS = {"exit", "e"}
BACK_COMMANDS = {"back", "b"}
LINE = "=" * 70
DIVIDER = "-" * 70

# Returned by the ask functions when the user wants the previous input.
# (Only returned when allow_back=True, so other files never see it.)
BACK = object()

# Destination validation (uses the geonamescache)

_GEO = {}

def _normalise(text):
    """Lowercase and remove accents and punctuation from names."""

    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        char for char in text
        if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _load_geo_data():
    """Build lookup tables from geonamescache (runs once)."""
    if _GEO or geonamescache is None:
        return

    gc = geonamescache.GeonamesCache()

    country_names = {}   # country code -> display name
    country_lookup = {}  # normalised name / ISO code -> country code
    for code, country in gc.get_countries().items():
        country_names[code] = country["name"]
        for key in (country["name"], country["iso"], country["iso3"]):
            country_lookup[_normalise(key)] = code

    city_lookup = {}  # normalised city -> {country code: (population, name)}
    for city in gc.get_cities().values():
        key = _normalise(city["name"])
        if not key:
            continue
        by_country = city_lookup.setdefault(key, {})
        code = city["countrycode"]
        if code not in by_country or city["population"] > by_country[code][0]:
            by_country[code] = (city["population"], city["name"])

    _GEO["country_names"] = country_names
    _GEO["country_lookup"] = country_lookup
    _GEO["city_lookup"] = city_lookup


def _suggest(key, pool):
    """Return the closest known name to a mistyped one, or None."""
    matches = difflib.get_close_matches(key, pool, n=1, cutoff=0.75)
    return matches[0] if matches else None


def validate_destination(text):
    """Check a destination. Returns (clean_destination, error_message).

    Accepted formats: "Japan", "SG", "Paris", or "City, Country".
    Exactly one of the two returned values is None.
    """
    parts = [part.strip() for part in text.split(",") if part.strip()]
    if not parts:
        return None, "Please enter a destination."

    _load_geo_data()
    if not _GEO:
        # Library not installed: accept the text rather than crash.
        return ", ".join(parts), None

    names = _GEO["country_names"]
    countries = _GEO["country_lookup"]
    cities = _GEO["city_lookup"]

    # Only one part: it must be a country (name or code) or a city.
    if len(parts) == 1:
        key = _normalise(parts[0])
        if key in countries:
            return names[countries[key]], None
        if key in cities:
            # If several countries have this city, use the most populous.
            code, (_, city) = max(
                cities[key].items(), key=lambda item: item[1][0]
            )
            if _normalise(city) == _normalise(names[code]):
                return city, None
            return f"{city}, {names[code]}", None

        message = (
            f"'{parts[0]}' is not a valid country or city. "
            "Please enter a valid country or city."
        )
        guess = _suggest(key, list(countries) + list(cities))
        if guess:
            name = (
                names[countries[guess]] if guess in countries
                else next(iter(cities[guess].values()))[1]
            )
            message += f" Did you mean {name}?"
        return None, message

    # City + country: the country (last part) and the city must both be real.
    country_text = parts[-1]
    city_text = ", ".join(parts[:-1])
    country_key = _normalise(country_text)

    if country_key not in countries:
        message = f"'{country_text}' is not a recognised country."
        guess = _suggest(country_key, list(countries))
        if guess:
            message += f" Did you mean {names[countries[guess]]}?"
        return None, message

    code = countries[country_key]
    country = names[code]
    city_key = _normalise(city_text)

    if city_key == _normalise(country):
        return country, None
    if city_key in cities and code in cities[city_key]:
        return f"{cities[city_key][code][1]}, {country}", None

    message = f"Could not find '{city_text}' in {country}."
    in_country = [k for k, v in cities.items() if code in v]
    guess = _suggest(city_key, in_country)
    if guess:
        message += f" Did you mean {cities[guess][code][1]}?"
    return None, message


# Banner and Menu

def display_welcome_banner():
    """Show the title when the program starts."""
    print(LINE)
    print("              TRAVEL RECOMMENDATION ASSISTANT")
    print("     AI discovers places; Python checks your requirements")
    print(LINE)
    print("Press Enter to use the default shown in [ ] at the end of a prompt.\n")
    print("Type 'back' or 'b' at an input prompt to return to the previous input.\n")
    print("Type 'exit' or 'e' at an input prompt to return to the main menu.\n")

def display_menu():
    print("\nMAIN MENU")
    print("1. Generate Recommendations")
    print("2. View / Delete Saved Recommendation Sets")
    print("3. Exit")

def get_user_choice():
    """Ask the user to choose an option from the main menu."""

    while True:
        choice = input("\nEnter choice (1-3): ").strip()

        if choice in {"1", "2", "3"}:
            return choice

        print("Invalid choice. Please enter 1, 2, or 3.")

def is_exit(value):
    """Check whether the user typed an exit command."""

    return value.strip().lower() in EXIT_COMMANDS

def get_required_text(prompt):
    """Ask for text that cannot be left blank."""

    while True:
        value = input(prompt).strip()

        if is_exit(value):
            return None

        if value:
            return value

        print("This field cannot be empty.")


def get_optional_text(prompt, default=""):
    """Ask for optional text and use a default if it is blank."""

    value = input(prompt).strip()

    if is_exit(value):
        return None

    return value if value else default

def get_positive_float(prompt, allow_zero=False):
    """Ask for a valid positive number."""

    while True:
        value = input(prompt).strip()

        if is_exit(value):
            return None

        try:
            number = float(value)
            if number > 0 or (allow_zero and number >= 0):
                return number
        except ValueError:
            pass

        print("Please enter a valid positive amount.")


def get_choice(prompt, choices, default):
    """Ask the user to choose from a fixed list of options."""

    choices_lower = [choice.lower() for choice in choices]

    while True:
        value = input(prompt).strip()

        if is_exit(value):
            return None

        if not value:
            return default

        if value.lower() in choices_lower:
            return choices[choices_lower.index(value.lower())]

        print("Invalid choice. Options: " + ", ".join(choices))


def _split_csv(value):
    """Turn comma-separated text into a clean Python list."""

    return [
        part.strip()
        for part in value.split(",")
        if part.strip()
    ]

def collect_user_requirements():
    """Collect the requirements that Python will use for filtering."""

    print("\n" + "=" * 70)
    print("USER INPUTS")
    print("=" * 70)

    destination = get_required_text("Destination: ")
    if destination is None:
        return None

    max_activity_spend = get_positive_float(
        "Max spend per activity (SGD): "
    )
    if max_activity_spend is None:
        return None

    max_meal_spend = get_positive_float(
        "Max spend per meal (SGD): "
    )
    if max_meal_spend is None:
        return None
    
    max_accommodation_spend = get_positive_float(
        "Max accommodation spend per night (SGD): "
        
    )

    if max_accommodation_spend is None:
        return None  

    max_shopping_spend = get_positive_float(
    "Max shopping spend (SGD): "
    )

    if max_shopping_spend is None:
        return None 

    interests_text = get_optional_text(
        "Interests (comma-separated) [Any]: ",
        "",
    )
    if interests_text is None:
        return None

    preferred_text = get_optional_text(
        "Preferred activities (comma-separated) [Any]: ",
        "",
    )
    if preferred_text is None:
        return None  
    
    accommodation_text = get_optional_text(
        "Accommodation preferences (comma-separated) [Any]: ",
        "",
    )
    if accommodation_text is None:
        return None

    shopping_text = get_optional_text(
    "Shopping preferences (comma-separated) [Any]: ",
    ""
    )
    if shopping_text is None:
        return None

    must_visit_text = get_optional_text(
        "Must-visits (comma-separated) [None]: ",
        "",
    )
    if must_visit_text is None:
        return None

    avoid_text = get_optional_text(
        "Avoid list (comma-separated) [None]: ",
        "",
    )
    if avoid_text is None:
        return None

    dietary = get_optional_text(
        "Dietary requirement [None]: ",
        "None",
    )
    if dietary is None:
        return None

    transport = get_choice(
        "Preferred transport [Any] (Walk/Transit/Taxi/Any): ",
        ["Walk", "Transit", "Taxi", "Any"],
        "Any",
    )
    if transport is None:
        return None

    # Keep all user inputs together so the logic manager can use them
    data = {
        "destination": destination,
        "max_activity_spend": max_activity_spend,
        "max_meal_spend": max_meal_spend,
        "max_accommodation_spend": max_accommodation_spend,
        "max_shopping_spend": max_shopping_spend,
        "interests": _split_csv(interests_text),
        "preferred_activities": _split_csv(preferred_text),
        "must_visit": _split_csv(must_visit_text),
        "avoid_list": _split_csv(avoid_text),
        "dietary": dietary,
        "preferred_transport": transport,
        "accommodation_preferences": _split_csv(accommodation_text),
        "shopping_preferences": _split_csv(shopping_text),
    }

    display_input_summary(data)
    return data

def display_input_summary(data):
    """Show the requirements back to the user before filtering."""

    print("\n" + "=" * 70)
    print("USER REQUIREMENTS")
    print("=" * 70)
    print(f"Destination:          {data['destination']}")
    print(f"Max per activity:     SGD ${data['max_activity_spend']:.2f}")
    print(f"Max per meal:         SGD ${data['max_meal_spend']:.2f}")
    print(
        f"Max accommodation:    SGD ${data['max_accommodation_spend']:.2f}"
    )
    print(
        f"Max shopping spend:   "
        f"SGD ${data['max_shopping_spend']:.2f}"
    )
    print(
        "Accommodation:        "
        f"{', '.join(data['accommodation_preferences']) or 'Any'}"
    )
    print(
        "Shopping:             "
        f"{', '.join(data['shopping_preferences']) or 'Any'}"
    )
    print(f"Interests:            {', '.join(data['interests']) or 'Any'}")
    print(
        "Preferred activities: "
        f"{', '.join(data['preferred_activities']) or 'Any'}"
    )
    print(f"Must-visits:          {', '.join(data['must_visit']) or 'None'}")
    print(f"Avoid:                {', '.join(data['avoid_list']) or 'None'}")
    print(f"Dietary:              {data['dietary']}")
    print(f"Transport:            {data['preferred_transport']}")
    print("=" * 70)

def display_filter_audit(audit, user_inputs): 
    """Show why each recommendation was kept or filtered out."""

    print("\n" + "=" * 70)
    print("AI RECOMMENDATIONS -> PYTHON LOGIC CHECK")
    print("=" * 70)
    print(f"Max per activity: SGD {user_inputs['max_activity_spend']:.2f}")
    print(f"Max per meal:     SGD {user_inputs['max_meal_spend']:.2f}")
    print(
        f"Max accommodation: SGD "
        f"{user_inputs['max_accommodation_spend']:.2f}"
    )

    for decision in audit:
        item = decision["item"]
        print("\n" + "-" * 70)
        print(item["name"])
        print(f"Type: {item['type']}")
        print(f"Category: {item['category']}")
        print(f"Cost: SGD ${item['estimated_cost_sgd']:.2f}")

        for check in decision["checks"]:
            status = "PASS" if check["passed"] else "FAIL"
            print(f"[{status}] {check['label']}: {check['detail']}")

        print("KEEP" if decision["keep"] else "FILTER OUT")

    print("=" * 70)

def display_approved_recommendations(result):
    """Show the final approved activities and food recommendations."""

    print("\n" + "=" * 70)
    print(f"APPROVED RECOMMENDATIONS: {result['destination'].upper()}")
    print("=" * 70)
   
    print(
        f"Approved: {result['summary']['approved_count']} | "
        f"Filtered out: {result['summary']['filtered_out_count']}"
    )

    must_visit = [
        item
        for item in result.get("activities", [])
        if item.get("category", "").strip().lower() == "must visit"
        or "must visit" in [
            str(tag).strip().lower()
            for tag in item.get("tags", [])
        ]
    ]

    other_activities = [
        item
        for item in result.get("activities", [])
        if item not in must_visit
    ]

    _display_section("MUST-VISIT PLACES", must_visit)
    _display_section("ACTIVITIES", other_activities)

    _display_section("FOOD", result.get("food", []))

    _display_section(
            "ACCOMMODATION",
            result.get("accommodation", []),
            cost_note="per night",
        )

    _display_section(
        "SHOPPING",
        result.get("shopping", []),
        cost_note="typical spend",
        )
    
def _display_section(title, items, cost_note="per person"):
    """Show one group of approved recommendations."""

    print("\n" + title)
    print("-" * 70)

    if not items:
        print("No approved recommendations in this category.")
        return

    for index, item in enumerate(items, start=1):
        print(f"\n{index}. {item['name']}")
        print(f"   {item['category']} · {item['location']}")

        print(
            f"   Estimated: SGD ${item['estimated_cost_sgd']:.2f} "
            f"{cost_note}"
        )

        print(f"   {item['description']}")

        if item.get("tags"):
            print("   Tags: " + ", ".join(item["tags"]))

        if item.get("transport_options"):
            print(
                "   Transport: " + ", ".join(item["transport_options"])
            )
            
def get_yes_no(prompt):
    """Ask a simple yes/no question."""

    while True:
        value = input(prompt).strip().lower()

        if is_exit(value):
            return None

        if value in {"y", "yes"}:
            return True

        if value in {"n", "no"}:
            return False

        print("Please enter y or n.")


def display_message(message):
    """Show a normal information message."""
    print(f"\n[INFO] {message}")


def display_error(error):
    """Show an error message."""
    print(f"\n[ERROR] {error}")
        