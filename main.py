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

            # Python now compares the generic AI results with the user inputs
            approved, rejected, audit = (
                logic_manager.filter_recommendations(
                    valid_items,
                    user_inputs,
                )
            )

            # Show the KEEP / FILTER OUT checks
            io_manager.display_filter_audit(audit, user_inputs)

            # Organise the approved results into activities and food
            result = logic_manager.build_processed_result(
                destination,
                user_inputs,
                approved,
                rejected,
            )

            # Show the final approved recommendations
            io_manager.display_approved_recommendations(result)

            # Let the user save the processed result if they want to
            save_choice = io_manager.get_yes_no(
                "\nSave approved recommendations to JSON and CSV? (y/n): "
            )

            if save_choice:
                saved_paths = (
                    data_manager.save_processed_recommendations(result)
                )

                if saved_paths:
                    json_path, csv_path = saved_paths

                    io_manager.display_message(
                        f"Saved JSON: {json_path}"
                    )

                    io_manager.display_message(
                        f"Saved CSV:  {csv_path}"
                    )

                else:
                    io_manager.display_error(
                        "Could not save recommendation files."
                    )

        elif choice == "2":
            # Open the saved recommendations menu
            data_manager.manage_saved_recommendations()

        else:
            # End the program
            io_manager.display_message("Bon voyage! Thanks for planning your trip with us.")
            break


if __name__ == "__main__":
    run_application()