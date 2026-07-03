"""Validation spike: PTSL v3 import_audio (the one workflow command not yet
live-tested on this machine - docs/DEVELOPER_IMPROVEMENT_PLAN.md section 7.1).

Creates a scratch session under testing/ptsl_audio_spike/, imports the WAV
fixtures from tests/fixtures/ with the exact parameters PTSLWorkflow uses
(CopyAudio + MD_NewTrack + ML_SessionStart), then verifies:

1. The command succeeds (no PT_InvalidParameter).
2. The files were COPIED into the session's Audio Files folder
   (project requirement: copy, never link).
3. The files landed on new tracks (track count grew).

Run with Pro Tools open and idle:
    venv/bin/python prototypes/ptsl_audio_import_spike.py

Safe: writes only under testing/. Delete the output folder afterwards.
"""

import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.protools import ptsl_compat  # noqa: F401  (must precede ptsl import)

from ptsl import open_engine, PTSL_pb2 as pt
from ptsl.errors import CommandError

OUTPUT_DIR = PROJECT_ROOT / "testing" / "ptsl_audio_spike"
FIXTURES = sorted((PROJECT_ROOT / "tests" / "fixtures").glob("48000*.wav"))
SESSION_NAME = f"AudioSpike_{time.strftime('%H%M%S')}"


def main() -> int:
    if not FIXTURES:
        print("No 48kHz fixtures found in tests/fixtures/ - generate with sox first.")
        return 1

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cm = open_engine(
        company_name="Pro Tools Prepper",
        application_name="Audio Import Spike",
    )
    engine = cm.__enter__()
    try:
        print(f"Connected (PTSL version {engine.ptsl_version()})")

        print(f"Creating scratch session {SESSION_NAME!r} (48 kHz / 24-bit)...")
        b = engine.create_session(SESSION_NAME, str(OUTPUT_DIR))
        b.wave_format()
        b.sample_rate(48000)
        b.bit_depth(24)
        b.create()
        time.sleep(8)

        tracks_before = len(engine.track_list())
        print(f"Tracks before import: {tracks_before}")

        print(f"Importing {len(FIXTURES)} file(s) with CopyAudio + MD_NewTrack...")
        engine.import_audio(
            file_list=[str(f) for f in FIXTURES],
            audio_operations=pt.CopyAudio,
            audio_destination=pt.MD_NewTrack,
            audio_location=pt.ML_SessionStart,
        )
        time.sleep(8)

        tracks_after = len(engine.track_list())
        print(f"Tracks after import: {tracks_after}")

        # Verify copy semantics: files must exist in the session's Audio Files
        audio_files_dir = OUTPUT_DIR / SESSION_NAME / "Audio Files"
        copied = list(audio_files_dir.glob("*.wav")) if audio_files_dir.exists() else []
        print(f"Files in {audio_files_dir}: {[f.name for f in copied]}")

        engine.save_session()
        engine.close_session(save_on_close=True)

        print()
        print("=== VERDICT ===")
        ok_tracks = tracks_after > tracks_before
        ok_copied = len(copied) >= len(FIXTURES)
        print(f"New tracks created:      {'PASS' if ok_tracks else 'FAIL'}")
        print(f"Files copied (not linked): {'PASS' if ok_copied else 'FAIL'}")
        if ok_tracks and ok_copied:
            print("import_audio VALIDATED - PTSLWorkflow.import_audio is good to go.")
            return 0
        print("import_audio NOT validated - inspect the session manually;")
        print("consider the AppleScript fallback for step 5 (see plan section 7.1).")
        return 1

    except CommandError as e:
        print(f"PTSL command failed: {e}")
        print("If ErrType 126: a request parameter is rejected on this PTSL build.")
        return 1
    finally:
        cm.__exit__(*sys.exc_info())


if __name__ == "__main__":
    sys.exit(main())
