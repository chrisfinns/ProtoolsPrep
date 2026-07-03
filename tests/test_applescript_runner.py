"""Tests for the minimal AppleScript runner (escaping, encodings, timeouts)."""

import subprocess
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.core.exceptions import AppleScriptError
from src.protools.applescript_runner import (
    AppleScriptRunner,
    escape_applescript_string,
    DEFAULT_TIMEOUT,
    TIMEOUT_MARGIN,
)


class TestEscaping:
    def test_plain_string_unchanged(self):
        assert escape_applescript_string("My Song") == "My Song"

    def test_double_quotes_escaped(self):
        assert escape_applescript_string('Song "Live" Take') == 'Song \\"Live\\" Take'

    def test_backslashes_escaped(self):
        assert escape_applescript_string("a\\b") == "a\\\\b"

    def test_backslash_before_quote_order(self):
        # Backslashes must be escaped BEFORE quotes, or the quote's new
        # backslash would itself get doubled.
        assert escape_applescript_string('\\"') == '\\\\\\"'

    def test_path_with_spaces_unchanged(self):
        assert (
            escape_applescript_string("/Users/chris/My Music/Song.wav")
            == "/Users/chris/My Music/Song.wav"
        )


@pytest.fixture
def scripts_dir(tmp_path):
    d = tmp_path / "scripts"
    d.mkdir()
    return d


@pytest.fixture
def runner(scripts_dir):
    return AppleScriptRunner(scripts_dir=scripts_dir)


def _fake_run_result(returncode=0, stdout="ok", stderr=""):
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


class TestRunner:
    def test_missing_scripts_dir_raises(self, tmp_path):
        with pytest.raises(AppleScriptError, match="Scripts directory not found"):
            AppleScriptRunner(scripts_dir=tmp_path / "nope")

    def test_missing_script_raises(self, runner):
        with pytest.raises(AppleScriptError, match="Script not found"):
            runner.run("does_not_exist")

    def test_placeholders_substituted_and_escaped(self, runner, scripts_dir):
        (scripts_dir / "t.applescript").write_text('return "{name}"')
        with patch("subprocess.run", return_value=_fake_run_result()) as mock_run:
            runner.run("t", placeholders={"name": 'A "B" C'})
        script = mock_run.call_args[0][0][2]
        assert script == 'return "A \\"B\\" C"'

    def test_returns_stripped_stdout(self, runner, scripts_dir):
        (scripts_dir / "t.applescript").write_text("return 1")
        with patch("subprocess.run", return_value=_fake_run_result(stdout="none\n")):
            assert runner.run("t") == "none"

    def test_nonzero_exit_raises_with_stderr(self, runner, scripts_dir):
        (scripts_dir / "t.applescript").write_text("return 1")
        with patch(
            "subprocess.run",
            return_value=_fake_run_result(returncode=1, stdout="", stderr="boom"),
        ):
            with pytest.raises(AppleScriptError, match="boom"):
                runner.run("t")

    def test_timeout_derived_from_internal_wait(self, runner, scripts_dir):
        (scripts_dir / "t.applescript").write_text("return 1")
        with patch("subprocess.run", return_value=_fake_run_result()) as mock_run:
            runner.run("t", max_internal_wait=300.0)
        assert mock_run.call_args.kwargs["timeout"] == 300.0 + TIMEOUT_MARGIN

    def test_timeout_has_floor(self, runner, scripts_dir):
        (scripts_dir / "t.applescript").write_text("return 1")
        with patch("subprocess.run", return_value=_fake_run_result()) as mock_run:
            runner.run("t")  # no internal wait
        assert mock_run.call_args.kwargs["timeout"] == DEFAULT_TIMEOUT

    def test_subprocess_timeout_raises(self, runner, scripts_dir):
        (scripts_dir / "t.applescript").write_text("return 1")
        with patch(
            "subprocess.run",
            side_effect=subprocess.TimeoutExpired(cmd="osascript", timeout=60),
        ):
            with pytest.raises(AppleScriptError, match="timeout"):
                runner.run("t")

    def test_utf16_script_readable(self, runner, scripts_dir):
        # Script Editor re-saves as UTF-16; the runner must cope.
        (scripts_dir / "t.applescript").write_bytes('return "{x}"'.encode("utf-16-le"))
        with patch("subprocess.run", return_value=_fake_run_result()) as mock_run:
            runner.run("t", placeholders={"x": "hi"})
        assert mock_run.call_args[0][0][2] == 'return "hi"'
