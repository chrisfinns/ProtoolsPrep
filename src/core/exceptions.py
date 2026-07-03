"""Exception hierarchy for Pro Tools Session Builder."""


class PTSessionBuilderError(Exception):
    """Base exception for all Pro Tools Session Builder errors."""
    pass


class AudioAnalysisError(PTSessionBuilderError):
    """Error during audio file analysis."""
    pass


class SampleRateMismatchError(AudioAnalysisError):
    """Different sample rates found in folder."""
    pass


class ValidationError(PTSessionBuilderError):
    """Invalid session specification."""
    pass


class AppleScriptError(PTSessionBuilderError):
    """AppleScript UI scripting failed (surviving scripts: MIDI import, dialog supervisor)."""
    pass


class PTSLError(PTSessionBuilderError):
    """Pro Tools Scripting Library (gRPC) operation failed."""
    pass


class ProToolsNotRunningError(PTSLError):
    """PTSL endpoint unreachable - Pro Tools not running or crashed."""
    pass


class SessionBlockedError(PTSLError):
    """PTSL reported PT_NoOpenedSession (106).

    CAUTION: this means "no session open OR a modal dialog is blocking".
    Callers must run the dialog supervisor and re-query state before
    concluding that no session is open.
    """
    pass


class PTSLParameterError(PTSLError):
    """PTSL rejected a request parameter (PT_InvalidParameter, 126). Non-retryable."""
    pass


class DialogBlockedError(PTSLError):
    """An unknown (non-whitelisted) dialog is blocking Pro Tools."""

    def __init__(self, dialog_title: str):
        self.dialog_title = dialog_title
        super().__init__(f"Pro Tools is blocked by an unrecognized dialog: {dialog_title!r}")


class JobExecutionError(PTSessionBuilderError):
    """Workflow step failed during job execution."""
    pass


class QueueError(PTSessionBuilderError):
    """Error during queue operations."""
    pass
