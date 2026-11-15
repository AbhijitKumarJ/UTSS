import sqlite3
import pytest
from utss.schema import SCHEMA_SQL, init_db, EXPECTED_TABLES


def test_schema_creates_all_eleven_tables(mem_conn: sqlite3.Connection):
    init_db(mem_conn, reset=True)
    cursor = mem_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';"
    )
    tables = {row[0] for row in cursor.fetchall()}
    assert tables == EXPECTED_TABLES
    assert len(tables) == 11
    assert "callable_overloads" in tables


def test_schema_extended_columns(mem_conn: sqlite3.Connection):
    init_db(mem_conn, reset=True)

    # Check environments columns (sys_platform)
    env_cols = {row[1] for row in mem_conn.execute("PRAGMA table_info(environments);").fetchall()}
    assert "sys_platform" in env_cols

    # Check containers columns (stub_path)
    c_cols = {row[1] for row in mem_conn.execute("PRAGMA table_info(containers);").fetchall()}
    assert "stub_path" in c_cols

    # Check callables columns (has_overloads, overload_count, type_params_json)
    call_cols = {row[1] for row in mem_conn.execute("PRAGMA table_info(callables);").fetchall()}
    assert "has_overloads" in call_cols
    assert "overload_count" in call_cols
    assert "type_params_json" in call_cols

    # Check parameters columns (overload_id, type_source)
    param_cols = {row[1] for row in mem_conn.execute("PRAGMA table_info(parameters);").fetchall()}
    assert "overload_id" in param_cols
    assert "type_source" in param_cols


def test_schema_ast_coordinates(mem_conn: sqlite3.Connection):
    init_db(mem_conn, reset=True)

    # Check containers AST coordinates
    c_cols = {row[1] for row in mem_conn.execute("PRAGMA table_info(containers);").fetchall()}
    for col in ("start_line", "start_col", "end_line", "end_col"):
        assert col in c_cols, f"Missing {col} in containers"

    # Check symbols AST coordinates
    s_cols = {row[1] for row in mem_conn.execute("PRAGMA table_info(symbols);").fetchall()}
    for col in ("start_line", "start_col", "end_line", "end_col"):
        assert col in s_cols, f"Missing {col} in symbols"


def test_foreign_key_constraints(mem_conn: sqlite3.Connection):
    init_db(mem_conn, reset=True)
    # Inserting a distribution without an environment should fail foreign key check
    with pytest.raises(sqlite3.IntegrityError):
        mem_conn.execute(
            """
            INSERT INTO distributions (env_id, stratum, dist_name, dist_version)
            VALUES (9999, 1, 'orphan-dist', '1.0.0');
            """
        )


def test_init_db_reset(mem_conn: sqlite3.Connection):
    init_db(mem_conn, reset=True)
    mem_conn.execute(
        """
        INSERT INTO environments (
            language, runtime_name, language_version, version_major, version_minor,
            version_micro, platform_triplet, sys_platform, executable_path
        )
        VALUES ('python', 'CPython', '3.13.0', 3, 13, 0, 'Linux-x86_64', 'linux', '/usr/bin/python');
        """
    )
    mem_conn.commit()
    count = mem_conn.execute("SELECT COUNT(*) FROM environments;").fetchone()[0]
    assert count == 1

    # Re-init with reset=True should wipe and recreate
    init_db(mem_conn, reset=True)
    count_after = mem_conn.execute("SELECT COUNT(*) FROM environments;").fetchone()[0]
    assert count_after == 0
