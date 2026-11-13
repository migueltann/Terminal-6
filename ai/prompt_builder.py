
import json
from typing import Any, Optional


# Field rules shared by the full prompt and the per-category prompts.
RECOMMENDATION_FIELDS = """
    Return ONLY valid JSON as one array containing recommendation objects.

    Every object must contain:

    "name": string

    "type": one of:
    "activity", "food", "accommodation", "shopping"

    "category": short descriptive category, such as Museum, Nature,
    Restaurant, Cafe, Hotel, Hostel, Serviced Apartment,
    Shopping Mall, Market or Shopping Street.

    "estimated_cost_sgd": non-negative number in SGD.
    - Activities and food: estimated cost per person.
    - Accommodation: estimated cost per room per night.
    - Shopping: reasonable typical spend per person.
    - Free activities may cost 0.
    - Shopping cost represents typical spending, not entry fees.

    "location": string

    "environment": one of "Indoor" or "Outdoor".
    - Describe the actual environment of the recommendation.
    - Indoor means the main experience takes place inside a building
      or other enclosed venue.
    - Outdoor means the main experience takes place outside.
    - For mixed venues, use the environment of the primary experience.
    - Do not choose an environment merely to match user preferences.

    "description": short, factual description of the recommendation.

    "best_time": one of "morning", "afternoon", "evening" or "any".
    - The time of day this place is best visited, based on its real
      opening hours and what the visit is like.
    - Use "evening" for places that only open, or are best, after dark,
      such as night safaris, night markets, light shows and bars.
    - Use "morning" or "afternoon" for places that close in the early
      evening or are best earlier in the day.
    - Use "any" when the time of day does not matter.
    - For food and accommodation, use "any" (meals are planned separately).

    "tags": array of accurate, descriptive lowercase keywords.
    - Apply these tagging rules to EVERY recommendation across
      activities, food, accommodation and shopping.
    - Include specific features, activities, experiences or products
      associated with the recommendation.
    - Include broader categories and related concepts that accurately
      describe the recommendation.
    - Include relevant characteristics that travellers might want
      to avoid, when supported by the recommendation's details.
    - Use commonly understood keywords at different levels of
      specificity, so both specific and general terms are represented.
    - For example, an activity may have both a specific activity tag
      and a broader category tag describing that activity.
    - Do not limit tags to the user's stated preferences.
    - Do not invent characteristics or include unrelated keywords.
    - Do not add tags merely to satisfy user restrictions.
    - Tags must accurately reflect the recommendation.


    "transport_options": array containing only:
    "walk", "transit", "taxi"
    Include only transport options reasonably available.

    "dietary_tags": array.
    - For food, use applicable labels such as halal, vegetarian,
      vegan, no-pork or none.
    - Do not label a place halal without reliable evidence.
    - If dietary suitability is uncertain, use ["none"].
    - For non-food recommendations, use ["none"].

    "shopping_types": array.
    - For shopping recommendations, describe the type of location,
      such as mall, street_market, shopping_street,
      department_store, specialty_store or outlet.
    - For non-shopping recommendations, use [].

    "shopping_interests": array.
    - For shopping recommendations, include accurate keywords
      describing what visitors can shop for.
    - Examples include fashion, sneakers, electronics, souvenirs,
      local crafts, watches, books, cosmetics and sports equipment.
    - Generate keywords based on the actual location.
    - For non-shopping recommendations, use [].
"""


# Recommendation type -> (plural wording, matching user_inputs key).
CATEGORY_DETAILS = {
    "activity": ("activities", "preferred_activities"),
    "food": ("food choices", "food_preferences"),
    "accommodation": ("accommodation choices", "accommodation_preferences"),
    "shopping": ("shopping choices", "shopping_preferences"),
}

CATEGORY_COUNT = 15


