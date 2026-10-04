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

        if choice == "1":
            # Collect the user's requirements
            user_inputs = io_manager.collect_user_requirements()

            if user_inputs is None:
                continue

            destination = user_inputs["destination"]

            # Only the destination is sent to Gemini
            io_manager.display_message(
                "AI is generating generic destination recommendations..."
            )

            try:
                raw_items = ai_manager.generate_recommendations(destination)
            except Exception as err:
                io_manager.display_error(
                    f"AI generation failed: {err}"
                )
                continue

            # Make sure the AI returned data that the program can use
            valid_items = logic_manager.validate_ai_response(raw_items)

            if not valid_items:
                io_manager.display_error(
                    "AI returned no valid recommendations."
                )
                continue

        elif choice == "3":
            io_manager.display_message("Goodbye!")
            break

if __name__ == "__main__":
    run_application()
