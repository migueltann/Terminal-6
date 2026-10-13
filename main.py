import os
import ai_manager
import logic_manager
import data_manager
import io_manager

def manage_saved_recommendations():
    """Terminal menu for viewing, filtering or deleting saved results."""

    keyword = ""

    while True:
        saved = data_manager.find_saved_sets(keyword)

        if not saved:
            io_manager.display_message(
                "No saved recommendation sets found."
            )
            if not keyword:
                return
            keyword = ""
            continue

        io_manager.display_saved_sets(saved, keyword)
        choice = io_manager.ask_saved_set_action()

        if choice == "b":
            return

        if choice == "f":
            keyword = io_manager.ask_filter_keyword()
            continue

        if choice == "d":
            number = io_manager.ask_delete_number()

            if number.isdigit() and 1 <= int(number) <= len(saved):
                filename = os.path.basename(
                    saved[int(number) - 1]["json_path"]
                )
                if data_manager.delete_saved_recommendation(filename):
                    io_manager.display_message(
                        "Saved recommendation set deleted."
                    )
                    continue

            io_manager.display_error("Invalid selection.")
            continue

        if choice.isdigit() and 1 <= int(choice) <= len(saved):
            result = data_manager.load_result(
                saved[int(choice) - 1]["json_path"]
            )

            if result:
                io_manager.display_approved_recommendations(result)
            else:
                io_manager.display_error(
                    "Saved JSON file could not be read."
                )
        else:
            io_manager.display_error("Invalid choice.")

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
                "AI is generating general and interest-related recommendations..."
            )

            try:
                raw_items = ai_manager.generate_recommendations(
                    destination,
                    user_inputs,
                    notify=io_manager.display_status,
                )

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


            # Organise the approved results into activities and food
            result = logic_manager.build_processed_result(
                destination,
                user_inputs,
                approved,
                rejected,
            )

            # Show categorised recommendations with audit explanations
            io_manager.display_filtered_recommendations(result)

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
            manage_saved_recommendations()

        else:
            # End the program
            io_manager.display_message("Bon voyage! Thanks for planning your trip with us.")
            break


if __name__ == "__main__":
    run_application()