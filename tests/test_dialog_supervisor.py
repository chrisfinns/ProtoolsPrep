"""Tests for dialog supervisor result parsing and sweep behavior."""

from unittest.mock import MagicMock

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
