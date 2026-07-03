"""Pro Tools automation layer.

Primary path: PTSL (official gRPC API, Pro Tools 2022.4+; v3 in 2024.3).
AppleScript survives only for MIDI import and the dialog supervisor.
"""

from src.protools.settings import AppSettings
from src.protools.applescript_runner import AppleScriptRunner
from src.protools.dialog_supervisor import DialogSupervisor

__all__ = [
    "AppSettings",
    "AppleScriptRunner",
    "DialogSupervisor",
    "PTSLWorkflow",
    "PTSLClient",
]


def __getattr__(name):
    # PTSLWorkflow/PTSLClient import grpc + ptsl; load them lazily so that
    # settings/UI code can import this package without the ptsl stack.
    if name == "PTSLWorkflow":
        from src.protools.ptsl_workflow import PTSLWorkflow
        return PTSLWorkflow
    if name == "PTSLClient":
        from src.protools.ptsl_client import PTSLClient
        return PTSLClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
