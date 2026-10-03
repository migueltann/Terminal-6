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