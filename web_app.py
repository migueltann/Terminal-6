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

app = Flask(__name__)

@app.get("/")
def index():
    return render_template("index.html")

if __name__ == "__main__":
        app.run(debug=True)