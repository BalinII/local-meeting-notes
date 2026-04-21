"""Application bootstrap wiring for Phase 2."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .config import AppConfig, load_config
from .core.registry import build_service_registry
from .logging_config import configure_logging
from .storage.service import StorageService


@dataclass(slots=True)
class ApplicationState:
    """Container for top-level config, logger, and service registry."""

    config: AppConfig
    logger: logging.Logger
    services: dict[str, object]


def bootstrap_application(
    env: dict[str, str] | None = None, bootstrap_db: bool = False
) -> ApplicationState:
    """Load config, configure logging, and optionally bootstrap SQLite."""

    config = load_config(env=env)
    logger = configure_logging(config)
    services = build_service_registry(config, logger=logger)

    if bootstrap_db:
        storage_service = services["storage"]
        assert isinstance(storage_service, StorageService)
        storage_service.bootstrap()

    return ApplicationState(config=config, logger=logger, services=services)
