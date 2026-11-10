
from typing import Optional

from user_io.io_manager import IOManager
from ai.ai_manager import AIManager
from filtering.logic_manager import LogicManager
from storage.data_manager import DataManager
from storage.json_csv_repository import JsonCsvRepository
from models import Recommendation, RecommendationSet, UserRequirements


class TravelAssistant:
    """Coordinate AI generation, filtering and storage."""

    def __init__(
        self,
        io_manager: Optional[IOManager] = None,
        ai_manager: Optional[AIManager] = None,
        logic_manager: Optional[LogicManager] = None,
        data_manager: Optional[DataManager] = None,
    ):
        
        self._io_manager = (
        io_manager if io_manager is not None else IOManager()
        )
            
        self._ai_manager = (
            ai_manager if ai_manager is not None else AIManager()
        )

        self._logic_manager = (
            logic_manager if logic_manager is not None else LogicManager()
        )

        self._data_manager = (
            data_manager if data_manager is not None
            else DataManager(JsonCsvRepository())
        )


    
    def run(self) -> None:
        """Run the terminal travel recommendation workflow."""

        self._io_manager.show_welcome()

        while True:
            choice = self._io_manager.show_menu()

            if choice == "3":
                self._io_manager.show_message("Goodbye!")
                return

            if choice == "2":
                self.show_saved_menu()
                continue

            requirements = self._io_manager.collect_requirements()

            if requirements is None:
                continue

            requirements = self._io_manager.confirm_or_edit(
                requirements
            )

            if requirements is None:
                continue

            try:
                result = self.generate_trip(
                    requirements,
                    notify=self._io_manager.show_status,
                )

                # Display the generated recommendations.
                self._io_manager.show_recommendations(result)

                # Ask whether the user wants to save the results.
                save_choice = self._io_manager.ask_yes_no(
                    "\nWould you like to save these recommendations? (y/n): "
                )

                if save_choice:
                    filename = self._data_manager.save(result)
                    self._io_manager.show_message(
                        f"Recommendations saved successfully: {filename}"
                    )


            except Exception as error:
                self._io_manager.show_error(str(error))


    def generate_trip(
        self,
        requirements: UserRequirements,
        notify=None,
        save: bool = False,
    ) -> RecommendationSet:
        """Generate, filter and optionally save recommendations."""

        if not isinstance(requirements, UserRequirements):
            raise TypeError(
                "requirements must be a UserRequirements object"
            )

        # Step 1: Generate recommendations.
        raw_items = self._ai_manager.generate_recommendations(
            destination=requirements.destination,
            user_inputs=requirements.to_dict(),
            notify=notify,
        )

        # Step 2: Convert dictionaries to objects.
        recommendations = [
            Recommendation.from_dict(item)
            for item in raw_items
        ]

        # Step 3: Filter recommendations.
        result = self._logic_manager.process(
            requirements,
            recommendations,
        )

        # Step 4: Save the result if requested.
        if save:
            self._data_manager.save(result)

        return result


    def show_saved_menu(self) -> None:
        """Allow users to view, search and delete saved trips."""

        keyword = ""

        while True:
            # Retrieve saved recommendation sets.
            saved = self._data_manager.find(keyword)

            if not saved:
                self._io_manager.show_message(
                    "No saved recommendations found."
                )
            else:
                self._io_manager.show_saved_sets(saved, keyword)

            action, value = self._io_manager.ask_saved_action()

            if action == "back":
                return

            if action == "filter":
                keyword = value
                continue

            if action not in {"view", "delete"}:
                self._io_manager.show_error("Invalid choice.")
                continue

            # Check whether the selected number is valid.
            if not value.isdigit():
                self._io_manager.show_error(
                    "Please enter a valid number."
                )
                continue

            index = int(value) - 1

            if index < 0 or index >= len(saved):
                self._io_manager.show_error(
                    "Selected recommendation set does not exist."
                )
                continue

            # Convert the selected number into a filename.
            filename = saved[index]["filename"]

            if action == "view":
                result = self._data_manager.load(filename)

                if result is None:
                    self._io_manager.show_error(
                        "Unable to load saved recommendations."
                    )
                else:
                    self._io_manager.show_recommendations(result)

            elif action == "delete":
                confirm = self._io_manager.ask_yes_no(
                    "Delete this recommendation set? (y/n): "
                )

                if confirm is None:
                    return

                if confirm:
                    if self._data_manager.delete(filename):
                        self._io_manager.show_message(
                            "Recommendation set deleted."
                        )
                    else:
                        self._io_manager.show_error(
                            "Unable to delete recommendation set."
                        )
