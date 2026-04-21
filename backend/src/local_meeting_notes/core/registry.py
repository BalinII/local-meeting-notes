"""Service registry for placeholder backend modules."""

from __future__ import annotations

from ..action_extractor.service import ActionExtractorService
from ..audio_capture.service import AudioCaptureService
from ..config import AppConfig
from ..diarization_engine.service import DiarizationEngineService
from ..export_service.service import ExportService
from ..meeting_detector.service import MeetingDetectorService
from ..microsoft_integration.service import MicrosoftIntegrationService
from ..speaker_attribution.service import SpeakerAttributionService
from ..storage.service import StorageService
from ..summarizer.service import SummarizerService
from ..transcription_engine.service import TranscriptionEngineService


def build_service_registry(config: AppConfig) -> dict[str, object]:
    """Register Phase 1 placeholder services in one predictable location."""

    return {
        "meeting_detector": MeetingDetectorService(config),
        "audio_capture": AudioCaptureService(config),
        "transcription_engine": TranscriptionEngineService(config),
        "diarization_engine": DiarizationEngineService(config),
        "speaker_attribution": SpeakerAttributionService(config),
        "summarizer": SummarizerService(config),
        "action_extractor": ActionExtractorService(config),
        "storage": StorageService(config),
        "microsoft_integration": MicrosoftIntegrationService(config),
        "export_service": ExportService(config),
    }
