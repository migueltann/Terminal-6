# Terminal 6 web frontend

The Flask frontend calls the existing `ai_manager.py`, `logic_manager.py`, `io_manager.py`, and `data_manager.py`, so it uses the same AI generation and Python filtering rules as the terminal application.

## Setup (Windows PowerShell)

1. Open the `Terminal-6` folder in VS Code.
2. Create/activate your virtual environment if your project uses one.
3. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root (same folder as `web_app.py`) containing:

   ```text
   GEMINI_API_KEY=your_actual_gemini_api_key
   ```

   Never commit or push `.env` to GitHub.

5. Start the website:

   ```powershell
   python web_app.py
   ```

6. Open the local URL printed by Flask, normally `http://127.0.0.1:5000`.

## What it does

- Provides web inputs corresponding to the terminal's destination, activity, food, accommodation, shopping, budget, environment, dietary, transport and avoid-list requirements.
- Validates destination and positive budgets on the server, even if browser-side validation is bypassed.
- Hides the form and displays a loading screen while the AI request runs.
- Calls the existing Gemini generation, response validation, Python filtering and result-building functions.
- Displays approved results by category, plus filtered-out candidates and rule-check explanations.
- Saves the latest result using the existing JSON/CSV data manager.
- Shows actionable messages for common API key, quota, timeout, connection and service errors while retaining form values.

The first launch requires the dependencies in `requirements.txt`. The AI feature requires a valid Gemini API key and internet access.
