"""Provider boundary for offline diarization backends."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from ..config import AppConfig


@dataclass(slots=True)
class DiarizationResultSegment:
    start_offset_seconds: float
    end_offset_seconds: float
    speaker_label: str
    confidence: float | None = None


class DiarizationProvider(Protocol):
    def diarize_file(self, audio_path: Path) -> list[DiarizationResultSegment]: ...


@dataclass(slots=True)
class DiarizationWindow:
    start_offset_seconds: float
    end_offset_seconds: float
    speaker_label: str


def _merge_adjacent_same_speaker_segments(
    segments: list[DiarizationResultSegment], max_gap_seconds: float = 0.6
) -> list[DiarizationResultSegment]:
    if not segments:
        return []

    merged = [segments[0]]
    for segment in segments[1:]:
        previous = merged[-1]
        if (
            previous.speaker_label == segment.speaker_label
            and segment.start_offset_seconds - previous.end_offset_seconds <= max_gap_seconds
        ):
            previous.end_offset_seconds = max(previous.end_offset_seconds, segment.end_offset_seconds)
            previous.confidence = None
        else:
            merged.append(segment)
    return merged


def _suppress_micro_segments(
    segments: list[DiarizationResultSegment], min_duration_seconds: float = 1.5
) -> list[DiarizationResultSegment]:
    if len(segments) < 3:
        return segments

    adjusted = list(segments)
    for index in range(1, len(adjusted) - 1):
        current = adjusted[index]
        duration = current.end_offset_seconds - current.start_offset_seconds
        previous = adjusted[index - 1]
        following = adjusted[index + 1]
        if (
            duration < min_duration_seconds
            and previous.speaker_label == following.speaker_label
            and previous.speaker_label != current.speaker_label
        ):
            previous.end_offset_seconds = following.end_offset_seconds
            following.start_offset_seconds = previous.end_offset_seconds
            current.speaker_label = previous.speaker_label
            current.start_offset_seconds = previous.start_offset_seconds
            current.end_offset_seconds = previous.end_offset_seconds

    filtered: list[DiarizationResultSegment] = []
    for segment in adjusted:
        if filtered and segment.speaker_label == filtered[-1].speaker_label:
            filtered[-1].end_offset_seconds = max(filtered[-1].end_offset_seconds, segment.end_offset_seconds)
        else:
            filtered.append(
                DiarizationResultSegment(
                    start_offset_seconds=segment.start_offset_seconds,
                    end_offset_seconds=segment.end_offset_seconds,
                    speaker_label=segment.speaker_label,
                    confidence=None,
                )
            )
    return filtered


def _finalise_segments(segments: list[DiarizationResultSegment]) -> list[DiarizationResultSegment]:
    stable = _merge_adjacent_same_speaker_segments(segments)
    stable = _suppress_micro_segments(stable)
    stable = _merge_adjacent_same_speaker_segments(stable)
    return [
        DiarizationResultSegment(
            start_offset_seconds=round(segment.start_offset_seconds, 2),
            end_offset_seconds=round(max(segment.end_offset_seconds, segment.start_offset_seconds + 0.5), 2),
            speaker_label=segment.speaker_label,
            confidence=None,
        )
        for segment in stable
    ]


class LibrosaClusteringProvider:
    """Offline diarization using speech windows, clustering, and temporal smoothing."""

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
        self.window_seconds = 1.2
        self.hop_seconds = 0.6
        self.min_segment_seconds = 1.5

    def diarize_file(self, audio_path: Path) -> list[DiarizationResultSegment]:
        import librosa
        import numpy as np
        from sklearn.cluster import AgglomerativeClustering

        samples, sample_rate = librosa.load(str(audio_path), sr=16000, mono=True)
        if samples.size == 0:
            return []

        window_size = int(sample_rate * self.window_seconds)
        hop_size = int(sample_rate * self.hop_seconds)
        if len(samples) < window_size:
            window_size = len(samples)
            hop_size = max(1, len(samples))

        windows: list[DiarizationWindow] = []
        features: list[np.ndarray] = []

        rms_global = librosa.feature.rms(y=samples, frame_length=2048, hop_length=512)[0]
        activity_threshold = max(0.015, float(np.percentile(rms_global, 60)))

        for start in range(0, max(len(samples) - window_size + 1, 1), hop_size):
            end = min(start + window_size, len(samples))
            window_samples = samples[start:end]
            if window_samples.size < sample_rate // 4:
                continue

            rms = float(np.sqrt(np.mean(np.square(window_samples))))
            if rms < activity_threshold:
                continue

            mfcc = librosa.feature.mfcc(y=window_samples, sr=sample_rate, n_mfcc=13)
            spectral_centroid = librosa.feature.spectral_centroid(y=window_samples, sr=sample_rate)
            feature = np.concatenate(
                [
                    mfcc.mean(axis=1),
                    mfcc.std(axis=1),
                    spectral_centroid.mean(axis=1),
                    np.array([rms], dtype=float),
                ]
            )
            features.append(feature)
            windows.append(
                DiarizationWindow(
                    start_offset_seconds=start / sample_rate,
                    end_offset_seconds=end / sample_rate,
                    speaker_label="Unknown",
                )
            )

        if not windows:
            return []

        feature_matrix = np.vstack(features)
        n_clusters = min(self.max_speakers, max(1, len(windows) // 8))
        if n_clusters <= 1:
            labels = np.zeros(len(windows), dtype=int)
        else:
            labels = AgglomerativeClustering(n_clusters=n_clusters).fit_predict(feature_matrix)

        segments: list[DiarizationResultSegment] = []
        current_label = int(labels[0])
        start_time = windows[0].start_offset_seconds
        previous_end = windows[0].end_offset_seconds

        for window, label in zip(windows[1:], labels[1:]):
            if int(label) != current_label or window.start_offset_seconds - previous_end > self.hop_seconds:
                segments.append(
                    DiarizationResultSegment(
                        start_offset_seconds=start_time,
                        end_offset_seconds=previous_end,
                        speaker_label=f"Speaker {current_label + 1}",
                        confidence=None,
                    )
                )
                current_label = int(label)
                start_time = window.start_offset_seconds
            previous_end = window.end_offset_seconds

        segments.append(
            DiarizationResultSegment(
                start_offset_seconds=start_time,
                end_offset_seconds=previous_end,
                speaker_label=f"Speaker {current_label + 1}",
                confidence=None,
            )
        )
        return _finalise_segments(segments)


def build_diarization_provider(config: AppConfig) -> DiarizationProvider:
    if config.diarization_provider == "librosa-clustering":
        return LibrosaClusteringProvider(config)
    raise RuntimeError(f"Unsupported diarization provider: {config.diarization_provider}")
