import io
import json
import math
import os
import traceback
import uuid
from urllib.parse import quote_plus

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

from travel_assistant import TravelAssistant
from models import UserRequirements
from storage.data_manager import DataManager
from storage.json_csv_repository import JsonCsvRepository
from storage.itinerary_repository import JsonItineraryRepository
from storage.itinerary_manager import ItineraryManager
from models import Itinerary
from models import RecommendationSet
from user_io.destination_validator import DestinationValidator

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

# status messages from ai_manager go to the Flask log, not the terminal
def _log_ai_status(level, message):
    """Send AI status messages to the Flask log."""
    if level == "warning":
        app.logger.warning(message)
    else:
        app.logger.info(message)

def _normalise_optional_text(value):
    """Clean optional text input."""
    text = str(value or "").strip()
    return None if text.lower() in {"", "any", "none"} else text

# input helpers
def _split_list(value):
    """Convert comma-separated form input into a clean list."""
    values = [
        part.strip()
        for part in (value or "").split(",")
        if part.strip()
    ]

    if any(part.lower() in {"any", "none"} for part in values):
        return []

    return values


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
        "no usable recommendations" in low
        or "malformed" in low
        or "invalid json" in low
    ):
        return (
            "Gemini returned an answer the app could not use. "
            "Please try again."
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
        DestinationValidator().validate(destination_raw)
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
        _normalise_optional_text(
            form.get("dietary")
        )
        or "None"
    )

    if dietary == "Other":
        dietary = (
            _normalise_optional_text(
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
        # Convert Flask form data into an OOP requirements object.
        requirements = UserRequirements.from_dict(user_inputs)

        # Generate and filter recommendations through the OOP application.
        assistant = TravelAssistant()

        recommendation_set = assistant.generate_trip(
            requirements,
            notify=_log_ai_status,
        )

        # Convert the OOP result into the dictionary expected by Flask.
        result = recommendation_set.to_dict()

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
    """Display saved recommendation sets using OOP."""
    keyword = request.args.get("destination", "").strip().lower()

    try:
        manager = DataManager(JsonCsvRepository())
        saved = manager.find(keyword)

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
        keyword=keyword,
    )


@app.get("/saved/view/<path:filename>")
def view_saved(filename):
    """Display a saved recommendation set using OOP."""
    manager = DataManager(JsonCsvRepository())

    recommendation_set = manager.load(
        os.path.basename(filename)
    )

    if recommendation_set is None:
        flash(
            "That saved recommendation set could not be found or read.",
            "error",
        )
        return redirect(url_for("saved_sets"))

    result = recommendation_set.to_dict()

    _store_latest_result(result)

    return render_template(
        "index.html",
        form_data={},
        result=result,
        error=None,
        field_errors={},
    )

@app.post("/saved/delete/<path:filename>")
def delete_saved(filename):
    """Delete a saved recommendation set using OOP."""
    manager = DataManager(JsonCsvRepository())

    if manager.delete(os.path.basename(filename)):
        flash(
            "Saved recommendation set deleted.",
            "success",
        )
    else:
        flash(
            "Could not delete that saved recommendation set.",
            "error",
        )

    return redirect(url_for("saved_sets"))


@app.post("/saved/rename/<path:filename>")
def rename_saved(filename):
    """Rename a saved recommendation set."""
    new_name = request.form.get("new_name", "").strip()

    if not new_name:
        flash("Please enter a new name.", "error")
        return redirect(url_for("saved_sets"))

    if len(new_name) > 100:
        flash("The new name must be 100 characters or fewer.", "error")
        return redirect(url_for("saved_sets"))

    manager = DataManager(JsonCsvRepository())

    if manager.rename(os.path.basename(filename), new_name):
        flash(f"Saved set renamed to '{new_name}'.", "success")
    else:
        flash("Could not rename that saved recommendation set.", "error")

    return redirect(url_for("saved_sets"))


# ========================================
# ITINERARY BUILDER
# ========================================

DEFAULT_DAYS = 3
DEFAULT_DAILY_BUDGET = 200


def _data_manager():
    return DataManager(JsonCsvRepository())


def _itinerary_manager():
    return ItineraryManager(JsonItineraryRepository())


def _catalog(recommendation_set):
    """The approved recommendations the builder can place on days."""
    return [
        {
            "index": index,
            "name": item.name,
            "type": item.item_type,
            "cost": item.cost_sgd,
            "location": item.location,
        }
        for index, item in enumerate(recommendation_set.approved())
    ]


def _render_builder(set_id, recommendation_set,
                    itinerary=None, itinerary_id=""):
    """Show the builder for a new itinerary, or reopen a saved one."""
    catalog = _catalog(recommendation_set)

    if itinerary is None:
        days = [[] for _ in range(DEFAULT_DAYS)]
    else:
        # Map saved items back onto the catalog so they can still be edited.
        # Each placed item is its own copy, so its meal choice stays with that day.
        days = [
            [dict(catalog[entry["index"]], meal=entry["meal"], time=entry["time"],
                  duration=entry["duration"])
             for entry in day]
            for day in itinerary.selection_for(recommendation_set)
        ]

    return render_template(
        "itinerary.html",
        catalog=catalog,
        days=days,
        set_id=set_id,
        itinerary_id=itinerary_id,
        title=itinerary.title if itinerary else recommendation_set.destination,
        destination=recommendation_set.destination,
        daily_budget=(
            itinerary.daily_budget if itinerary else DEFAULT_DAILY_BUDGET
        ),
        start_date=itinerary.start_date if itinerary else "",
        max_days=Itinerary.MAX_DAYS,
        max_items=Itinerary.MAX_ITEMS_PER_DAY,
    )


TYPE_LABELS = {
    "activity": "Activity",
    "food": "Food",
    "shopping": "Shopping",
    "accommodation": "Stay",
}


def _maps_link(item, destination):
    """A Google Maps search link for a stop (name + address + city)."""
    query = ", ".join(
        part for part in (item.name, item.location, destination) if part
    )
    return "https://www.google.com/maps/search/?api=1&query=" + quote_plus(query)


def _itinerary_view_days(itinerary):
    """Everything the itinerary page needs for each day."""
    view_days = []

    for index in range(len(itinerary.days)):
        day_date = itinerary.date_for(index)
        stops = [
            {
                "time": stop.time,
                "end": stop.end,
                "period": stop.period,
                "label": stop.label,
                "type": stop.item.item_type,
                "type_label": TYPE_LABELS.get(stop.item.item_type, "Stop"),
                "name": stop.item.name,
                "category": stop.item.category,
                "location": stop.item.location,
                "description": stop.item.description,
                "cost": stop.item.cost_sgd,
                "top_pick": stop.item.top_pick,
                "maps": _maps_link(stop.item, itinerary.destination),
            }
            for stop in itinerary.schedule(index)
        ]

        view_days.append({
            "number": index + 1,
            "date": day_date.strftime("%A, %d %B %Y") if day_date else "",
            "stops": stops,
            "visits": [stop for stop in stops if stop["period"] != "Overnight"],
            "stays": [stop for stop in stops if stop["period"] == "Overnight"],
            "total": itinerary.day_total(index),
            "over": itinerary.is_over_budget(index),
        })

    return view_days


@app.get("/itineraries")
def itineraries():
    """List saved itineraries."""
    keyword = request.args.get("q", "").strip()

    try:
        saved = _itinerary_manager().find(keyword)
    except Exception as exc:
        app.logger.exception("Could not load itineraries")
        saved = []
        flash(f"Could not load itineraries: {exc}", "error")

    return render_template(
        "itineraries.html",
        itineraries=saved,
        keyword=keyword,
    )


@app.get("/itineraries/new/<path:set_id>")
def new_itinerary(set_id):
    """Open the builder for a saved recommendation set."""
    set_id = os.path.basename(set_id)
    recommendation_set = _data_manager().load(set_id)

    if recommendation_set is None:
        flash("That saved recommendation set could not be found.", "error")
        return redirect(url_for("saved_sets"))

    if not recommendation_set.approved():
        flash("That saved set has no approved recommendations to plan with.", "error")
        return redirect(url_for("saved_sets"))

    return _render_builder(set_id, recommendation_set)


@app.get("/itineraries/<itinerary_id>")
def edit_itinerary(itinerary_id):
    """Reopen a saved itinerary in the builder."""
    itinerary = _itinerary_manager().load(itinerary_id)

    if itinerary is None:
        flash("That itinerary could not be found.", "error")
        return redirect(url_for("itineraries"))

    recommendation_set = _data_manager().load(itinerary.source_id)

    if recommendation_set is None:
        flash(
            "The saved recommendation set this itinerary was built from "
            "has been deleted, so it can no longer be edited.",
            "error",
        )
        return redirect(url_for("view_itinerary", itinerary_id=itinerary_id))

    return _render_builder(
        itinerary.source_id, recommendation_set, itinerary, itinerary_id
    )


@app.get("/itineraries/<itinerary_id>/view")
def view_itinerary(itinerary_id):
    """Show a saved itinerary as a day-by-day plan that can be followed or printed."""
    itinerary = _itinerary_manager().load(itinerary_id)

    if itinerary is None:
        flash("That itinerary could not be found.", "error")
        return redirect(url_for("itineraries"))

    first_date = itinerary.date_for(0)
    last_date = itinerary.date_for(len(itinerary.days) - 1)

    return render_template(
        "itinerary_view.html",
        itinerary=itinerary,
        itinerary_id=itinerary_id,
        days=_itinerary_view_days(itinerary),
        date_range=(
            f"{first_date:%d %b} – {last_date:%d %b %Y}" if first_date else ""
        ),
        can_edit=_data_manager().load(itinerary.source_id) is not None,
    )


@app.post("/itineraries/save")
def save_itinerary():
    """Create a new itinerary or update an existing one."""
    set_id = os.path.basename(request.form.get("set_id", ""))
    itinerary_id = request.form.get("itinerary_id", "").strip()

    back = (
        url_for("edit_itinerary", itinerary_id=itinerary_id)
        if itinerary_id
        else url_for("new_itinerary", set_id=set_id or "missing")
    )

    try:
        selection = json.loads(request.form.get("plan", ""))
        daily_budget = float(request.form.get("daily_budget", ""))
    except (TypeError, ValueError):
        flash("The itinerary could not be read. Please try again.", "error")
        return redirect(back)

    recommendation_set = _data_manager().load(set_id)

    if recommendation_set is None:
        flash("The saved recommendation set could not be found.", "error")
        return redirect(url_for("itineraries"))

    manager = _itinerary_manager()

    try:
        itinerary = manager.build(
            recommendation_set,
            set_id,
            daily_budget,
            selection,
            request.form.get("title", ""),
            request.form.get("start_date", ""),
        )
    except (TypeError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(back)

    try:
        if itinerary_id:
            if not manager.update(itinerary_id, itinerary):
                flash("Could not update that itinerary.", "error")
                return redirect(url_for("itineraries"))
            message = "Itinerary updated."
        else:
            itinerary_id = manager.save(itinerary)
            message = "Itinerary saved."
    except Exception as exc:
        app.logger.exception("Saving itinerary failed")
        flash(f"Could not save the itinerary: {exc}", "error")
        return redirect(back)

    flash(message, "success")

    over = itinerary.over_budget_days()
    if over:
        flash(
            "Over the daily budget on day "
            + ", ".join(str(day) for day in over)
            + ".",
            "error",
        )

    # Show the finished itinerary straight after saving.
    return redirect(url_for("view_itinerary", itinerary_id=itinerary_id))


@app.post("/itineraries/<itinerary_id>/delete")
def delete_itinerary(itinerary_id):
    """Delete a saved itinerary."""
    if _itinerary_manager().delete(itinerary_id):
        flash("Itinerary deleted.", "success")
    else:
        flash("Could not delete that itinerary.", "error")

    return redirect(url_for("itineraries"))


@app.post("/itineraries/plan-latest")
def plan_latest():
    """Save the results just generated, then open the builder for them."""
    result = _get_latest_result()

    if not result:
        flash("Generate recommendations first.", "error")
        return redirect(url_for("index"))

    try:
        set_id = _data_manager().save(RecommendationSet.from_dict(result))
    except Exception as exc:
        app.logger.exception("Saving before planning failed")
        flash(f"Could not save the recommendations: {exc}", "error")
        return redirect(url_for("index"))

    flash("Recommendations saved. Now plan your days.", "success")
    return redirect(url_for("new_itinerary", set_id=set_id))


@app.post("/download/json")
def download_json():
    """Send the current recommendation result to the browser."""
    result = _get_latest_result()

    if not result:
        flash(
            "There are no recommendations to download. "
            "Please generate recommendations first.",
            "error",
        )
        return redirect(url_for("index"))

    try:
        destination = str(
            result.get(
                "destination",
                "travel_recommendations",
            )
        )

        # Create a safe filename.
        safe_name = "".join(
            character.lower()
            if character.isalnum()
            else "_"
            for character in destination
        ).strip("_")

        if not safe_name:
            safe_name = "travel_recommendations"

        filename = (
            f"{safe_name}_recommendations.json"
        )

        # Serialise the result as readable JSON.
        json_content = json.dumps(
            result,
            indent=4,
            ensure_ascii=False,
            allow_nan=False,
        )

        # Create an in-memory file for the download response.
        json_file = io.BytesIO(
            json_content.encode("utf-8")
        )
        json_file.seek(0)

        return send_file(
            json_file,
            mimetype="application/json",
            as_attachment=True,
            download_name=filename,
        )

    except Exception as exc:
        app.logger.exception(
            "JSON download failed"
        )

        flash(
            f"Could not download JSON: {exc}",
            "error",
        )

        return redirect(url_for("index"))


@app.post("/save")
def save():
    """Save the current recommendation result using the OOP DataManager."""
    result = _get_latest_result()

    if not result:
        flash(
            "There is no generated recommendation set to save. "
            "Generate recommendations first.",
            "error",
        )
        return redirect(url_for("index"))

    try:
        # Convert the Flask dictionary back into an OOP object.
        recommendation_set = RecommendationSet.from_dict(result)

        # Save through the OOP DataManager.
        manager = DataManager(JsonCsvRepository())
        filename = manager.save(recommendation_set)

        flash(
            f"Recommendations saved successfully: {filename}",
            "success",
        )

    except Exception as exc:
        app.logger.exception("Saving recommendations failed")

        flash(
            f"Could not save recommendations: {exc}",
            "error",
        )

    return redirect(url_for("index"))



@app.get("/reset")
def reset():
    _clear_latest_result()

    session.pop("latest_form", None)

    return redirect(url_for("index"))


@app.errorhandler(413)
def too_large(_error):
    return render_template(
        "index.html",
        form_data={},
        result=None,
        error="The submitted form is too large.",
        field_errors={},
    ), 413


if __name__ == "__main__":
        app.run(
            debug=os.getenv(
            "FLASK_DEBUG",
            "false",
        ).lower() == "true"
    )