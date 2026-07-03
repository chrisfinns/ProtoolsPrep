"""Tests for PTSLWorkflow with a mocked PTSL client/engine.

Covers the behaviors that matter most (docs/DEVELOPER_IMPROVEMENT_PLAN.md):
- the import_data timecode quirk (section 3.1)
- state-aware 106 recovery: sweep dialogs, verify state, only then re-issue
- postcondition verification (session name after create, track count after
  template import, .ptx on disk after save)
"""

import contextlib
import threading
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from src.core.exceptions import PTSLError, SessionBlockedError
from src.protools.ptsl_workflow import PTSLWorkflow
from src.protools.settings import AppSettings


@pytest.fixture
def settings():
    s = AppSettings()
    s.ptsl_settle_time = 0.0     # keep tests fast
    s.save_poll_timeout = 0.5
    return s


@pytest.fixture
def engine():
    return MagicMock()


@pytest.fixture
def client(engine):
    """Fake PTSLClient: passthrough error translation, no-op pacing."""
    c = MagicMock()
    c.engine.return_value = engine
    c.translate_errors = contextlib.nullcontext
    return c


@pytest.fixture
def supervisor():
    s = MagicMock()
    s.sweep.return_value = []
    return s


@pytest.fixture
def workflow(settings, client, supervisor):
    return PTSLWorkflow(
        settings, client=client, runner=MagicMock(), supervisor=supervisor
    )


class TestCreateSession:
    def test_builder_called_with_int_hz(self, workflow, engine, tmp_path):
        builder = MagicMock()
        engine.create_session.return_value = builder
        engine.session_name.return_value = "My Song"
        output_dir = tmp_path / "Artist" / "My Song"

        workflow.create_session("My Song", 48000, 24, output_dir)

        engine.create_session.assert_called_once_with("My Song", str(output_dir.parent))
        builder.wave_format.assert_called_once()
        builder.sample_rate.assert_called_once_with(48000)  # int Hz, not "48 kHz"
        builder.bit_depth.assert_called_once_with(24)
        builder.create.assert_called_once()

    def test_parent_dir_created(self, workflow, engine, tmp_path):
        engine.session_name.return_value = "Song"
        output_dir = tmp_path / "Artist" / "Album" / "Song"
        workflow.create_session("Song", 44100, 16, output_dir)
        assert output_dir.parent.exists()

    def test_wrong_session_open_fails_verification(self, workflow, engine, tmp_path):
        engine.session_name.return_value = "Some Other Session"
        with pytest.raises(PTSLError, match="verification failed"):
            workflow.create_session("My Song", 48000, 24, tmp_path / "a" / "My Song")

    def test_blocked_create_not_reissued_if_it_went_through(
        self, workflow, engine, supervisor, tmp_path
    ):
        # create raises 106 (modal), but after the sweep the session IS open:
        # the queued command executed. Re-issuing would double-create.
        builder = MagicMock()
        builder.create.side_effect = SessionBlockedError("blocked")
        engine.create_session.return_value = builder
        engine.session_name.return_value = "Song"

        workflow.create_session("Song", 48000, 24, tmp_path / "a" / "Song")

        supervisor.sweep.assert_called()
        assert builder.create.call_count == 1  # NOT re-issued

    def test_blocked_create_reissued_if_it_did_not_happen(
        self, workflow, engine, supervisor, tmp_path
    ):
        builder = MagicMock()
        builder.create.side_effect = [SessionBlockedError("blocked"), None]
        engine.create_session.return_value = builder
        # First query (state check): no session; final verify: correct name
        engine.session_name.side_effect = [SessionBlockedError("none"), "Song"]

        # Recreate builder on second create_session call
        workflow.create_session("Song", 48000, 24, tmp_path / "a" / "Song")

        assert builder.create.call_count == 2


