"""SQLite connection and bootstrap helpers."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from ..config import AppConfig
from .schema import SCHEMA_STATEMENTS


def create_connection(database_path: Path) -> sqlite3.Connection:
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


@contextmanager
def connection_context(database_path: Path) -> Iterator[sqlite3.Connection]:
    connection = create_connection(database_path)
    try:
        yield connection
    finally:
        connection.close()


def bootstrap_database(config: AppConfig) -> None:
    with connection_context(config.database_path) as connection:
        for statement in SCHEMA_STATEMENTS:
            connection.execute(statement)
        connection.commit()
