"""Saves processed recommendation results to JSON and CSV files."""
#Set up data storage directory and index file
import csv
import json
import os
from datetime import datetime

DATA_DIR = "data"
INDEX_FILE = os.path.join(DATA_DIR, "recommendation_sets.json")


def ensure_storage_directory():
    """Create the data folder and index file if they do not exist yet."""

    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(INDEX_FILE):
        with open(INDEX_FILE, "w", encoding="utf-8") as file:
            json.dump([], file, indent=4)


def _safe_name(value):
    """Create a simple file-safe name from the destination."""

    return "".join(
        character.lower() if character.isalnum() else "_"
        for character in value
    ).strip("_")

def save_processed_recommendations(result):
    """Save approved recommendations in both JSON and CSV format."""

    ensure_storage_directory()

    # Create a unique timestamp for the filenames
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Create a safe destination name
    destination_name = _safe_name(result["destination"])

    # Combine the destination and timestamp
    base_name = f"{destination_name}_{timestamp}"

    # Create the JSON and CSV file paths
    json_path = os.path.join(DATA_DIR, base_name + ".json")
    csv_path = os.path.join(DATA_DIR, base_name + ".csv")

    try:
        # Save the complete processed result as JSON
        with open(json_path, "w", encoding="utf-8") as file:
            json.dump(
                result,
                file,
                indent=4,
                ensure_ascii=False
            )

        # Define the columns for the CSV file
        fieldnames = [
            "type",
            "name",
            "category",
            "estimated_cost_sgd",
            "location",
            "description",
            "tags",
            "transport_options",
            "dietary_tags",
        ]

        # Save approved activities and food as CSV rows
        with open(
            csv_path,
            "w",
            newline="",
            encoding="utf-8"
        ) as file:

            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames
            )

            # Write the column headings
            writer.writeheader()

            # Combine activities, food, accommodation and shopping into one list
            all_approved = (
                result.get("activities", [])
                + result.get("food", [])
                + result.get("accommodation", [])
                + result.get("shopping", [])
            )

            # Write each approved recommendation
            for item in all_approved:
                writer.writerow(
                    {
                        "type": item.get("type", ""),
                        "name": item.get("name", ""),
                        "category": item.get("category", ""),
                        "estimated_cost_sgd": item.get(
                            "estimated_cost_sgd",
                            "",
                        ),
                        "location": item.get("location", ""),
                        "description": item.get("description", ""),
                        "tags": ", ".join(
                            item.get("tags", [])
                        ),
                        "transport_options": ", ".join(
                            item.get("transport_options", [])
                        ),
                        "dietary_tags": ", ".join(
                            item.get("dietary_tags", [])
                        ),
                    }
                )

        # Add this saved result to the small index used by the menu/front end
        saved = load_all_sets()

        summary = result.get("summary", {})

        approved_count = summary.get(
            "approved_count",
            len(all_approved),
        )

        saved.append(
            {
                "destination": result.get("destination", "Unknown"),
                "approved_count": approved_count,
                "json_path": json_path,
                "csv_path": csv_path,
                "saved_at": timestamp,
            }
        )

        with open(INDEX_FILE, "w", encoding="utf-8") as file:
            json.dump(saved, file, indent=4)

        return json_path, csv_path

    except (IOError, OSError):
        return None

def load_all_sets():
    """Load the list of previously saved recommendation sets."""

    ensure_storage_directory()

    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (IOError, json.JSONDecodeError):
        return []

"""Load one saved JSON result."""
def load_result(json_path):

    try:
        with open(json_path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (IOError, json.JSONDecodeError):
        return None

def delete_set(index):
    """Delete one saved result and its JSON/CSV files."""

    saved = load_all_sets()

    if index < 1 or index > len(saved):
        return False

    entry = saved.pop(index - 1)

    # Remove both saved files if they still exist
    for path_key in ("json_path", "csv_path"):
        path = entry.get(path_key)
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    try:
        with open(INDEX_FILE, "w", encoding="utf-8") as file:
            json.dump(saved, file, indent=4)
        return True
    except IOError:
        return False

def save_recommendations(
    destination,
    recommendations_json,
    user_inputs_json="{}",
):
    """Save recommendations received from the Flask website."""

    # Convert JSON text into Python data
    if isinstance(recommendations_json, str):
        recommendations = json.loads(recommendations_json)
    else:
        recommendations = recommendations_json

    if isinstance(user_inputs_json, str):
        user_inputs = json.loads(user_inputs_json)
    else:
        user_inputs = user_inputs_json

    # Separate recommendations according to type
    activities = []
    food = []
    accommodation = []
    shopping = []

    for item in recommendations:
        item_type = item.get("type", "")

        if item_type == "activity":
            activities.append(item)

        elif item_type == "food":
            food.append(item)

        elif item_type == "accommodation":
            accommodation.append(item)

        elif item_type == "shopping":
            shopping.append(item)

    # Build the same structure used by the other managers
    result = {
        "destination": destination,
        "requirements": user_inputs,
        "activities": activities,
        "food": food,
        "accommodation": accommodation,
        "shopping": shopping,
        "summary": {
            "approved_count": len(recommendations),
        },
    }

    saved_paths = save_processed_recommendations(result)

    if saved_paths is None:
        raise RuntimeError(
            "Recommendations could not be saved."
        )

    json_path, csv_path = saved_paths
    return json_path

def get_saved_recommendations():
    """Return saved recommendations in the format used by Flask."""

    saved = load_all_sets()
    result = []

    for entry in saved:
        json_path = entry.get("json_path", "")
        filename = os.path.basename(json_path)

        result.append(
            {
                "filename": filename,
                "destination": entry.get(
                    "destination",
                    "Unknown",
                ),
                "approved_count": entry.get(
                    "approved_count",
                    0,
                ),
                "saved_at": entry.get(
                    "saved_at",
                    "",
                ),
                "json_path": json_path,
                "csv_path": entry.get(
                    "csv_path",
                    "",
                ),
            }
        )

    return result

def delete_saved_recommendation(filename):
    """Delete a saved recommendation using its JSON filename."""

    saved = load_all_sets()

    for index, entry in enumerate(saved, start=1):
        json_path = entry.get("json_path", "")

        if os.path.basename(json_path) == filename:
            return delete_set(index)

    return False

def manage_saved_recommendations():
    """Simple terminal menu for viewing or deleting saved results."""

    import io_manager

    while True:
        saved = load_all_sets()

        if not saved:
            io_manager.display_message(
                "No saved recommendation sets found."
            )
            return

        print("\n" + "=" * 70)
        print("SAVED RECOMMENDATION SETS")
        print("=" * 70)

        for index, entry in enumerate(saved, start=1):
            print(
                f"{index}. {entry.get('destination', 'Unknown')} | "
                f"Approved: {entry.get('approved_count', 0)} | "
                f"{entry.get('saved_at', '')}"
            )

        print("\nEnter a number to view, D to delete, or B to go back.")
        choice = input("Choice: ").strip().lower()

        if choice == "b":
            return

        if choice == "d":
            delete_choice = input("Number to delete: ").strip()

            if delete_choice.isdigit() and delete_set(int(delete_choice)):
                print("Saved recommendation set deleted.")
            else:
                print("Invalid selection.")
            continue

        if choice.isdigit() and 1 <= int(choice) <= len(saved):
            result = load_result(saved[int(choice) - 1]["json_path"])

            if result:
                io_manager.display_approved_recommendations(result)
            else:
                io_manager.display_error(
                    "Saved JSON file could not be read."
                )
        else:
            print("Invalid choice.")
