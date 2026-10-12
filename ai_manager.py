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

def generate_recommendations(destination, user_inputs=None):
    """Ask Gemini for general and preference-related recommendations."""

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
        print(f"[INFO] Trying Gemini model: {model_name}")

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
                    timeout=45,
                )
            except requests.RequestException as err:
                last_error = err
                break

            # Return the recommendations when the API call works
            if response.status_code == 200:
                print(f"[INFO] Gemini succeeded using {model_name}.")
                return parse_gemini_response(response)

            # 429 and 5xx errors are usually temporary, so try again
            if response.status_code in {429, 500, 502, 503, 504}:
                last_error = RuntimeError(
                    f"HTTP {response.status_code}: {response.text[:300]}"
                )

                if attempt < 2:
                    wait_time = 2 ** (attempt + 1)
                    print(
                        f"[WARNING] {model_name} is busy. "
                        f"Retrying in {wait_time} seconds..."
                    )
                    time.sleep(wait_time)
                    continue

                print(f"[WARNING] {model_name} is still unavailable.")
                break

            # If a model is not available, move to the next one
            if response.status_code == 404:
                last_error = RuntimeError(
                    f"HTTP 404: {response.text[:300]}"
                )
                print(f"[WARNING] {model_name} is not available.")
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

    interests = active_preferences(
        user_inputs.get("interests", [])
    )

    preferred_activities = active_preferences(
        user_inputs.get("preferred_activities", [])
    )

    # Only interests and preferred activities are used for discovery.
    # All other user requirements remain with the Logic Manager.
    interest_count = 10 if interests else 0
    preferred_count = 10 if preferred_activities else 0

    general_activity_count = 30 - interest_count - preferred_count

    return f"""
You are a travel discovery engine.

Destination: {destination}

User interests: {json.dumps(interests)}
User preferred activities: {json.dumps(preferred_activities)}

Generate exactly 60 travel recommendation candidates.

Do not create an itinerary or schedule.

RECOMMENDATION BREAKDOWN:

ACTIVITIES: 30 total
- {general_activity_count} general activities covering popular and
  varied experiences in the destination.
- {interest_count} activities related to the user's interests.
- {preferred_count} activities related to the user's preferred activities.

FOOD: 20 general recommendations.
ACCOMMODATION: 20 general recommendations.
SHOPPING: 20 general recommendations.

The interest-related and preferred-activity-related groups should
be based on the actual user preferences provided above.

When there are multiple interests or preferred activities,
aim for variety across them.

Avoid duplicate recommendations across groups.

IMPORTANT:
- User interests and preferred activities influence activity discovery only.
- Do not personalise food, accommodation or shopping.
- Do not exclude general activities because they do not match preferences.
- Do not filter or rank recommendations based on user preferences.
- Do not assume any user budget, dietary restriction, avoid list,
  accommodation preference, shopping preference or transport preference.
- The Python Logic Manager handles filtering, scoring and ranking later.

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
2. Generate a varied selection of activities.
3. Generate general food, accommodation and shopping choices.
4. Include different accommodation categories where available.
5. Include different shopping categories where available.
6. Do not invent venues or claim uncertain facts as verified.
7. Do not include timing-related fields.
8. Do not include additional fields that replace the required fields.
9. Every recommendation must have all required fields.
10. Do not include explanations outside the JSON array.
""".strip()