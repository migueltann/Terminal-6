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



@app.get("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
        app.run(debug=True)