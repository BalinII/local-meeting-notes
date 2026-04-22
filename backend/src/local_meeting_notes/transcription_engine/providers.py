"""Provider boundary for local transcription backends."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..config import AppConfig


class TranscriptionDependencyError(RuntimeError):
    """Raised when the configured transcription backend cannot be loaded."""


@dataclass(slots=True)
class TranscriptionResult:
    text: str
    provider_name: str
    model_name: str


class TranscriptionProvider(Protocol):
    def transcribe_file(self, chunk_path: Path) -> TranscriptionResult: ...


class FasterWhisperProvider:
    def __init__(self, config: AppConfig) -> None:
        try:
            from faster_whisper import WhisperModel  # type: ignore
        except ImportError as exc:  # pragma: no cover - depends on local install
            raise TranscriptionDependencyError(
                "Local transcription requires the 'faster-whisper' package. "
                "Install backend dependencies before using `transcript transcribe`."
            ) from exc

        self.provider_name = "faster-whisper"
        self.model_name = config.transcription_model_size
        self.model = WhisperModel(
            config.transcription_model_size,
            device=config.transcription_device,
            compute_type="int8",
        )

    def transcribe_file(self, chunk_path: Path) -> TranscriptionResult:
        segments, _info = self.model.transcribe(str(chunk_path), vad_filter=False)
        text = " ".join(segment.text.strip() for segment in segments).strip()
        return TranscriptionResult(
            text=text,
            provider_name=self.provider_name,
            model_name=self.model_name,
        )


def build_transcription_provider(config: AppConfig) -> TranscriptionProvider:
    if config.transcription_provider == "faster-whisper":
        return FasterWhisperProvider(config)
    raise RuntimeError(f"Unsupported transcription provider: {config.transcription_provider}")
