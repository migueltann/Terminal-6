# Terminal-6 — AI-Powered Travel Recommendation Assistant

Terminal-6 is a Python-based travel recommendation application that uses **Google Gemini AI** to generate destination-specific recommendations for activities, food, accommodation and shopping.

Users can enter their travel preferences and requirements. Gemini AI generates recommendations based on the four category-specific preferences, while Python validates and filters the results according to budget, environment, dietary, transportation and avoid-list restrictions.

The application supports both a **terminal interface** and a **Flask web interface**.

## Features

- AI-generated recommendations for activities, food, accommodation and shopping
- Customisable travel preferences and restrictions
- Python-based validation and filtering
- Approved and rejected recommendations with filtering explanations
- JSON saving and CSV exporting
- Automated testing using pytest (works without a live API connection)
- Continuous integration using GitHub Actions
- Docker support
- Transparent PASS/FAIL checks for every recommendation and a multi-condition "top pick" rule

## Setup

**Requirements:** Python 3.11, internet access and a valid Gemini API key.

1. Clone the repository:
      git clone https://github.com/migueltann/Terminal-6.git
      cd Terminal-6

2. Install dependencies:
      python -m pip install -r requirements.txt

3. Create a `.env` file in the main project folder:
      GEMINI_API_KEY=your_actual_gemini_api_key

   Replace the placeholder with your Gemini API key. Do not upload `.env` to GitHub.

## Running in Docker

Build the image once:

    docker build -t terminal-6 .

The API key is passed from your `.env` file and saved results are kept in the local `data` folder:

Run the **Terminal version:** application (interactive):

    docker run -it --rm --env-file .env -v "$(pwd)/data:/app/data" terminal-6

Run the **Flask web version:** application:

    docker run --rm -p 5000:5000 --env-file .env -v "$(pwd)/data:/app/data" terminal-6 python -m flask --app web_app:app run --host=0.0.0.0 --port=5000


On Windows PowerShell use `${PWD}` instead of `$(pwd)`.

Run the automated tests inside the container (no API key or internet needed):

    docker run --rm terminal-6 python -m pytest tests/ -v

A template for the key file is provided as `.env.example`. Never commit your real `.env`.

## Running the Application

**Terminal version:**

python3 main.py

**Flask web version:**

python web_app.py

Open the local URL displayed in the terminal, usually http://127.0.0.1:5000.

## Testing

Run the automated tests from the main project folder:

python -m pytest tests/ -v

Terminal-6 includes **24 automated tests** covering recommendation validation and filtering. GitHub Actions automatically runs syntax checks and tests when code is pushed or a pull request is opened.

## Data Storage

Terminal-6 uses **JSON** to save recommendation sets, including approved and rejected recommendations, and **CSV** to export approved recommendations.

Saved recommendation sets are indexed in `data/recommendation_sets.json`.

## Limitations

AI-generated recommendations, locations and estimated costs may be inaccurate or outdated. Users should verify the information before making travel arrangements.