import json
import os
import time

import requests

def generate_recommendations(destination):
    """Ask Gemini for a generic list of activities and food places."""

    # Read the Gemini API key from the .env file
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing.")



def build_ai_prompt(destination):
    """Create the prompt. Only the destination is sent to Gemini."""

    return f"""
You are a travel discovery engine.

Destination: {destination}

Generate 24 to 30 GENERIC recommendations for this destination.
Do not create an itinerary or schedule.

Do not use user budgets, interests, preferred activities, dietary needs,
must-visits, avoid lists, transport preferences, travel dates, start times,
end times, duration, pace, or any other personal requirement.

The Python program will apply all user-specific rules later.

Return ONLY valid JSON as one array.
Every object must contain these fields:
- "name": string
- "type": either "activity" or "food"
- "category": short category such as Theme Park, Museum, Shopping, Nature,
  Observation Deck, Local Food, Cafe, Restaurant
- "estimated_cost_sgd": number for ONE person
- "location": string
- "description": one short generic description
- "tags": array of general keywords such as culture, shopping, nature,
  family, theme park, museum, views, adventure, food
- "transport_options": array using only walk, transit, taxi
- "dietary_tags": array of general labels such as halal, vegetarian, vegan,
  no-pork, or none

Rules:
1. Include a useful mix of activities and food.
2. Use realistic places in {destination}.
3. estimated_cost_sgd must be a non-negative number in SGD.
4. Do not decide whether a place suits this specific user.
5. Do not include timing-related fields.
6. Do not filter the recommendations.
""".strip()