class PromptBuilder:
    """Build Gemini prompts from the traveller's preferences."""

    def _active_preferences(self, values: Any) -> list[str]:
        """Remove empty and placeholder preferences."""
        if not isinstance(values, list):
            return []

        return [
            str(value).strip()
            for value in values
            if str(value).strip().lower() not in {"", "any", "none"}
        ]

    def build(
        self,
        destination: str,
        user_inputs: Optional[dict] = None,
        category: Optional[str] = None,
    ) -> str:
        """Generate a mix of general and preference-related recommendations.

        With no category, the prompt asks for all 60 recommendations.
        With a category (e.g. "food"), it asks for only the 15 of that
        type, so the four categories can be requested in parallel.
        """

        user_inputs = user_inputs or {}

        if category is not None:
            return self._build_category(destination, user_inputs, category)

        preferred_activities = self._active_preferences(
            user_inputs.get("preferred_activities", [])
        )

        food_preferences = self._active_preferences(
            user_inputs.get("food_preferences", [])
        )

        accommodation_preferences = self._active_preferences(
            user_inputs.get("accommodation_preferences", [])
        )

        shopping_preferences = self._active_preferences(
            user_inputs.get("shopping_preferences", [])
        )

        return f"""

    You are a travel discovery engine.

    Destination: {destination}

    User activity preferences: {json.dumps(preferred_activities)}
    User food preferences: {json.dumps(food_preferences)}
    User accommodation preferences: {json.dumps(accommodation_preferences)}
    User shopping preferences: {json.dumps(shopping_preferences)}

    Generate exactly 60 travel recommendation candidates.

    Do not create an itinerary or schedule.

    RECOMMENDATION BREAKDOWN:

    ACTIVITIES: exactly 15 recommendations.
    - If activity preferences are provided, aim for 10 recommendations
      related to those preferences and 5 general activities.
    - Otherwise, generate 15 general activities.

    FOOD: exactly 15 recommendations.
    - If food preferences are provided, aim for 10 recommendations
      related to those preferences and 5 general food choices.
    - Otherwise, generate 15 general food choices.

    ACCOMMODATION: exactly 15 recommendations.
    - If accommodation preferences are provided, aim for 10 recommendations
      related to those preferences and 5 general accommodation choices.
    - Otherwise, generate 15 general accommodation choices.

    SHOPPING: exactly 15 recommendations.
    - If shopping preferences are provided, aim for 10 recommendations
      related to those preferences and 5 general shopping choices.
    - Otherwise, generate 15 general shopping choices.


    PREFERENCE INTERPRETATION AND VALIDATION:

    - Treat user preferences as free-text descriptions of their
      interests, not as guaranteed valid category labels.

    - For each of the four recommendation categories,
      independently assess whether its preferences express
      meaningful, interpretable travel interests.

    - Accept natural language, informal wording, common
      abbreviations, spelling mistakes, and niche interests
      when the intended meaning can reasonably be understood.

    - Do not reject a preference merely because it is unusual,
      uncommon, or unfamiliar.

    - If a preference is random characters, meaningless text,
      or cannot reasonably be interpreted, ignore that
      preference when generating recommendations.

    - If a category contains both meaningful and meaningless
      preferences, use only the meaningful preferences.

    - If a category has no meaningful preferences remaining,
      generate 15 varied general recommendations for that
      category.

    - If meaningful preferences remain, aim for 10 related
      recommendations and 5 varied general recommendations
      for that category.

    - Never invent a meaning for unintelligible input.

    - Apply these rules independently to activities, food,
      accommodation and shopping.

    - Do not include preference-validation decisions or
      explanations in the output JSON.


    - Use preferences to guide discovery, not to filter or rank results.
    - If multiple preferences are provided, aim for variety across them.
    - Include popular and varied general recommendations even when
      preferences are provided.
    - Do not invent places just to match a preference.
    - Avoid duplicate recommendations.
    - Keep recommendations specific to their assigned category.

    IMPORTANT:

    - Do not apply budget restrictions.
    - Do not apply indoor/outdoor restrictions.
    - Do not apply dietary restrictions.
    - Do not apply transport restrictions.
    - Do not apply an avoid list.
    - Do not calculate scores or rankings.
    - The Python Logic Manager handles hard restrictions separately.

{RECOMMENDATION_FIELDS}
    RULES:

    1. Use real places in {destination}.
    2. Return exactly 60 recommendations:
       15 activity, 15 food, 15 accommodation, 15 shopping.
    3. Personalise each category using its corresponding preferences.
    4. Include varied general choices in every category.
    5. Include different accommodation categories where available.
    6. Include different shopping categories where available.
    7. Every recommendation must include "environment".
    8. Do not invent venues or claim uncertain facts as verified.
    9. Do not include timing-related fields other than "best_time".
    10. Do not add preference scores, rankings or eligibility decisions.
    11. Every recommendation must contain all required fields.
    12. Do not include explanations outside the JSON array.
    """.strip()

    def _build_category(
        self,
        destination: str,
        user_inputs: dict,
        category: str,
    ) -> str:
        """Build a prompt for the 15 recommendations of one type."""

        if category not in CATEGORY_DETAILS:
            raise ValueError(
                f"Unknown recommendation category: {category}. "
                f"Expected one of: {', '.join(CATEGORY_DETAILS)}"
            )

        plural, input_key = CATEGORY_DETAILS[category]

        preferences = self._active_preferences(
            user_inputs.get(input_key, [])
        )

        return f"""

    You are a travel discovery engine.

    Destination: {destination}

    User {category} preferences: {json.dumps(preferences)}

    Generate exactly {CATEGORY_COUNT} {category} recommendation candidates.

    Do not create an itinerary or schedule.

    RECOMMENDATION BREAKDOWN:

    {category.upper()}: exactly {CATEGORY_COUNT} recommendations.
    - If {category} preferences are provided, aim for 10 recommendations
      related to those preferences and 5 general {plural}.
    - Otherwise, generate {CATEGORY_COUNT} general {plural}.


    PREFERENCE INTERPRETATION AND VALIDATION:

    - Treat user preferences as free-text descriptions of their
      interests, not as guaranteed valid category labels.

    - Assess whether the preferences express meaningful,
      interpretable travel interests.

    - Accept natural language, informal wording, common
      abbreviations, spelling mistakes, and niche interests
      when the intended meaning can reasonably be understood.

    - Do not reject a preference merely because it is unusual,
      uncommon, or unfamiliar.

    - If a preference is random characters, meaningless text,
      or cannot reasonably be interpreted, ignore that
      preference when generating recommendations.

    - If no meaningful preferences remain, generate
      {CATEGORY_COUNT} varied general {plural}.

    - Never invent a meaning for unintelligible input.

    - Do not include preference-validation decisions or
      explanations in the output JSON.


    - Use preferences to guide discovery, not to filter or rank results.
    - If multiple preferences are provided, aim for variety across them.
    - Include popular and varied general recommendations even when
      preferences are provided.
    - Do not invent places just to match a preference.
    - Avoid duplicate recommendations.

    IMPORTANT:

    - Do not apply budget restrictions.
    - Do not apply indoor/outdoor restrictions.
    - Do not apply dietary restrictions.
    - Do not apply transport restrictions.
    - Do not apply an avoid list.
    - Do not calculate scores or rankings.
    - The Python Logic Manager handles hard restrictions separately.

{RECOMMENDATION_FIELDS}
    RULES:

    1. Use real places in {destination}.
    2. Return exactly {CATEGORY_COUNT} recommendations, and every one
       must have "type": "{category}".
    3. Personalise the recommendations using the preferences above.
    4. Include varied general choices.
    5. Include different {category} categories where available.
    6. Every recommendation must include "environment".
    7. Do not invent venues or claim uncertain facts as verified.
    8. Do not include timing-related fields other than "best_time".
    9. Do not add preference scores, rankings or eligibility decisions.
    10. Every recommendation must contain all required fields.
    11. Do not include explanations outside the JSON array.
    """.strip()
