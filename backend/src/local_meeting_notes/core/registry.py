"""Service registry for placeholder backend modules."""

from __future__ import annotations

import logging

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
from ..session_workflow.service import SessionWorkflowService
from ..transcription_engine.service import TranscriptionEngineService


def build_service_registry(config: AppConfig, logger: logging.Logger | None = None) -> dict[str, object]:
    """Register Phase 1 placeholder services in one predictable location."""

    services = {
        "meeting_detector": MeetingDetectorService(config),
        "audio_capture": AudioCaptureService(config, logger=logger),
        "transcription_engine": TranscriptionEngineService(config, logger=logger),
        "diarization_engine": DiarizationEngineService(config, logger=logger),
        "speaker_attribution": SpeakerAttributionService(config),
        "summarizer": SummarizerService(config, logger=logger),
        "action_extractor": ActionExtractorService(config, logger=logger),
        "storage": StorageService(config, logger=logger),
        "microsoft_integration": MicrosoftIntegrationService(config),
        "export_service": ExportService(config),
    }
    services["session_workflow"] = SessionWorkflowService(
        config,
        audio_capture=services["audio_capture"],
        transcription_engine=services["transcription_engine"],
        diarization_engine=services["diarization_engine"],
        summarizer=services["summarizer"],
        action_extractor=services["action_extractor"],
        export_service=services["export_service"],
        microsoft_integration=services["microsoft_integration"],
        logger=logger,
    )
    return services
