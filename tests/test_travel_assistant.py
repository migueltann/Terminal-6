
import unittest
from unittest.mock import Mock, call

from travel_assistant import TravelAssistant
from models import Recommendation, RecommendationSet, UserRequirements


class TestTravelAssistant(unittest.TestCase):

    def test_ai_to_filtering(self):
        """Check AI output is converted and passed to LogicManager."""

        mock_ai = Mock()
        mock_logic = Mock()

        # Simulated Gemini response
        raw_items = [
            {
                "name": "Tokyo Skytree",
                "type": "activity",
                "category": "attraction",
                "estimated_cost_sgd": 25,
                "location": "Tokyo, Japan",
                "environment": "Indoor",
                "description": "Observation tower",
                "tags": ["Sightseeing"],
                "transport_options": ["Train"],
                "dietary_tags": [],
                "shopping_types": [],
                "shopping_interests": [],
            }
        ]

        mock_ai.generate_recommendations.return_value = raw_items

        expected_result = Mock(spec=RecommendationSet)
        mock_logic.process.return_value = expected_result

        assistant = TravelAssistant(
            ai_manager=mock_ai,
            logic_manager=mock_logic,
        )

        requirements = UserRequirements.from_dict({
            "destination": "Japan",
            "preferred_activities": ["Sightseeing"],
        })

        result = assistant.generate_trip(requirements)

        # Check AI received the correct destination.
        mock_ai.generate_recommendations.assert_called_once_with(
            destination="Japan",
            user_inputs=requirements.to_dict(),
            notify=None,
        )

        # Check filtering received Recommendation objects.
        mock_logic.process.assert_called_once()

        passed_requirements, passed_items = (
            mock_logic.process.call_args.args
        )

        self.assertIs(passed_requirements, requirements)
        self.assertEqual(len(passed_items), 1)
        self.assertIsInstance(passed_items[0], Recommendation)
        self.assertEqual(passed_items[0].name, "Tokyo Skytree")

        # Check the final result is returned.
        self.assertIs(result, expected_result)

    
    def test_real_logic_manager_budget_filter(self):
        """Test AIManager integration with the actual filtering rules."""

        from filtering.logic_manager import LogicManager

        mock_ai = Mock()

        mock_ai.generate_recommendations.return_value = [
            {
                "name": "Tokyo Skytree",
                "type": "activity",
                "category": "attraction",
                "estimated_cost_sgd": 25,
                "location": "Tokyo, Japan",
                "environment": "Indoor",
                "description": "Observation tower",
                "tags": ["Sightseeing"],
                "transport_options": ["Train"],
                "dietary_tags": [],
                "shopping_types": [],
                "shopping_interests": [],
            },
            {
                "name": "Expensive Theme Park",
                "type": "activity",
                "category": "attraction",
                "estimated_cost_sgd": 150,
                "location": "Tokyo, Japan",
                "environment": "Outdoor",
                "description": "Theme park",
                "tags": ["Adventure"],
                "transport_options": ["Train"],
                "dietary_tags": [],
                "shopping_types": [],
                "shopping_interests": [],
            },
        ]

        requirements = UserRequirements.from_dict({
            "destination": "Japan",
            "max_activity_spend": 50,
        })

        assistant = TravelAssistant(
            ai_manager=mock_ai,
            logic_manager=LogicManager(),
        )

        result = assistant.generate_trip(requirements)

        self.assertIsInstance(result, RecommendationSet)

        self.assertEqual(len(result.approved()), 1)
        self.assertEqual(len(result.rejected_items()), 1)

        self.assertEqual(
            result.approved()[0].name,
            "Tokyo Skytree",
        )

        self.assertEqual(
            result.rejected_items()[0].name,
            "Expensive Theme Park",
        )

    def test_save_recommendations(self):
        """Check that TravelAssistant saves results when requested."""

        mock_ai = Mock()
        mock_logic = Mock()
        mock_data = Mock()

        mock_ai.generate_recommendations.return_value = [
            {
                "name": "Tokyo Skytree",
                "type": "activity",
                "category": "attraction",
                "estimated_cost_sgd": 25,
                "location": "Tokyo, Japan",
                "environment": "Indoor",
                "description": "Observation tower",
                "tags": ["Sightseeing"],
                "transport_options": ["Train"],
                "dietary_tags": [],
                "shopping_types": [],
                "shopping_interests": [],
            }
        ]

        expected_result = Mock(spec=RecommendationSet)
        mock_logic.process.return_value = expected_result

        assistant = TravelAssistant(
            ai_manager=mock_ai,
            logic_manager=mock_logic,
            data_manager=mock_data,
        )

        requirements = UserRequirements.from_dict({
            "destination": "Japan",
        })

        result = assistant.generate_trip(
            requirements,
            save=True,
        )

        mock_data.save.assert_called_once_with(expected_result)
        self.assertIs(result, expected_result)

    
    def test_real_data_manager_save_and_load(self):
        """Test saving and loading with Rachel's real repository."""

        import os
        import tempfile

        from data_manager import DataManager
        from storage.json_csv_repository import JsonCsvRepository
        from filtering.logic_manager import LogicManager

        mock_ai = Mock()

        mock_ai.generate_recommendations.return_value = [
            {
                "name": "Tokyo Skytree",
                "type": "activity",
                "category": "attraction",
                "estimated_cost_sgd": 25,
                "location": "Tokyo, Japan",
                "environment": "Indoor",
                "description": "Observation tower",
                "tags": ["Sightseeing"],
                "transport_options": ["Train"],
                "dietary_tags": [],
                "shopping_types": [],
                "shopping_interests": [],
            }
        ]

        requirements = UserRequirements.from_dict({
            "destination": "Japan",
        })

        with tempfile.TemporaryDirectory() as temp_dir:
            data_manager = DataManager(
                JsonCsvRepository(data_dir=temp_dir)
            )

            assistant = TravelAssistant(
                ai_manager=mock_ai,
                logic_manager=LogicManager(),
                data_manager=data_manager,
            )

            # Generate, filter and save.
            result = assistant.generate_trip(
                requirements,
                save=True,
            )

            # Find the saved file.
            saved_entries = data_manager.find("Japan")

            self.assertEqual(len(saved_entries), 1)

            filename = saved_entries[0]["filename"]

            # Load the saved recommendation set.
            loaded_result = data_manager.load(filename)

            self.assertIsNotNone(loaded_result)
            self.assertIsInstance(loaded_result, RecommendationSet)

            # Confirm the loaded data matches the original.
            self.assertEqual(
                loaded_result.to_dict(),
                result.to_dict(),
            )

            # Confirm both JSON and CSV were created.
            self.assertTrue(
                os.path.exists(saved_entries[0]["json_path"])
            )

            self.assertTrue(
                os.path.exists(saved_entries[0]["csv_path"])
            )


    def test_terminal_workflow(self):
        """Test terminal input, generation and display without Gemini."""

        mock_io = Mock()
        mock_ai = Mock()
        mock_logic = Mock()
        mock_data = Mock()

        mock_io.ask_yes_no.return_value = False

        requirements = UserRequirements.from_dict({
            "destination": "Japan",
        })

        expected_result = Mock(spec=RecommendationSet)

        # Simulate selecting Generate, then Exit.
        mock_io.show_menu.side_effect = ["1", "3"]

        # Simulate the user's completed inputs.
        mock_io.collect_requirements.return_value = requirements
        mock_io.confirm_or_edit.return_value = requirements

        # Avoid making a real Gemini API request.
        mock_ai.generate_recommendations.return_value = []
        mock_logic.process.return_value = expected_result

        assistant = TravelAssistant(
            ai_manager=mock_ai,
            logic_manager=mock_logic,
            data_manager=mock_data,
            io_manager=mock_io,
        )

        assistant.run()

        # Check that the terminal workflow was executed.
        mock_io.show_welcome.assert_called_once()
        mock_io.collect_requirements.assert_called_once()
        mock_io.confirm_or_edit.assert_called_once_with(
            requirements
        )

        # Check that AI and filtering were called.
        mock_ai.generate_recommendations.assert_called_once()
        mock_logic.process.assert_called_once()

        # Check that recommendations were displayed.
        mock_io.show_recommendations.assert_called_once_with(
            expected_result
        )

        # Check that the program exited normally.
        mock_io.show_message.assert_called_with("Goodbye!")



    def test_view_saved_recommendations(self):
        """Test viewing a saved recommendation set."""

        mock_io = Mock()
        mock_data = Mock()

        saved = [{
            "filename": "japan.json",
            "destination": "Japan",
        }]

        expected_result = Mock(spec=RecommendationSet)

        mock_data.find.return_value = saved
        mock_data.load.return_value = expected_result
        mock_io.ask_saved_action.side_effect = [
            ("view", "1"),
            ("back", ""),
        ]

        assistant = TravelAssistant(
            data_manager=mock_data,
            io_manager=mock_io,
        )

        assistant.show_saved_menu()

        mock_data.load.assert_called_once_with("japan.json")
        mock_io.show_recommendations.assert_called_once_with(
            expected_result
        )

    def test_filter_saved_recommendations(self):
        """Test searching saved trips by destination."""

        mock_io = Mock()
        mock_data = Mock()

        mock_data.find.side_effect = [
            [],
            [{
                "filename": "japan.json",
                "destination": "Japan",
            }],
        ]

        mock_io.ask_saved_action.side_effect = [
            ("filter", "Japan"),
            ("back", ""),
        ]

        assistant = TravelAssistant(
            data_manager=mock_data,
            io_manager=mock_io,
        )

        assistant.show_saved_menu()

        self.assertEqual(
            mock_data.find.call_args_list,
            [call(""), call("Japan")],
        )

    def test_delete_saved_recommendations(self):
        """Test deleting a saved trip after confirmation."""

        mock_io = Mock()
        mock_data = Mock()

        mock_data.find.return_value = [{
            "filename": "japan.json",
            "destination": "Japan",
        }]

        mock_io.ask_saved_action.side_effect = [
            ("delete", "1"),
            ("back", ""),
        ]

        mock_io.ask_yes_no.return_value = True
        mock_data.delete.return_value = True

        assistant = TravelAssistant(
            data_manager=mock_data,
            io_manager=mock_io,
        )

        assistant.show_saved_menu()

        mock_io.ask_yes_no.assert_called_once()
        mock_data.delete.assert_called_once_with("japan.json")
        mock_io.show_message.assert_any_call(
            "Recommendation set deleted."
        )

    
    def test_terminal_save_recommendations(self):
        """Test saving recommendations when the user chooses Yes."""

        mock_io = Mock()
        mock_ai = Mock()
        mock_logic = Mock()
        mock_data = Mock()

        requirements = UserRequirements.from_dict({
            "destination": "Japan",
        })

        expected_result = Mock(spec=RecommendationSet)

        # User generates recommendations, then exits.
        mock_io.show_menu.side_effect = ["1", "3"]
        mock_io.collect_requirements.return_value = requirements
        mock_io.confirm_or_edit.return_value = requirements

        # User chooses Yes to save.
        mock_io.ask_yes_no.return_value = True

        # Mock AI and filtering.
        mock_ai.generate_recommendations.return_value = []
        mock_logic.process.return_value = expected_result

        mock_data.save.return_value = "japan.json"

        assistant = TravelAssistant(
            ai_manager=mock_ai,
            logic_manager=mock_logic,
            data_manager=mock_data,
            io_manager=mock_io,
        )

        assistant.run()

        # Verify recommendations were saved.
        mock_data.save.assert_called_once_with(expected_result)

        # Verify the success message.
        mock_io.show_message.assert_any_call(
            "Recommendations saved successfully: japan.json"
        )

        # Verify Gemini was only called once.
        mock_ai.generate_recommendations.assert_called_once()




if __name__ == "__main__":
    unittest.main()
