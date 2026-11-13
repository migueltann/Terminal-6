"""Tests for the terminal ProgressSpinner (no real terminal needed)."""
import io
import threading
import time
from unittest.mock import Mock

from user_io.io_manager import IOManager
from user_io.progress_spinner import ProgressSpinner


def test_format_elapsed_seconds_and_minutes():
    assert ProgressSpinner.format_elapsed(0) == "0s"
    assert ProgressSpinner.format_elapsed(12.9) == "12s"
    assert ProgressSpinner.format_elapsed(75) == "1m 15s"


def test_not_a_terminal_prints_only_the_final_line():
    stream = io.StringIO()            # StringIO is not a tty, so no animation
    spinner = ProgressSpinner("Generating", stream=stream).start()
    spinner.stop("Done")
    assert stream.getvalue() == "\nDone in 0s.\n"


def test_animation_draws_spinner_line_with_timer():
    stream = io.StringIO()
    spinner = ProgressSpinner("Generating", stream=stream, animate=True).start()
    time.sleep(0.25)
    spinner.stop("Done")
    output = stream.getvalue()
    assert "\r| Generating... 0s elapsed" in output
    assert output.endswith("\nDone in 0s.\n")


def test_wrap_still_passes_every_status_message_through():
    stream = io.StringIO()
    notify = Mock()
    spinner = ProgressSpinner("Generating", stream=stream, animate=True).start()
    wrapped = spinner.wrap(notify)

    # The AI threads call notify at the same time.
    threads = [threading.Thread(target=wrapped, args=("info", f"msg {n}"))
               for n in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    spinner.stop()

    assert notify.call_count == 4
    notify.assert_any_call("info", "msg 0")


def test_wrap_none_stays_none():
    assert ProgressSpinner("x", stream=io.StringIO()).wrap(None) is None


def test_context_manager_says_stopped_on_error():
    stream = io.StringIO()
    try:
        with ProgressSpinner("Generating", stream=stream):
            raise RuntimeError("AI failed")
    except RuntimeError:
        pass
    assert "Stopped in 0s." in stream.getvalue()


def test_io_manager_start_spinner_returns_a_running_spinner(capsys):
    spinner = IOManager().start_spinner("Generating recommendations")
    assert isinstance(spinner, ProgressSpinner)
    spinner.stop("Done")
    assert "Done in 0s." in capsys.readouterr().out


def _assistant_with(spinner, ai_error=None):
    from models import UserRequirements
    from travel_assistant import TravelAssistant

    mock_io = Mock()
    mock_io.start_spinner.return_value = spinner
    mock_io.show_menu.side_effect = ["1", "3"]
    requirements = UserRequirements.from_dict({"destination": "Japan"})
    mock_io.collect_requirements.return_value = requirements
    mock_io.confirm_or_edit.return_value = requirements
    mock_io.ask_yes_no.return_value = False

    mock_ai = Mock()
    if ai_error:
        mock_ai.generate_recommendations.side_effect = ai_error
    else:
        mock_ai.generate_recommendations.return_value = []
    assistant = TravelAssistant(io_manager=mock_io, ai_manager=mock_ai,
                                logic_manager=Mock(), data_manager=Mock())
    return assistant, mock_io, mock_ai


def test_terminal_generation_runs_inside_the_spinner():
    spinner = Mock()
    assistant, mock_io, mock_ai = _assistant_with(spinner)
    assistant.run()

    mock_io.start_spinner.assert_called_once_with("Generating recommendations")
    # the AI still gets the IOManager's status printer (wrapped)
    spinner.wrap.assert_called_once_with(mock_io.show_status)
    assert mock_ai.generate_recommendations.call_args.kwargs["notify"] is spinner.wrap.return_value
    spinner.stop.assert_called_once_with("Done")
    mock_io.show_recommendations.assert_called_once()


def test_spinner_is_stopped_when_the_ai_fails():
    spinner = Mock()
    assistant, mock_io, _ = _assistant_with(spinner, RuntimeError("All AI providers failed"))
    assistant.run()

    spinner.stop.assert_called_once_with("Stopped")
    mock_io.show_error.assert_called_once_with("All AI providers failed")