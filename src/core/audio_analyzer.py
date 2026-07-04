"""Audio file analysis via libsndfile (the soundfile package).

soundfile ships libsndfile inside its wheel, so this works from a
PyInstaller .app bundle with no external tools installed - it replaced
the original sox/soxi subprocess approach, which required a Homebrew
install and broke under a Finder-launched app's bare PATH.
"""

import re
from pathlib import Path
from typing import Dict
from dataclasses import dataclass

import soundfile as sf

from .exceptions import AudioAnalysisError, SampleRateMismatchError


@dataclass
class AudioSpec:
    """Audio file specifications."""
    sample_rate: int
    bit_depth: int
    channels: int
    duration: float  # seconds


# libsndfile subtypes that don't encode their width in the name
_SUBTYPE_BITS = {
    "FLOAT": 32,
    "DOUBLE": 64,
    "PCM_S8": 8,
    "PCM_U8": 8,
}


def _bit_depth_from_subtype(subtype: str) -> int:
    """Map a libsndfile subtype (e.g. 'PCM_24') to a bit depth."""
    if subtype in _SUBTYPE_BITS:
        return _SUBTYPE_BITS[subtype]
    match = re.search(r"(\d+)$", subtype)
    if match:
        return int(match.group(1))
    raise AudioAnalysisError(f"Unrecognized audio subtype: {subtype}")


class AudioAnalyzer:
    """Reads audio file specs (sample rate, bit depth, channels, duration)."""

    def analyze_file(self, file_path: Path) -> AudioSpec:
        """
        Analyze a single audio file.

        Args:
            file_path: Path to audio file (.wav or .aif)

        Returns:
            AudioSpec with sample rate, bit depth, channels, duration

        Raises:
            AudioAnalysisError: If file cannot be analyzed
        """
        if not file_path.exists():
            raise AudioAnalysisError(f"File not found: {file_path}")

        try:
            info = sf.info(str(file_path))
        except (sf.LibsndfileError, RuntimeError) as e:
            raise AudioAnalysisError(f"Failed to analyze {file_path.name}: {e}")

        return AudioSpec(
            sample_rate=int(info.samplerate),
            bit_depth=_bit_depth_from_subtype(info.subtype),
            channels=int(info.channels),
            duration=float(info.duration),
        )

    def validate_folder(self, audio_files: list[Path]) -> Dict[str, int]:
        """
        Validate all audio files in folder have matching sample rate and bit depth.

        Args:
            audio_files: List of audio file paths to validate

        Returns:
            Dict with 'sample_rate' and 'bit_depth' keys

        Raises:
            AudioAnalysisError: If no audio files provided
            SampleRateMismatchError: If files have different sample rates or bit depths
        """
        if not audio_files:
            raise AudioAnalysisError("No audio files to validate")

        # Analyze first file to get reference specs
        first_spec = self.analyze_file(audio_files[0])
        reference_sample_rate = first_spec.sample_rate
        reference_bit_depth = first_spec.bit_depth

        # Check all other files match
        mismatches = []
        for audio_file in audio_files[1:]:
            spec = self.analyze_file(audio_file)

            if spec.sample_rate != reference_sample_rate:
                mismatches.append(
                    f"{audio_file.name}: {spec.sample_rate} Hz "
                    f"(expected {reference_sample_rate} Hz)"
                )

            if spec.bit_depth != reference_bit_depth:
                mismatches.append(
                    f"{audio_file.name}: {spec.bit_depth}-bit "
                    f"(expected {reference_bit_depth}-bit)"
                )

        if mismatches:
            error_msg = "Sample rate/bit depth mismatch found:\n" + "\n".join(mismatches)
            raise SampleRateMismatchError(error_msg)

        return {
            "sample_rate": reference_sample_rate,
            "bit_depth": reference_bit_depth
        }
