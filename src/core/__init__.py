"""Core layer for Pro Tools Session Builder.

Contains business logic for audio analysis, folder scanning, path resolution,
and session specification.
"""

from src.core.audio_analyzer import AudioAnalyzer
from src.core.exceptions import (
    AppleScriptError,
    AudioAnalysisError,
    JobExecutionError,
    PTSessionBuilderError,
    QueueError,
    SampleRateMismatchError,
    ValidationError,
)
from src.core.folder_scanner import FolderScanner
from src.core.path_resolver import PathResolver
from src.core.session_spec import SessionSpec

__all__ = [
    "AudioAnalyzer",
    "FolderScanner",
    "PathResolver",
    "SessionSpec",
    "PTSessionBuilderError",
    "AudioAnalysisError",
    "SampleRateMismatchError",
    "ValidationError",
    "AppleScriptError",
    "JobExecutionError",
    "QueueError",
]
