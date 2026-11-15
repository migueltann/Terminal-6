"""LatestResultStore: keeps each web user's latest result in a server file."""

import json
import os
import uuid
from typing import Optional

from flask import session


class LatestResultStore:
    """Save, load and clear the latest generated result for one browser.

    60 recommendations are too big for a cookie (about 4 KB), so the result
    is written to instance/latest_result_<key>.json and the signed session
    cookie only holds the random key.
    """

    SESSION_KEY = "latest_result_key"

    def __init__(self, folder: str) -> None:
        self.__folder = folder      # Flask's instance folder (ignored by git)

    def _path_for(self, result_key) -> Optional[str]:
        """Return the file path for a key, or None if the key is unsafe."""
        if not isinstance(result_key, str) or not result_key:
            return None

        # Only hex characters (0-9, a-f) are allowed. This blocks keys like
        # "../../secret", so a key can never point outside the folder.
        if any(character not in "0123456789abcdef"
               for character in result_key.lower()):
            return None

        return os.path.join(self.__folder, f"latest_result_{result_key}.json")

    def save(self, result: dict) -> None:
        """Save the latest generated result on the server."""
        os.makedirs(self.__folder, exist_ok=True)

        result_key = session.get(self.SESSION_KEY)

        # First result for this user (or a broken key): give them a new
        # random key. Later results reuse the key and overwrite the file.
        if not self._path_for(result_key):
            result_key = uuid.uuid4().hex
            session[self.SESSION_KEY] = result_key

        with open(self._path_for(result_key), "w", encoding="utf-8") as file:
            json.dump(result, file, indent=4, ensure_ascii=False, allow_nan=False)

    def load(self) -> Optional[dict]:
        """Return the current user's latest result, or None.

        Raises nothing: a missing or damaged file just means "no result".
        """
        path = self._path_for(session.get(self.SESSION_KEY))

        if not path or not os.path.isfile(path):
            return None

        try:
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
        except (OSError, json.JSONDecodeError):
            return None

    def clear(self) -> None:
        """Forget the current user's latest result and delete its file."""
        path = self._path_for(session.pop(self.SESSION_KEY, None))

        if path and os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass