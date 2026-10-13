import json
import os
import time

import requests

from dotenv import load_dotenv
load_dotenv()

def active_preferences(values):
    """Remove empty and placeholder preferences."""
    if not isinstance(values, list):
        return []

    return [
        str(value).strip()
        for value in values
        if str(value).strip().lower() not in {"", "any", "none"}
    ]

def _notify(notify, level, message):
    """Send a status message to the caller if a callback was given."""
    if notify is not None:
        notify(level, message)


def generate_recommendations(destination, user_inputs=None, notify=None):
    """Ask Gemini for general and preference-related recommendations.

    notify is an optional function(level, message). The caller decides how
    status messages are shown, so this module never prints anything.
    """

    # Read the Gemini API key from the .env file
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing.")
    
    prompt = build_ai_prompt(destination, user_inputs)

    # Try another model if the first model is busy or unavailable
    models_to_try = [
        "gemini-3.8-flash",
        "gemini-3.6-flash",
        "gemini-3.5-flash-lite",
    ]

    last_error = None

    for model_name in models_to_try:
        _notify(notify, "info", f"Trying Gemini model: {model_name}")

        # Retry temporary errors before moving to the next model
        for attempt in range(3):
            url = (
                "https://generativelanguage.googleapis.com/"
                f"v1beta/models/{model_name}:generateContent"
            )

            try:
                response = requests.post(
                    url,
                    headers={
                        "Content-Type": "application/json",
                        "x-goog-api-key": api_key,
                    },
                    json={
                        "contents": [{"parts": [{"text": prompt}]}],
                        "generationConfig": {
                            "response_mime_type": "application/json"
                        },
                    },
                    timeout=100,
                )
            except requests.RequestException as err:
                last_error = err
                break

            # Return the recommendations when the API call works
            if response.status_code == 200:
                try:
                    recommendations = parse_gemini_response(response)
                except RuntimeError as err:
                    # Malformed output: retry, then try the next model
                    last_error = err

                    if attempt < 2:
                        _notify(
                            notify,
                            "warning",
                            f"{model_name} returned malformed output. "
                            "Retrying...",
                        )
                        continue

                    _notify(
                        notify,
                        "warning",
                        f"{model_name} kept returning malformed output.",
                    )
                    break

                _notify(notify, "info", f"Gemini succeeded using {model_name}.")
                return recommendations

            # 429 and 5xx errors are usually temporary, so try again
            if response.status_code in {429, 500, 502, 503, 504}:
                last_error = RuntimeError(
                    f"HTTP {response.status_code}: {response.text[:300]}"
                )

                if attempt < 2:
                    wait_time = 2 ** (attempt + 1)
                    _notify(
                        notify,
                        "warning",
                        f"{model_name} is busy. "
                        f"Retrying in {wait_time} seconds...",
                    )
                    time.sleep(wait_time)
                    continue

                _notify(notify, "warning", f"{model_name} is still unavailable.")
                break

            # If a model is not available, move to the next one
            if response.status_code == 404:
                last_error = RuntimeError(
                    f"HTTP 404: {response.text[:300]}"
                )
                _notify(notify, "warning", f"{model_name} is not available.")
                break

            last_error = RuntimeError(
                f"Gemini API returned HTTP {response.status_code}: "
                f"{response.text[:300]}"
            )
            break

    raise RuntimeError(
        "All Gemini models failed. "
        f"Last error: {last_error}"
    )

def parse_gemini_response(response):
    """Turn Gemini's JSON response into a Python list."""

    response_data = response.json()
    candidates = response_data.get("candidates", [])

    if not candidates:
        raise RuntimeError("Gemini returned no candidates.")

    try:
        content = candidates[0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        raise RuntimeError("Gemini response format was unexpected.")

    try:
        parsed = json.loads(clean_json_response(content))
    except json.JSONDecodeError as err:
        raise RuntimeError(f"Gemini returned invalid JSON: {err}")

    # Gemini normally returns the list directly
    if isinstance(parsed, list):
        return parsed

    # Accept these wrapper names too in case Gemini adds one
    if isinstance(parsed, dict):
        for key in ("recommendations", "items"):
            if isinstance(parsed.get(key), list):
                return parsed[key]

    raise RuntimeError("Gemini returned an unexpected JSON structure.")


def clean_json_response(content):
    """Remove ```json fences if Gemini adds them around the JSON."""

    content = content.strip()

    if content.startswith("```"):
        lines = content.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        content = "\n".join(lines).strip()

    return content


def build_ai_prompt(destination, user_inputs=None):
    """Generate a mix of general and preference-related recommendations."""

    user_inputs = user_inputs or {}

    preferred_activities = active_preferences(
        user_inputs.get("preferred_activities", [])
    )

    food_preferences = active_preferences(
        user_inputs.get("food_preferences", [])
    )

    accommodation_preferences = active_preferences(
        user_inputs.get("accommodation_preferences", [])
    )

    shopping_preferences = active_preferences(
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

PREFERENCE GUIDELINES:

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

"tags": array of specific, descriptive lowercase keywords.
- Describe the actual place or experience.
- Include relevant activity themes such as culture, sports,
  museums, nature, history, adventure or entertainment.
- Use relevant keywords beyond these examples.
- Do not add tags simply to match the user's preferences.
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
9. Do not include timing-related fields.
10. Do not add preference scores, rankings or eligibility decisions.
11. Every recommendation must contain all required fields.
12. Do not include explanations outside the JSON array.
""".strip()