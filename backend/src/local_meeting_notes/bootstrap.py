"""Application bootstrap wiring for Phase 1."""

from dataclasses import dataclass

from .config import AppConfig, load_config
from .core.registry import build_service_registry


@dataclass(slots=True)
class ApplicationState:
    """Container for top-level config and service registry."""

    config: AppConfig
    services: dict[str, object]


def bootstrap_application() -> ApplicationState:
    """Load config and register placeholder services."""

    config = load_config()
    services = build_service_registry(config)
    return ApplicationState(config=config, services=services)
