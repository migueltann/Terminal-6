# Terminal-6 — AI-Powered Travel Recommendation Assistant

Terminal-6 is an object-oriented Python application that uses **Google Gemini** (with **Groq** as a backup) to discover destination-specific recommendations for activities, food, accommodation and shopping. Python rules then check every recommendation against the traveller's budget, environment, dietary, transport and avoid-list requirements and explain each PASS / FAIL.

The application has a **terminal interface** (`main.py`) and a **Flask web interface** (`web_app.py`). Both use the same classes.

## Features

- 60 AI recommendations per trip (15 per category), requested as four category prompts **in parallel threads** (advanced feature: threading)
- Automatic fallback across three Gemini models, then Groq
- Every AI reply is parsed and schema-checked before use (15 complete items per category, required fields, valid cost)
- Five filtering rules with PASS / FAIL explanations, plus a multi-condition **top pick** rule (matches a preference **and** costs at most half the budget)
- Save, view, search, rename and delete recommendation sets (JSON + CSV)
- **Itinerary Builder** (new feature, web): plan saved places day by day with automatic times, meal slots, best-time warnings, daily-budget checks and Google Maps links
- Automated tests (pytest) that run without a live API, GitHub Actions CI and Docker

## Project structure

| Folder | Contents |
| --- | --- |
| `main.py`, `travel_assistant.py` | Terminal entry point and the coordinator of the four managers |
| `user_io/` | **IO Manager** (`IOManager`), destination checking, progress spinner, web progress tracker |
| `ai/` | **AI Manager** (`AIManager`), `PromptBuilder`, `AIClient` interface, `GeminiClient`, `GroqClient`, `FallbackClient`, `AIResponseValidator` |
| `filtering/` | **Logic Manager** (`LogicManager`), `RecommendationFilter`, abstract `Rule` and its five subclasses, `TextMatcher` |
| `storage/` | **Data Manager** (`DataManager`), `ItineraryManager`, repository interfaces and their JSON/CSV implementations |
| `models/` | Data classes: `UserRequirements`, `Recommendation`, `RuleResult`, `RecommendationSet`, `Itinerary`, `ItineraryItem`, `DayPlanner`, `ScheduledStop` |
| `web/` | Helper classes for the Flask app: input validation, latest-result storage, error messages, itinerary page data |
| `tests/` | pytest test suite |

## Setup

**Requirements:** Python 3.12 (the version used by Docker and CI), internet access and a Gemini API key.

1. Clone the repository:

       git clone https://github.com/migueltann/Terminal-6.git
       cd Terminal-6

2. Install dependencies:

       python -m pip install -r requirements.txt

3. Copy `.env.example` to `.env` and add your key:

       GEMINI_API_KEY=your_actual_gemini_api_key

4. (Optional, recommended) Add a free Groq key as a backup. When every Gemini model fails, the app switches to Groq automatically:

       GROQ_API_KEY=your_actual_groq_api_key

   Groq retires models often; if the default models stop working, set your own list with `GROQ_MODELS=model-one,model-two`.

`.env` is listed in `.gitignore` and `.dockerignore`. Never commit or zip your real `.env`.

## Running in Docker

Build the image:

    docker build -t terminal-6 .

Terminal version (interactive). The key comes from your `.env`, and saved results are kept in the local `data` folder:

    docker run -it --rm --env-file .env -v "$(pwd)/data:/app/data" terminal-6

Web version, then open http://localhost:5000:

    docker run --rm -p 5000:5000 --env-file .env -v "$(pwd)/data:/app/data" terminal-6 python -m flask --app web_app:app run --host=0.0.0.0 --port=5000

Automated tests inside the container (no API key or internet needed):

    docker run --rm terminal-6 python -m pytest tests/ -v

On Windows PowerShell use `${PWD}` instead of `$(pwd)`.

## Running without Docker

    python main.py        # terminal version
    python web_app.py     # web version, then open http://127.0.0.1:5000

## Testing

    python -m pytest tests/ -v

The suite has 289 tests (288 run offline; 1 live-API test is skipped unless a key is set). Fakes, mocks and sample AI responses replace the real API. The tests cover the filtering rules and top picks, the Logic Manager, AI response validation, retries and provider fallback, parallel category generation, storage (including missing and corrupt files), input validation, the Itinerary Builder and the web routes.

## Continuous integration

`.github/workflows/python-ci.yml` runs on every push and pull request:

1. Install dependencies and compile every module (syntax check).
2. Run the pytest suite.
3. Build the Docker image and run the tests again inside the container.

## Data storage

| File | Format | Contents |
| --- | --- | --- |
| `data/recommendation_sets.json` | JSON list | Index of saved sets: destination, approved count, file paths, save time |
| `data/<destination>_<time>.json` | JSON object | One full `RecommendationSet` (requirements, approved items by category, filtered-out items with rule results) |
| `data/<destination>_<time>.csv` | CSV | Approved recommendations, one row each |
| `data/itineraries.json` | JSON list | Saved itineraries |
| `instance/latest_result_<key>.json` | JSON | The web user's latest unsaved result (the cookie only holds the key) |

## Limitations

AI-generated places, costs and best times may be inaccurate or out of date. Check them before making travel arrangements.