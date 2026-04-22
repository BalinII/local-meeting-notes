"""Provider boundary for offline diarization backends."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..config import AppConfig


@dataclass(slots=True)
class DiarizationResultSegment:
    start_offset_seconds: int
    end_offset_seconds: int
    speaker_label: str
    confidence: float | None = None


class DiarizationProvider(Protocol):
    def diarize_file(self, audio_path: Path) -> list[DiarizationResultSegment]: ...


class LibrosaClusteringProvider:
    """Simple offline diarization using speech windows and clustering."""

    def __init__(self, config: AppConfig) -> None:
        try:
            import librosa  # noqa: F401
            import numpy  # noqa: F401
            import sklearn.cluster  # noqa: F401
        except ImportError as exc:  # pragma: no cover - depends on local install
            raise RuntimeError(
                "Local diarization requires 'librosa' and 'scikit-learn'. "
                "Install backend dependencies before using `diarize` commands."
            ) from exc

        self.max_speakers = max(2, config.diarization_max_speakers)
        self.provider_name = "librosa-clustering"

    def diarize_file(self, audio_path: Path) -> list[DiarizationResultSegment]:
        import librosa
        import numpy as np
        from sklearn.cluster import AgglomerativeClustering

        samples, sample_rate = librosa.load(str(audio_path), sr=16000, mono=True)
        if samples.size == 0:
            return []

        frame_length = 2048
        hop_length = 512
        rms = librosa.feature.rms(y=samples, frame_length=frame_length, hop_length=hop_length)[0]
        times = librosa.frames_to_time(
            np.arange(len(rms)), sr=sample_rate, hop_length=hop_length
        )
        threshold = max(0.01, float(np.median(rms) * 1.2))
        active_indices = np.where(rms > threshold)[0]
        if active_indices.size == 0:
            return []

        mfcc = librosa.feature.mfcc(y=samples, sr=sample_rate, n_mfcc=13, hop_length=hop_length).T
        active_features = mfcc[active_indices]
        n_clusters = min(self.max_speakers, max(1, len(active_features) // 5))
        if n_clusters <= 1:
            labels = np.zeros(len(active_indices), dtype=int)
        else:
            labels = AgglomerativeClustering(n_clusters=n_clusters).fit_predict(active_features)

        segments: list[DiarizationResultSegment] = []
        current_label = int(labels[0])
        start_time = float(times[active_indices[0]])
        previous_time = float(times[active_indices[0]])

        for index, label in zip(active_indices[1:], labels[1:]):
            current_time = float(times[index])
            if int(label) != current_label or current_time - previous_time > 1.0:
                segments.append(
                    DiarizationResultSegment(
                        start_offset_seconds=int(start_time),
                        end_offset_seconds=max(int(previous_time) + 1, int(start_time) + 1),
                        speaker_label=f"Speaker {current_label + 1}",
                        confidence=0.5,
                    )
                )
                current_label = int(label)
                start_time = current_time
            previous_time = current_time

        segments.append(
            DiarizationResultSegment(
                start_offset_seconds=int(start_time),
                end_offset_seconds=max(int(previous_time) + 1, int(start_time) + 1),
                speaker_label=f"Speaker {current_label + 1}",
                confidence=0.5,
            )
        )
        return segments


def build_diarization_provider(config: AppConfig) -> DiarizationProvider:
    if config.diarization_provider == "librosa-clustering":
        return LibrosaClusteringProvider(config)
    raise RuntimeError(f"Unsupported diarization provider: {config.diarization_provider}")
