from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

import pytest


@pytest.fixture
def local_tmp_dir() -> Path:
    root = Path("backend/data/tmp/test-runs").resolve()
    root.mkdir(parents=True, exist_ok=True)
    path = root / uuid4().hex
    path.mkdir(parents=True, exist_ok=True)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
