"""The Flask web version of the app: run "python web_app.py" and open the page.

It reuses the same classes as the terminal version (TravelAssistant,
DataManager, ItineraryManager...), so the web pages and the terminal give
the same results.

Flask basics used in this file:
- @app.get("/path") / @app.post("/path") connect a URL to the function
  below it (a "route"). GET loads a page; POST sends a form.
- render_template("x.html", ...) fills in an HTML file from templates/.
- redirect(url_for("name")) sends the browser to another route.
- flash(message, "error"/"success") shows a one-time message on the next page.
- session is a small, signed cookie that remembers data for one user.
"""
import io
import json
import os

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
from storage.json_itinerary_repository import JsonItineraryRepository
from storage.itinerary_manager import ItineraryManager
from models import Itinerary
from models import RecommendationSet
from user_io.generation_progress import GenerationProgress
from web import (
    AIErrorTranslator,
    ItineraryPresenter,
    LatestResultStore,
    WebInputValidator,
)

# Load API keys and settings from the .env file.
load_dotenv()


app = Flask(__name__)

# The secret key signs the session cookie so users cannot edit it.
# The fallback is only for running locally; set FLASK_SECRET_KEY in .env
# for anything public.
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "terminal-6-local-development-key",
)

# Reject any request bigger than 1 MB (Flask returns error 413, handled
# by too_large() at the bottom of this file).
app.config["MAX_CONTENT_LENGTH"] = 1 * 1024 * 1024

# Objects shared by every request (created once when the app starts):
# - progress_tracker: live AI progress, polled by the loading screen
# - result_store: each browser's latest result, kept in a server file
# - input_validator: checks the form like IOManager checks the terminal
# - presenter: turns itineraries into data for the itinerary pages
progress_tracker = GenerationProgress()
result_store = LatestResultStore(app.instance_path)
input_validator = WebInputValidator()
presenter = ItineraryPresenter()


# status messages from ai_manager go to the Flask log, not the terminal
def _log_ai_status(level, message):
    """Send AI status messages to the Flask log."""
    if level == "warning":
        app.logger.warning(message)
    else:
        app.logger.info(message)

@app.post("/validate-inputs")
def validate_inputs():
    """Validate the submitted form before starting AI generation."""
    data, errors, field_errors = input_validator.collect(request.form)

    # Called by the page's JavaScript, so reply with JSON instead of HTML.
    return jsonify({
        "valid": not errors,
        "errors": field_errors,
        "message": " ".join(errors),
        # Cleaned name, e.g. "sg" -> "Singapore", for the loading screen.
        "destination": data["destination"],
    })


@app.get("/check-destination")
def check_destination():
    """Check one destination as soon as the user leaves the field.

    Lets the form say "Taken as Singapore" when the user types "sg".
    """
    typed = (request.args.get("destination") or "").strip()

    if not typed:
        return jsonify({"valid": False, "destination": "", "error": ""})

    destination, error = input_validator.check_destination(typed)

    return jsonify({
        "valid": error is None,
        "destination": destination or "",
        "error": error or "",
    })

@app.get("/")
def index():
    """Home page: an empty requirements form."""
    return render_template(
        "index.html",
        form_data={},
        result=None,
        error=None,
        field_errors={},
        )

@app.post("/generate")
def generate():
    """Check the form, ask the AI, filter the results and show them."""
    # Keep what the user typed so the form can be refilled on the page.
    form_data = request.form.to_dict()

    form_data.pop("progress_id", None)   # only used by the loading screen

    user_inputs, errors, field_errors = input_validator.collect(
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
        ), 400  # HTTP 400 = the request had invalid input

    # The loading screen sends a random id so it can ask how the AI is doing.
    progress_id = request.form.get("progress_id", "")
    notify = _log_ai_status

    if GenerationProgress.valid_id(progress_id):
        progress_tracker.start(progress_id)
        # Still logs every message, and also records it for /progress/<id>.
        notify = progress_tracker.notifier(progress_id, also=_log_ai_status)

    try:
        # Convert Flask form data into an OOP requirements object.
        requirements = UserRequirements.from_dict(user_inputs)

        # Generate and filter recommendations through the OOP application.
        assistant = TravelAssistant()

        recommendation_set = assistant.generate_trip(
            requirements,
            notify=notify,
        )

        # Convert the OOP result into the dictionary expected by Flask.
        result = recommendation_set.to_dict()

        # Store the full result on the server, not in the cookie.
        result_store.save(result)

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
        # Write the full error to the log for the developers, and show a
        # friendly version on the page.
        app.logger.exception(
            "Recommendation generation failed"
        )

        message = AIErrorTranslator.friendly(exc)

        return render_template(
            "index.html",
            form_data=form_data,
            result=None,
            error=message,
            technical_error=str(exc),
            field_errors={},
        ), 502  # HTTP 502 = an outside service (the AI) failed

    # Runs whether generation worked or failed, so the loading screen
    # always learns that the request has ended.
    finally:
        progress_tracker.finish(progress_id)


