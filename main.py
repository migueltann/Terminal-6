import ai_manager
import logic_manager
import data_manager
import io_manager

def run_application():
    """Run the terminal menu until the user exits."""

    # Show the welcome screen when the program starts
    io_manager.display_welcome_banner()
    while True:
        io_manager.display_menu()
        choice = io_manager.get_user_choice()

        if choice == "3":
            io_manager.display_message("Goodbye!")
            break

if __name__ == "__main__":
    run_application()
