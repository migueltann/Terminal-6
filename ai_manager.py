import json
import os
import time

import requests

def generate_recommendations(destination):
    """Ask Gemini for a generic list of activities and food places."""

    # Read the Gemini API key from the .env file
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is missing.")