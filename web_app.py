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

@app.get("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
        app.run(debug=True)