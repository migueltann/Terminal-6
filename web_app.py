import io
import json
import math
import os
import traceback
import uuid

from flask import (
    Flask, 
    render_template,
    request,
    session,
    redirect,
    url_for,
    flash,
    jsonify,
    send_file,
)   

from dotenv import load_dotenv

import ai_manager
import data_manager
import io_manager
import logic_manager

load_dotenv()


app = Flask(__name__)

app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "terminal-6-local-development-key",
)

app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

#form field configuration
LIST_FIELDS = (
    "preferred_activities",
    "food_preferences",
    "accommodation_preferences",
    "shopping_preferences",
    "avoid_list",
)

BUDGET_FIELDS = (
    ("max_activity_spend", "Max spend per activity"),
    ("max_meal_spend", "Max spend per meal"),
    (
        "max_accommodation_spend",
        "Max spend per night for accommodation",
    ),
    ("max_shopping_spend", "Max shopping spend"),
)

ENVIRONMENTS = ("Indoor", "Outdoor", "Any")
TRANSPORTS = ("Walk", "Transit", "Taxi", "Any")

#server-side storage
#store generated results as files rather than large cookies.
def _result_file_path(result_key):
    if not isinstance(result_key, str):
        return None

    if not result_key or any(
        character not in "0123456789abcdef"
        for character in result_key.lower()
    ):
        return None

    return os.path.join(
        app.instance_path,
        f"latest_result_{result_key}.json",
    )


def _store_latest_result(result):
    """Save the latest generated result on the server."""
    os.makedirs(app.instance_path, exist_ok=True)

    result_key = session.get("latest_result_key")

    if not result_key or not _result_file_path(result_key):
        result_key = uuid.uuid4().hex
        session["latest_result_key"] = result_key

    path = _result_file_path(result_key)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            result,
            file,
            indent=4,
            ensure_ascii=False,
            allow_nan=False,
        )

def _get_latest_result():
    """Retrieve the latest generated result for the current session."""
    result_key = session.get("latest_result_key")
    path = _result_file_path(result_key)

    if not path or not os.path.isfile(path):
        return None

    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except (OSError, json.JSONDecodeError):
        app.logger.exception(
            "Could not read the latest generated recommendation result."
        )
        return None


def _clear_latest_result():
    result_key = session.pop("latest_result_key", None)
    path = _result_file_path(result_key)

    if not path:
        return

    try:
        if os.path.isfile(path):
            os.remove(path)
    except OSError:
        app.logger.exception("Could not remove temporary result.")

# input helpers
def _split_list(value):
    """Use the terminal's comma-separated list handling."""
    return io_manager.normalise_optional_list(value or "")


def _error_message(err):
    """Convert common AI/API errors into helpful messages."""
    raw = str(err or "Unknown error")
    low = raw.lower()

    if (
        "gemini_api_key" in low
        or (
            "api key" in low
            and ("missing" in low or "invalid" in low)
        )
    ):
        return (
            "Gemini API key is missing or invalid. "
            "Add GEMINI_API_KEY=your_key to the project .env file, "
            "then restart Flask."
        )

    if (
        "http 401" in low
        or "http 403" in low
        or "unauthorized" in low
        or "permission" in low
    ):
        return (
            "Gemini rejected the API key or its permissions. "
            "Check GEMINI_API_KEY and ensure the key can use the Gemini API."
        )

    if (
        "http 429" in low
        or "quota" in low
        or "resource_exhausted" in low
    ):
        return (
            "Gemini rate limit or quota reached. "
            "Wait and try again, or check your API quota."
        )

    if "timed out" in low or "timeout" in low:
        return "The AI request timed out. Please try again."

    if "connection" in low or "network" in low:
        return (
            "Could not connect to Gemini. "
            "Check your internet connection and try again."
        )

    if (
        "all gemini models failed" in low
        or any(
            code in low
            for code in (
                "http 500",
                "http 502",
                "http 503",
                "http 504",
            )
        )
    ):
        return (
            "Gemini is temporarily unavailable. "
            "Please try again in a little while."
        )

    return f"Recommendation generation failed: {raw}"


