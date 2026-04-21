"""Optional imports for real audio capture libraries."""

from __future__ import annotations


class AudioDependencyError(RuntimeError):
    """Raised when the audio capture dependencies are unavailable."""


def load_audio_dependencies() -> tuple[object, object]:
    try:
        import soundcard as soundcard  # type: ignore
        import soundfile as soundfile  # type: ignore
    except ImportError as exc:
        raise AudioDependencyError(
            "Windows audio capture requires the 'soundcard' and 'soundfile' packages. "
            "Install backend audio dependencies before using `audio` commands."
        ) from exc

    return soundcard, soundfile
