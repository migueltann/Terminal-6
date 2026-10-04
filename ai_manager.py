import json
import os
import time

import requests

from dotenv import load_dotenv
load_dotenv()

def generate_recommendations(destination):
    """Ask Gemini for a generic list of activities and food places."""

    # Read the Gemini API key from the .env file
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing.")
    
    prompt = build_ai_prompt(destination)

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


print(generate_recommendations("Singapore"))