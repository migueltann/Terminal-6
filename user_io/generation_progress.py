"""Live progress of web generation requests, read by the loading screen."""

import re
import threading
import time
from typing import Callable, Optional


class GenerationProgress:
    """Remembers what the AI is doing for each web request.

    The browser sends a random progress id with its /generate request and
    then asks /progress/<id> about once a second. The AI threads report
    through notify(), which is the same (level, message) callback the
    terminal uses, so no AI code had to change.

    Old entries are dropped after MAX_AGE seconds so memory stays small.
    """

    CATEGORY_COUNT = 4                   # activity, food, accommodation, shopping
    MAX_AGE = 30 * 60                    # forget a request after 30 minutes
    _ID_PATTERN = re.compile(r"^[A-Za-z0-9-]{8,64}$")
    _MODEL_PATTERN = re.compile(r"Trying (?:Gemini|Groq) model: (\S+)")
    _DONE_PATTERN = re.compile(r"^\[(\w+)\] .*succeeded using")

    def __init__(self) -> None:
        self._jobs: dict[str, dict] = {}
        self._lock = threading.Lock()    # the four AI threads write at once

    @classmethod
    def valid_id(cls, progress_id: str) -> bool:
        """Only accept short ids made of letters, digits and dashes."""
        return bool(cls._ID_PATTERN.match(progress_id or ""))

    def start(self, progress_id: str) -> None:
        with self._lock:
            self._forget_old()
            self._jobs[progress_id] = {
                "started": time.monotonic(),
                "message": "Sending your requirements to the AI…",
                "model": "",
                "done": set(),           # categories that have finished
                "finished": False,
            }

    def notifier(self, progress_id: str,
                 also: Optional[Callable[[str, str], None]] = None
                 ) -> Callable[[str, str], None]:
        """A notify(level, message) that records progress, then calls `also`."""
        def notify(level: str, message: str) -> None:
            self.update(progress_id, message)
            if also is not None:
                also(level, message)
        return notify

    def update(self, progress_id: str, message: str) -> None:
        with self._lock:
            job = self._jobs.get(progress_id)
            if job is None:
                return
            model = self._MODEL_PATTERN.search(message)
            if model:
                job["model"] = model.group(1)
            done = self._DONE_PATTERN.match(message)
            if done:
                job["done"].add(done.group(1))
            job["message"] = message

    def finish(self, progress_id: str) -> None:
        with self._lock:
            if progress_id in self._jobs:
                self._jobs[progress_id]["finished"] = True

    def snapshot(self, progress_id: str) -> Optional[dict]:
        """What the loading screen shows, or None if the id is unknown."""
        with self._lock:
            job = self._jobs.get(progress_id)
            if job is None:
                return None
            return {
                "message": job["message"],
                "model": job["model"],
                "categories_done": len(job["done"]),
                "categories_total": self.CATEGORY_COUNT,
                "elapsed": round(time.monotonic() - job["started"], 1),
                "finished": job["finished"],
            }

    def _forget_old(self) -> None:
        now = time.monotonic()
        for key in [key for key, job in self._jobs.items()
                    if now - job["started"] > self.MAX_AGE]:
            del self._jobs[key]