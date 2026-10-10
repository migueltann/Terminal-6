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

"""Save approved recommendations in both JSON and CSV format."""
def save_processed_recommendations(result):

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
        saved.append(
            {
                "destination": result["destination"],
                "approved_count": result["summary"]["approved_count"],
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

"""Load the list of previously saved recommendation sets."""
def load_all_sets():

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

"""Delete one saved result and its JSON/CSV files."""
def delete_set(index):

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

"""Simple terminal menu for viewing or deleting saved results."""
def manage_saved_recommendations():

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
