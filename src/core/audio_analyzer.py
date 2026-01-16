"""Audio file analysis using sox/soxi shell commands."""

import subprocess
import shutil
from pathlib import Path
from typing import Dict, Optional
from dataclasses import dataclass

from .exceptions import AudioAnalysisError, SampleRateMismatchError


@dataclass
class AudioSpec:
    """Audio file specifications."""
    sample_rate: int
    bit_depth: int
    channels: int
    duration: float  # seconds


class AudioAnalyzer:
    """Wraps sox/soxi shell commands to analyze audio files."""

    def __init__(self):
        """Initialize analyzer and verify sox is installed."""
        if not self._is_sox_installed():
            raise AudioAnalysisError(
                "sox is not installed. Install with: brew install sox"
            )

    def _is_sox_installed(self) -> bool:
        """Check if soxi command is available."""
        return shutil.which("soxi") is not None

    def analyze_file(self, file_path: Path) -> AudioSpec:
        """
        Analyze a single audio file using soxi.

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
            # Get sample rate
            sample_rate = int(self._run_soxi(["-r", str(file_path)]))

            # Get bit depth
            bit_depth = int(self._run_soxi(["-b", str(file_path)]))

            # Get channels
            channels = int(self._run_soxi(["-c", str(file_path)]))

            # Get duration
            duration = float(self._run_soxi(["-D", str(file_path)]))

            return AudioSpec(
                sample_rate=sample_rate,
                bit_depth=bit_depth,
                channels=channels,
                duration=duration
            )
        except (ValueError, subprocess.CalledProcessError) as e:
            raise AudioAnalysisError(f"Failed to analyze {file_path.name}: {e}")

    def _run_soxi(self, args: list) -> str:
        """
        Execute soxi command and return output.

        Args:
            args: Command arguments for soxi

        Returns:
            Stripped stdout from command

        Raises:
            subprocess.CalledProcessError: If command fails
        """
        result = subprocess.run(
            ["soxi"] + args,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()

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
