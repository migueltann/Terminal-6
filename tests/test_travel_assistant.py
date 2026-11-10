
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



if __name__ == "__main__":
    unittest.main()
