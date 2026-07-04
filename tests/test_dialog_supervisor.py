"""Tests for dialog supervisor result parsing and sweep behavior."""

from unittest.mock import MagicMock, patch

import pytest

from src.core.exceptions import AppleScriptError, DialogBlockedError
from src.protools.dialog_supervisor import DialogSupervisor


@pytest.fixture
def runner():
    return MagicMock()


@pytest.fixture
def supervisor(runner):
    return DialogSupervisor(runner)


class TestCheck:
    def test_none_returns_empty(self, supervisor, runner):
        runner.run.return_value = "none"
        assert supervisor.check() == ""

    def test_dismissed_returns_label(self, supervisor, runner):
        runner.run.return_value = "dismissed:Missing AAX Plugins"
        assert supervisor.check() == "Missing AAX Plugins"

    def test_unknown_raises_dialog_blocked(self, supervisor, runner):
        runner.run.return_value = "unknown:Scary Error Dialog"
        with pytest.raises(DialogBlockedError) as exc_info:
            supervisor.check()
        assert exc_info.value.dialog_title == "Scary Error Dialog"

    def test_garbage_raises_applescript_error(self, supervisor, runner):
        runner.run.return_value = "something weird"
        with pytest.raises(AppleScriptError, match="unparseable"):
            supervisor.check()

    def test_pace_activation_dismissed(self, supervisor, runner):
        runner.run.return_value = (
            "dismissed:PACE Activation - EchoBoy V5 by Soundtoys requires activation."
        )
        assert supervisor.check().startswith("PACE Activation - EchoBoy V5")

    def test_ax_error_returns_empty(self, supervisor, runner):
        runner.run.return_value = "ax-error:AppleEvent handler failed (-10000)"
        assert supervisor.check() == ""


class TestSweep:
    def test_no_dialogs(self, supervisor, runner):
        runner.run.return_value = "none"
        assert supervisor.sweep() == []
        assert runner.run.call_count == 1

    def test_dismisses_stacked_dialogs_until_none(self, supervisor, runner):
        runner.run.side_effect = [
            "dismissed:Missing AAX Plugins",
            "dismissed:Session Notes",
            "none",
        ]
        assert supervisor.sweep(pause=0) == ["Missing AAX Plugins", "Session Notes"]

    def test_sweep_is_bounded(self, supervisor, runner):
        runner.run.return_value = "dismissed:Missing AAX Plugins"  # forever
        dismissed = supervisor.sweep(max_dismissals=3, pause=0)
        assert len(dismissed) == 3

    def test_unknown_dialog_propagates(self, supervisor, runner):
        runner.run.side_effect = ["dismissed:Session Notes", "unknown:Mystery"]
        with pytest.raises(DialogBlockedError):
            supervisor.sweep(pause=0)

    def test_pace_dismissals_pause_longer(self, supervisor, runner):
        """The next PACE helper process takes seconds to spawn - the sweep
        must wait longer after quitting one so it isn't missed."""
        runner.run.side_effect = [
            "dismissed:PACE Activation - EchoBoy V5 by Soundtoys requires activation.",
            "dismissed:Missing AAX Plugins",
            "none",
        ]
        with patch("src.protools.dialog_supervisor.time.sleep") as mock_sleep:
            dismissed = supervisor.sweep(pause=1.0)
        assert len(dismissed) == 2
        assert mock_sleep.call_args_list[0].args == (3.0,)  # after PACE
        assert mock_sleep.call_args_list[1].args == (1.0,)  # after plain dialog
