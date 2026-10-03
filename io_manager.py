EXIT_COMMANDS = {"exit", "quit", "q"}

def display_welcome_banner():
    print("=" * 70)
    print("              TRAVEL RECOMMENDATION ASSISTANT")
    print("     AI discovers places; Python checks your requirements")
    print("=" * 70)
    print(
        "Press Enter when you want to use the default "
        "shown in [ ].\n"
    )
    print(
        "Type 'exit' at an input prompt to return to "
        "the main menu.\n"
    )

def display_menu():
    print("\nMAIN MENU")
    print("1. Generate Recommendations")
    print("2. View / Delete Saved Recommendation Sets")
    print("3. Exit")