import sqlite3
import pytest
from pathlib import Path


@pytest.fixture
def mem_conn():
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys = ON;")
    yield conn
    conn.close()


@pytest.fixture
def temp_db_path(tmp_path: Path):
    db_file = tmp_path / "test_catalog.db"
    return db_file
