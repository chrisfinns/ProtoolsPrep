"""Tests for AppSettings persistence, defaults, and legacy-file tolerance."""

import json

import pytest

from src.protools.settings import AppSettings


@pytest.fixture
def settings_path(tmp_path, monkeypatch):
    path = tmp_path / "settings.json"
    monkeypatch.setattr(AppSettings, "get_settings_path", classmethod(lambda cls: path))
    return path


class TestDefaults:
    def test_ptsl_defaults(self):
        s = AppSettings()
        assert s.ptsl_port == 31416
        assert s.ptsl_settle_time == 8.0
        assert s.ptsl_connect_timeout == 240.0
        assert s.save_poll_timeout == 30.0

    def test_surviving_applescript_defaults(self):
        s = AppSettings()
        assert s.dialog_wait_time == 2.0
        assert s.midi_import_timeout == 60.0


class TestPersistence:
    def test_round_trip(self, settings_path):
        s = AppSettings()
        s.ptsl_settle_time = 12.5
        s.save_poll_timeout = 45.0
        s.root_output_dir = "/tmp/out"
        s.save()

        loaded = AppSettings.load()
        assert loaded.ptsl_settle_time == 12.5
        assert loaded.save_poll_timeout == 45.0
        assert loaded.root_output_dir == "/tmp/out"

    def test_missing_file_returns_defaults(self, settings_path):
        s = AppSettings.load()
        assert s.ptsl_port == 31416
        assert s.root_output_dir is not None  # testing dir default

    def test_legacy_keys_ignored(self, settings_path):
        # A settings file from the AppleScript era must still load: removed
        # knobs (window_appearance_timeout etc.) are silently dropped.
        legacy = {
            "dialog_wait_time": 3.0,
            "import_completion_timeout": 90.0,
            "window_appearance_timeout": 15.0,
            "applescript_retry_attempts": 5,
            "applescript_retry_delay": 2.0,
            "root_output_dir": "/tmp/legacy",
        }
        settings_path.write_text(json.dumps(legacy))

        s = AppSettings.load()
        assert s.dialog_wait_time == 3.0          # surviving key kept
        assert s.root_output_dir == "/tmp/legacy"
        assert s.ptsl_settle_time == 8.0          # new key gets default
        assert not hasattr(s, "window_appearance_timeout")

    def test_corrupted_file_returns_defaults(self, settings_path):
        settings_path.write_text("{not json")
        s = AppSettings.load()
        assert s.ptsl_port == 31416
