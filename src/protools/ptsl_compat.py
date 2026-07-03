"""Compatibility shim for py-ptsl 301 on protobuf >= 5.

py-ptsl 301.x calls protobuf's json_format with the pre-5.x keyword
`including_default_value_fields`, renamed in protobuf 5 to
`always_print_fields_with_no_presence`. Python >= 3.13 forces protobuf 5+,
so the keyword must be translated before py-ptsl loads.

Call install() before any `import ptsl`. Modules in this package that use
ptsl import this module first.

Remove this shim when py-ptsl is bumped past 301 (Pro Tools upgrade):
401 = 2024.6, 500 = 2024.10, 60x = 2025.6+.
"""

from google.protobuf import json_format as _jf

_installed = False


def _compat(fn):
    def wrapper(*args, **kwargs):
        if "including_default_value_fields" in kwargs:
            kwargs["always_print_fields_with_no_presence"] = kwargs.pop(
                "including_default_value_fields"
            )
        return fn(*args, **kwargs)

    wrapper.__wrapped__ = fn
    return wrapper


def install() -> None:
    """Install the json_format keyword shim (idempotent)."""
    global _installed
    if _installed:
        return
    _jf.MessageToJson = _compat(_jf.MessageToJson)
    _jf.MessageToDict = _compat(_jf.MessageToDict)
    _installed = True


install()
