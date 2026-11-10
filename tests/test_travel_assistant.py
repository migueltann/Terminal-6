
import unittest
from unittest.mock import Mock

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



if __name__ == "__main__":
    unittest.main()