# validate and normalise form inputs
def _collect_inputs(form):
    """Validate and normalise the same requirements as the terminal."""

    destination_raw = (form.get("destination") or "").strip()

    destination, destination_error = (
        io_manager.validate_destination(destination_raw)
    )

    errors = []
    field_errors = {}

    if destination_error:
        errors.append(destination_error)
        field_errors["destination"] = destination_error

    data = {
        "destination": destination or destination_raw,
    }

    # Preferred activities, food, accommodation, shopping and exclusions.
    for key in LIST_FIELDS:
        data[key] = _split_list(form.get(key, ""))

    # Validate all budgets.
    for key, label in BUDGET_FIELDS:
        raw = (form.get(key) or "").strip()

        try:
            number = float(raw)

            if not math.isfinite(number) or number <= 0:
                raise ValueError

            data[key] = number

        except (ValueError, TypeError):
            message = "Please enter a valid positive amount."

            errors.append(f"{label}: {message}")
            field_errors[key] = message
            data[key] = None

    # Validate environment selections.
    environment_fields = (
        ("activity_environment", "Activity environment"),
        ("food_environment", "Food environment"),
        ("shopping_environment", "Shopping environment"),
    )

    for key, label in environment_fields:
        value = (form.get(key) or "Any").strip().title()

        if value not in ENVIRONMENTS:
            message = (
                f"{label} must be Indoor, Outdoor, or Any."
            )
            errors.append(message)
            field_errors[key] = message
            value = "Any"

        data[key] = value

    # Validate transport.
    transport = (
        form.get("preferred_transport") or "Any"
    ).strip().title()

    if transport not in TRANSPORTS:
        message = "Transport must be Walk, Transit, Taxi, or Any."
        errors.append(message)
        field_errors["preferred_transport"] = message
        transport = "Any"

    data["preferred_transport"] = transport

    # Normalise dietary preferences.
    dietary = (
        io_manager.normalise_optional_text(
            form.get("dietary")
        )
        or "None"
    )

    if dietary == "Other":
        dietary = (
            io_manager.normalise_optional_text(
                form.get("dietary_custom")
            )
            or "None"
        )

    data["dietary"] = dietary

    return data, errors, field_errors


@app.post("/validate-inputs")
def validate_inputs():
    """Validate the submitted form before starting AI generation."""
    _data, errors, field_errors = _collect_inputs(request.form)

    return jsonify({
        "valid": not errors,
        "errors": field_errors,
        "message": " ".join(errors),
    })

@app.get("/")
def index():
    return render_template(
        "index.html",
        form_data={},
        result=None,
        error=None,
        field_errors={},
        )

@app.post("/generate")
def generate():
    form_data = request.form.to_dict()

    user_inputs, errors, field_errors = _collect_inputs(
        request.form
    )

    # Do not call the AI if validation fails.
    if errors:
        return render_template(
            "index.html",
            form_data=form_data,
            result=None,
            error=(
                "Please correct the highlighted fields and try again."
            ),
            field_errors=field_errors,
        ), 400

    try:
        # Generate recommendations using the existing AI manager.
        raw_items = ai_manager.generate_recommendations(
            user_inputs["destination"],
            user_inputs,
        )

        # Validate the structure returned by the AI.
        valid_items = logic_manager.validate_ai_response(
            raw_items
        )

        if not valid_items:
            raise ValueError(
                "AI returned no valid recommendations. "
                "Please retry; if this repeats, check the AI prompt "
                "and response fields."
            )

        # Apply the existing recommendation filtering logic.
        approved, rejected, audit = (
            logic_manager.filter_recommendations(
                valid_items,
                user_inputs,
            )
        )

        # Build the final processed result.
        result = logic_manager.build_processed_result(
            user_inputs["destination"],
            user_inputs,
            approved,
            rejected,
        )

        # Store the full result on the server, not in the cookie.
        _store_latest_result(result)

        # The form data is small enough to retain in the session.
        session["latest_form"] = form_data

        return render_template(
            "index.html",
            form_data=form_data,
            result=result,
            error=None,
            field_errors={},
            audit=audit,
        )

    except Exception as exc:
        app.logger.exception(
            "Recommendation generation failed"
        )

        message = _error_message(exc)

        return render_template(
            "index.html",
            form_data=form_data,
            result=None,
            error=message,
            technical_error=str(exc),
            field_errors={},
        ), 502

@app.get("/saved")
def saved_sets():
    try:
        saved = data_manager.get_saved_recommendations()

    except Exception as exc:
        app.logger.exception(
            "Could not load saved recommendation sets"
        )

        saved = []
        flash(
            f"Could not load saved sets: {exc}",
            "error",
        )

    return render_template(
        "saved.html",
        saved=saved,
    )


@app.get("/saved/view/<path:filename>")
def view_saved(filename):
    """Display a saved recommendation set."""
    # Only open files registered by the data manager.
    entry = next(
        (
            item
            for item in data_manager.get_saved_recommendations()
            if os.path.basename(
                item.get("json_path", "")
            ) == filename
        ),
        None,
    )

    if not entry:
        flash(
            "That saved recommendation set was not found.",
            "error",
        )
        return redirect(url_for("saved_sets"))

    result = data_manager.load_result(
        entry["json_path"]
    )

    if not result:
        flash(
            "The saved JSON file could not be read.",
            "error",
        )
        return redirect(url_for("saved_sets"))

    # Make this result available to the Save and Download buttons.
    _store_latest_result(result)

    return render_template(
        "index.html",
        form_data={},
        result=result,
        error=None,
        field_errors={},
    )


if __name__ == "__main__":
        app.run(debug=True)