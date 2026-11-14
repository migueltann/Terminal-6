"""Entry point for the terminal version: run "python main.py".

The web version starts from web_app.py instead.
"""
from travel_assistant import TravelAssistant


def main() -> None:
    """Start the OOP travel recommendation application."""
    assistant = TravelAssistant()
    assistant.run()


# True only when this file is run directly, not when it is imported
# (for example by a test), so importing it does not start the app.
if __name__ == "__main__":
    main()