@app.get("/progress/<progress_id>")
def generation_progress(progress_id):
    """How far the AI has got, for the loading screen (polled every second)."""
    snapshot = progress_tracker.snapshot(progress_id)

    if snapshot is None:
        return jsonify({"error": "Unknown progress id."}), 404

    return jsonify(snapshot)


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


# <path:filename> takes that part of the URL and passes it in as filename.
@app.get("/saved/view/<path:filename>")
def view_saved(filename):
    """Display a saved recommendation set using OOP."""
    manager = DataManager(JsonCsvRepository())

    # basename() keeps only the file name, dropping any folder part
    # such as "../", so the URL cannot reach files outside data/.
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

    # Make it the "latest result", so the download and plan buttons on
    # the page work with this saved set.
    result_store.save(result)

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

DEFAULT_DAYS = 3               # days shown when a new itinerary is opened
DEFAULT_DAILY_BUDGET = 200     # SGD per day, the user can change it


# Small helpers so each route does not repeat the set-up code.
def _data_manager():
    return DataManager(JsonCsvRepository())


def _itinerary_manager():
    return ItineraryManager(JsonItineraryRepository())


def _render_builder(set_id, recommendation_set,
                    itinerary=None, itinerary_id=""):
    """Show the builder for a new itinerary, or reopen a saved one."""
    catalog = presenter.catalog(recommendation_set)

    if itinerary is None:
        # New itinerary: start with DEFAULT_DAYS empty days.
        days = [[] for _ in range(DEFAULT_DAYS)]
    else:
        # Restore AI recommendations and personal entries in the builder.
        days = presenter.builder_days(itinerary, recommendation_set)

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

    # The builder needs the original recommendation set to show the
    # places to choose from.
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
        days=presenter.view_days(itinerary),
        # e.g. "16 Nov – 18 Nov 2026"; blank if there is no start date
        date_range=(
            f"{first_date:%d %b} – {last_date:%d %b %Y}" if first_date else ""
        ),
        # Editing needs the original recommendation set to still exist.
        can_edit=_data_manager().load(itinerary.source_id) is not None,
    )


@app.post("/itineraries/save")
def save_itinerary():
    """Create a new itinerary or update an existing one."""
    set_id = os.path.basename(request.form.get("set_id", ""))
    # A blank itinerary_id means this is a new itinerary, not an edit.
    itinerary_id = request.form.get("itinerary_id", "").strip()

    # Where to send the user if something goes wrong: back to the builder.
    back = (
        url_for("edit_itinerary", itinerary_id=itinerary_id)
        if itinerary_id
        else url_for("new_itinerary", set_id=set_id or "missing")
    )

    try:
        # The builder page's JavaScript sends the days as JSON text in a
        # hidden form field called "plan".
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

    # build() checks everything (days, budget, times, overlaps) and raises
    # ValueError with a message the user can understand.
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

    # Going over budget is allowed, but the user is warned.
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
    result = result_store.load()

    if not result:
        flash("Generate recommendations first.", "error")
        return redirect(url_for("index"))

    # An itinerary must point to a saved set, so save the results first.
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
    result = result_store.load()

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
        # (No file is written to disk; BytesIO acts like a file in memory.)
        json_file = io.BytesIO(
            json_content.encode("utf-8")
        )
        json_file.seek(0)   # go back to the start so the whole file is sent

        # as_attachment=True makes the browser download the file instead
        # of opening it.
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
    result = result_store.load()

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
    """Clear the current results and form, and go back to an empty page."""
    result_store.clear()

    session.pop("latest_form", None)

    return redirect(url_for("index"))


# Runs when a request is bigger than MAX_CONTENT_LENGTH (set near the top).
@app.errorhandler(413)
def too_large(_error):
    return render_template(
        "index.html",
        form_data={},
        result=None,
        error="The submitted form is too large.",
        field_errors={},
    ), 413


# Start the web server when this file is run directly.
# Debug mode (auto-reload and detailed error pages) is only switched on
# when FLASK_DEBUG=true is set, because it is unsafe on a public server.
if __name__ == "__main__":
        app.run(
            debug=os.getenv(
            "FLASK_DEBUG",
            "false",
        ).lower() == "true"
    )