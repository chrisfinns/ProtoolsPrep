"""PTSL end-to-end prototype: create session -> import template -> save -> close.

Mirrors the app's core workflow (JobExecutor steps 4, 7, 8, 9) using the
official Pro Tools Scripting Library instead of AppleScript UI scripting.

Creates a throwaway session under testing/ptsl_prototype/ — safe to delete.

Usage:
    venv/bin/python prototypes/ptsl_prototype.py
"""

import sys
import time
from pathlib import Path

# py-ptsl 301.x calls protobuf's json_format with the pre-5.x keyword
# `including_default_value_fields`, renamed in protobuf 5 to
# `always_print_fields_with_no_presence`. Python 3.14 forces protobuf 5+,
# so translate the keyword before py-ptsl loads.
from google.protobuf import json_format as _jf

def _compat(fn):
    def wrapper(*args, **kwargs):
        if "including_default_value_fields" in kwargs:
            kwargs["always_print_fields_with_no_presence"] = kwargs.pop(
                "including_default_value_fields"
            )
        return fn(*args, **kwargs)
    return wrapper

_jf.MessageToJson = _compat(_jf.MessageToJson)
_jf.MessageToDict = _compat(_jf.MessageToDict)

from ptsl import open_engine
from ptsl.errors import CommandError

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "testing" / "ptsl_prototype"
SESSION_NAME = f"PTSL_Test_{time.strftime('%H%M%S')}"
TEMPLATE = Path(
    "/Users/chris/Library/Mobile Documents/com~apple~CloudDocs/BIOMES/Audio"
    "/_TEMPLATES/Mix Templates/Speed Mix TEmplate/Speed Mix Template.ptx"
)


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    cm = open_engine(
        company_name="Pro Tools Prepper",
        application_name="PTSL Prototype",
    )
    engine = cm.__enter__()
    try:
        print(f"Connected (PTSL version {engine.ptsl_version()})")

        # --- Step: create session (replaces create_session.applescript) ---
        print(f"Creating session {SESSION_NAME!r} at {OUTPUT_DIR} (48 kHz / 24-bit WAV)...")
        b = engine.create_session(SESSION_NAME, str(OUTPUT_DIR))
        b.wave_format()
        b.sample_rate(48000)
        b.bit_depth(24)
        b.create()
        print(f"  created. Open session: {engine.session_name()}")
        print(f"  session path: {engine.session_path()}")

        # --- Step: import template (replaces import_template.applescript) ---
        if TEMPLATE.exists():
            print(f"Importing session data from template: {TEMPLATE.name}")
            imp = engine.import_data(str(TEMPLATE))
            imp.import_as_new_tracks()       # was: AXPress row 1 + Cmd+A hack
            imp.link_to_source_audio()       # no copy/SRC of template media
            imp.maintain_absolute_timecode() # was: dismiss Session Start Time warning
            imp.import_data()
            print("  template imported.")

            tracks = engine.track_list() if hasattr(engine, "track_list") else None
            if tracks is not None:
                print(f"  session now has {len(tracks)} tracks:")
                for t in tracks[:12]:
                    print(f"    - {t.name}")
        else:
            print(f"Template not found at {TEMPLATE}, skipping import step.")

        # --- Step: save (replaces save_session.applescript) ---
        print("Saving session...")
        engine.save_session()

        # --- Step: close (replaces close_session.applescript) ---
        print("Closing session...")
        engine.close_session(save_on_close=True)

    except CommandError as e:
        print(f"PTSL command failed: {e}")
        return 1
    finally:
        cm.__exit__(*sys.exc_info())

    # Verify the .ptx landed on disk where the app expects it
    expected = OUTPUT_DIR / SESSION_NAME / f"{SESSION_NAME}.ptx"
    if expected.exists():
        print(f"VERIFIED: {expected}")
    else:
        hits = list(OUTPUT_DIR.rglob("*.ptx"))
        print(f"Session file not at expected path {expected}")
        print(f"  .ptx files found under {OUTPUT_DIR}: {hits}")

    print("Prototype complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
