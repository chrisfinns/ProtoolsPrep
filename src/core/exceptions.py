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
    """AppleScript UI scripting failed."""
    pass


class JobExecutionError(PTSessionBuilderError):
    """Workflow step failed during job execution."""
    pass
