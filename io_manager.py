#I/O Manager - Handles the terminal inputs and outputs shown to the user

EXIT_COMMANDS = {"exit", "quit", "q"}

def display_welcome_banner():
    """Show the title when the program starts."""

    print("=" * 70)
    print("              TRAVEL RECOMMENDATION ASSISTANT")
    print("     AI discovers places; Python checks your requirements")
    print("=" * 70)
    print("Type 'exit' at an input prompt to return to the main menu.\n")

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
        "interests": _split_csv(interests_text),
        "preferred_activities": _split_csv(preferred_text),
        "must_visit": _split_csv(must_visit_text),
        "avoid_list": _split_csv(avoid_text),
        "dietary": dietary,
        "preferred_transport": transport,
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