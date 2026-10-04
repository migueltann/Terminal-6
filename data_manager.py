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

            # Combine activities and food into one list
            all_approved = (
                result.get("activities", [])
                + result.get("food", [])
            )

            # Write each approved recommendation
            for item in all_approved:
                writer.writerow(
                    {
                        "type": item["type"],
                        "name": item["name"],
                        "category": item["category"],
                        "estimated_cost_sgd": item[
                            "estimated_cost_sgd"
                        ],
                        "location": item["location"],
                        "description": item["description"],
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
        