class TestImportTemplate:
    def test_timecode_quirk_and_builder_options(self, workflow, engine, tmp_path):
        template = tmp_path / "Template.ptx"
        template.touch()
        imp = MagicMock()
        engine.import_data.return_value = imp
        engine.track_list.return_value = [MagicMock()] * 87

        workflow.import_template(template)

        engine.import_data.assert_called_once_with(str(template))
        imp.import_as_new_tracks.assert_called_once()
        imp.link_to_source_audio.assert_called_once()
        imp.maintain_absolute_timecode.assert_called_once()
        imp.import_clips_and_media.assert_called_once()
        # The PTSL v3 quirk: empty default -> PT_InvalidParameter (126)
        assert imp._timecode_mapping_start_time == "00:00:00:00"
        imp.import_data.assert_called_once()

    def test_missing_template_raises(self, workflow, tmp_path):
        with pytest.raises(ValueError, match="not found"):
            workflow.import_template(tmp_path / "nope.ptx")

    def test_zero_tracks_fails_postcondition(self, workflow, engine, tmp_path):
        template = tmp_path / "Template.ptx"
        template.touch()
        engine.import_data.return_value = MagicMock()
        engine.track_list.return_value = []

        with pytest.raises(PTSLError, match="no tracks"):
            workflow.import_template(template)

    def test_supervisor_sweeps_after_import(
        self, workflow, engine, supervisor, tmp_path
    ):
        # Missing AAX Plugins fires after every import on this machine
        template = tmp_path / "Template.ptx"
        template.touch()
        engine.import_data.return_value = MagicMock()
        engine.track_list.return_value = [MagicMock()]

        workflow.import_template(template)

        supervisor.sweep.assert_called()

    def test_blocked_import_not_reissued_if_tracks_arrived(
        self, workflow, engine, supervisor, tmp_path
    ):
        template = tmp_path / "Template.ptx"
        template.touch()
        imp = MagicMock()
        imp.import_data.side_effect = SessionBlockedError("blocked")
        engine.import_data.return_value = imp
        engine.track_list.return_value = [MagicMock()] * 5  # import DID land

        workflow.import_template(template)

        assert imp.import_data.call_count == 1  # NOT re-issued

    def test_verification_waits_out_pace_blockage(
        self, workflow, engine, settings, tmp_path
    ):
        # Live-observed: PACE/iLok activation windows keep track_list
        # returning 106 until the user presses Quit. A blocked query must
        # be waited out, never read as "zero tracks".
        template = tmp_path / "Template.ptx"
        template.touch()
        engine.import_data.return_value = MagicMock()
        engine.track_list.side_effect = [
            SessionBlockedError("PACE dialog up"),
            SessionBlockedError("PACE dialog up"),
            [MagicMock()] * 87,  # user pressed Quit; real answer arrives
        ]

        with patch("src.protools.ptsl_workflow.time.sleep"):
            workflow.import_template(template)  # must not raise

    def test_verification_blocked_past_timeout_raises(
        self, workflow, engine, settings, tmp_path
    ):
        settings.user_dialog_timeout = 0.1
        template = tmp_path / "Template.ptx"
        template.touch()
        engine.import_data.return_value = MagicMock()
        engine.track_list.side_effect = SessionBlockedError("forever blocked")

        with patch("src.protools.ptsl_workflow.time.sleep"):
            with pytest.raises(PTSLError, match="stayed blocked"):
                workflow.import_template(template)


class TestImportAudio:
    def test_copy_semantics_parameters(self, workflow, engine, tmp_path):
        from ptsl import PTSL_pb2 as pt

        files = [tmp_path / "a.wav", tmp_path / "b.wav"]
        workflow.import_audio(files)

        kwargs = engine.import_audio.call_args.kwargs
        assert kwargs["file_list"] == [str(f) for f in files]
        assert kwargs["audio_operations"] == pt.CopyAudio  # copy, never link
        assert kwargs["audio_destination"] == pt.MD_NewTrack

    def test_empty_list_raises(self, workflow):
        with pytest.raises(ValueError):
            workflow.import_audio([])


class TestSaveSession:
    def test_polls_until_file_exists(self, workflow, engine, tmp_path):
        session_file = tmp_path / "Song.ptx"

        def create_late():
            threading.Timer(0.1, session_file.touch).start()

        engine.save_session.side_effect = create_late
        workflow.save_session(session_file)  # must not raise

    def test_times_out_if_file_never_appears(self, workflow, engine, tmp_path):
        with pytest.raises(PTSLError, match="did not appear"):
            workflow.save_session(tmp_path / "never.ptx")


class TestCloseSession:
    def test_close_saves(self, workflow, engine):
        workflow.close_session()
        engine.close_session.assert_called_once_with(save_on_close=True)

    def test_persistent_106_means_already_closed(self, workflow, engine, supervisor):
        engine.close_session.side_effect = SessionBlockedError("no session")
        workflow.close_session()  # must not raise
        supervisor.sweep.assert_called()


class TestLaunch:
    def test_endpoint_up_skips_launching(self, workflow, client):
        client.is_endpoint_up.return_value = True
        workflow.launch()
        client.ensure_ready.assert_called_once()
