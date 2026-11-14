"""A small terminal spinner that shows how long the AI has been working."""

import sys
import threading
import time
from typing import Callable, Optional, TextIO


class ProgressSpinner:
    """Animate one line such as "| Generating recommendations... 12s".

    The spinner runs in its own background thread, so the main thread can
    keep waiting for the AI. Status messages printed while it spins (for
    example "[INFO] [food] Trying Gemini model: ...") are still printed in
    full: wrap() clears the spinner line first, prints the message, and the
    spinner is drawn again underneath it.

    When the output is not a real terminal (tests, CI, Docker without -t)
    nothing is animated, because "\\r" would only fill the log with
    half-lines. Only the final "Done in ..." line is printed.
    """

    # Shown one after another, these look like a spinning line.
    # ("\\" is one backslash; a single "\" would start an escape code.)
    FRAMES = ("|", "/", "-", "\\")
    INTERVAL = 0.1          # seconds between frames

    def __init__(self, message: str, stream: Optional[TextIO] = None,
                 animate: Optional[bool] = None) -> None:
        self._message = message
        self._stream = stream if stream is not None else sys.stdout
        # Only animate on a real terminal unless told otherwise.
        # isatty() is True for a real terminal. getattr(..., lambda: False)
        # is a fallback for streams that do not have isatty() at all.
        if animate is None:
            animate = bool(getattr(self._stream, "isatty", lambda: False)())
        self._animate = animate
        self._lock = threading.Lock()       # one writer at a time
        # An Event is a thread-safe on/off flag: stop() turns it on, and
        # the spinner thread checks it to know when to finish.
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._start_time = 0.0
        self._line_length = 0               # length of the spinner line on screen

    # ---------- public ----------

    def start(self) -> "ProgressSpinner":
        """Start the clock (and the animation on a real terminal)."""
        self._start_time = time.monotonic()
        self._stop_event.clear()
        if self._animate:
            # daemon=True so the spinner can never keep the program open
            self._thread = threading.Thread(target=self._spin, daemon=True,
                                            name="progress-spinner")
            self._thread.start()
        return self

    def stop(self, final_message: str = "Done") -> float:
        """Stop the animation and print how long it took. Returns seconds."""
        elapsed = self.elapsed()
        self._stop_event.set()          # tell the spinner thread to stop
        if self._thread is not None:
            self._thread.join()         # wait until it has actually stopped
            self._thread = None
        with self._lock:
            self._clear_line()
            self._stream.write(f"\n{final_message} in {self.format_elapsed(elapsed)}.\n")
            self._stream.flush()
        return elapsed

    def wrap(self, notify: Optional[Callable[[str, str], None]]
             ) -> Optional[Callable[[str, str], None]]:
        """Return a notify function that prints around the spinner line."""
        if notify is None:
            return None

        def notify_with_spinner(level: str, message: str) -> None:
            # The AI threads call this, so take the lock before printing.
            with self._lock:
                self._clear_line()
                notify(level, message)
                self._stream.flush()

        return notify_with_spinner

    def elapsed(self) -> float:
        """Seconds since start()."""
        return time.monotonic() - self._start_time if self._start_time else 0.0

    @staticmethod
    def format_elapsed(seconds: float) -> str:
        """12 -> '12s', 75 -> '1m 15s'."""
        whole = int(seconds)
        if whole < 60:
            return f"{whole}s"
        return f"{whole // 60}m {whole % 60:02d}s"

    # context manager: with ProgressSpinner("...") as spinner:
    # __enter__ runs at the start of the "with" block and __exit__ at the
    # end, even if an error happens inside it.
    def __enter__(self) -> "ProgressSpinner":
        return self.start()

    # exc_type is the error's type if the block failed, otherwise None.
    def __exit__(self, exc_type, exc, traceback) -> None:
        self.stop("Stopped" if exc_type else "Done")

    # ---------- private ----------

    def _spin(self) -> None:
        """Runs in the background thread until stop() is called."""
        frame = 0
        while not self._stop_event.is_set():
            with self._lock:
                # "% len" loops the frame number back to 0 after the last frame
                self._draw(self.FRAMES[frame % len(self.FRAMES)])
            frame += 1
            # Sleep for INTERVAL, but wake up straight away if stop() is called
            self._stop_event.wait(self.INTERVAL)

    def _draw(self, symbol: str) -> None:
        """Redraw the spinner line in place."""
        # "\r" (carriage return) moves the cursor back to the start of the
        # line without a new line, so the next write overwrites it.
        line =f"{symbol} {self._message}... {self.format_elapsed(self.elapsed())} elapsed"
        # pad with spaces so a shorter line fully covers the longer one
        padding = " " * max(0, self._line_length - len(line))
        self._stream.write("\r" + line + padding)
        self._stream.flush()
        self._line_length = len(line)

    def _clear_line(self) -> None:
        """Wipe the spinner line by overwriting it with spaces."""
        if self._line_length:
            self._stream.write("\r" + " " * self._line_length + "\r")
            self._line_length = 0