"""Read-only PTSL connection probe.

Connects to the running Pro Tools instance and reports:
- PTSL version negotiated
- Currently open session (if any)
- Which commands relevant to our workflow respond

Safe to run any time: makes no changes to Pro Tools state.

Usage:
    venv/bin/python prototypes/ptsl_probe.py
"""

import sys

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


def main() -> int:
    try:
        cm = open_engine(
            company_name="Pro Tools Prepper",
            application_name="PTSL Probe",
        )
        engine = cm.__enter__()
    except Exception as e:
        print(f"FAILED to connect to Pro Tools PTSL server: {e}")
        print("Is Pro Tools running? (PTSL listens on localhost:31416)")
        return 1

    try:
        print(f"Connected. PTSL version: {engine.ptsl_version()}")

        try:
            name = engine.session_name()
            print(f"Open session: {name}")
            print(f"  path: {engine.session_path()}")
            print(f"  sample rate: {engine.session_sample_rate()}")
        except CommandError as e:
            print(f"No open session (or session query failed): {e}")

        # Probe command availability without executing anything mutating.
        # A command missing from this PTSL version fails distinctly from
        # a command that exists but has invalid/empty args.
        for attr in (
            "create_session",
            "create_session_from_template",
            "import_data",
            "import_audio",
            "save_session",
            "save_session_as",
            "close_session",
            "open_session",
            "export_session_as_text",
        ):
            present = hasattr(engine, attr)
            print(f"  engine.{attr}: {'available in client' if present else 'MISSING'}")
    finally:
        cm.__exit__(*sys.exc_info())

    print("Probe complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
