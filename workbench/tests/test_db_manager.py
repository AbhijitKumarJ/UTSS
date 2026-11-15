import sqlite3
import pytest
from server.db_manager import DatabaseManager

def test_discover_databases():
    manager = DatabaseManager()
    dbs = manager.discover_databases()
    assert len(dbs) >= 1
    py_db = next((d for d in dbs if d["id"] == "python_base_full"), None)
    assert py_db is not None
    assert py_db["language"] == "python"
    assert py_db["symbol_count"] > 25000
    assert py_db["container_count"] > 1000
    assert py_db["is_available"] is True

def test_discover_fallback_database(tmp_path, monkeypatch):
    # Test handling of SQLite databases missing the UTSS environments table
    db_file = tmp_path / "custom_data.db"
    conn = sqlite3.connect(db_file)
    conn.execute("CREATE TABLE sample (id INT, val TEXT);")
    conn.execute("INSERT INTO sample VALUES (1, 'hello');")
    conn.commit()
    conn.close()

    from server.config import Config
    monkeypatch.setattr(Config, "DBS_DIR", tmp_path)

    manager = DatabaseManager()
    dbs = manager.discover_databases()
    assert len(dbs) == 1
    custom_db = dbs[0]
    assert custom_db["id"] == "custom_data"
    assert custom_db["language"] == "unknown"
    assert custom_db["is_available"] is True

def test_execute_query_valid():
    manager = DatabaseManager()
    res = manager.execute_query("python_base_full", "SELECT stratum, dist_name FROM distributions LIMIT 2;")
    assert "error" not in res
    assert res["columns"] == ["stratum", "dist_name"]
    assert len(res["rows"]) == 2
    assert res["row_count"] == 2
    assert res["has_more"] is False
    assert "execution_time_ms" in res
    assert res["db_id"] == "python_base_full"

def test_execute_query_truncation():
    manager = DatabaseManager()
    res = manager.execute_query("python_base_full", "SELECT symbol_id FROM symbols;", limit=10)
    assert "error" not in res
    assert len(res["rows"]) == 10
    assert res["row_count"] == 10
    assert res["has_more"] is True

def test_execute_query_security_rejection():
    manager = DatabaseManager()
    res = manager.execute_query("python_base_full", "DROP TABLE symbols;")
    assert "error" in res
    assert "Disallowed statement" in res["error"]

    res_insert = manager.execute_query("python_base_full", "INSERT INTO symbols DEFAULT VALUES;")
    assert "error" in res_insert
    assert "Disallowed statement" in res_insert["error"]

def test_execute_query_with_comment():
    manager = DatabaseManager()
    res = manager.execute_query("python_base_full", "-- note: selecting single number\nSELECT 1 AS num;")
    assert "error" not in res
    assert res["rows"][0][0] == 1

def test_execute_query_with_keywords_in_string_literals():
    manager = DatabaseManager()
    # Query searching for symbols with names like 'insert', 'update', 'replace' inside string literals
    sql = "SELECT name, symbol_kind FROM symbols WHERE name IN ('insert', 'update', 'replace') LIMIT 5;"
    res = manager.execute_query("python_base_full", sql)
    assert "error" not in res
    assert len(res["rows"]) > 0

def test_execute_query_timeout():
    manager = DatabaseManager()
    # Recursive CTE creating a slow loop to test statement timeout
    slow_sql = "WITH RECURSIVE cnt(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM cnt) SELECT count(*) FROM cnt;"
    res = manager.execute_query("python_base_full", slow_sql, timeout_seconds=1.0)
    assert "error" in res
    assert "timeout" in res["error"].lower() or "interrupted" in res["error"].lower()

def test_execute_query_sqlite_schema():
    manager = DatabaseManager()
    # Test standard database schema inspection
    res_std = manager.execute_query("python_recommended", "SELECT * FROM sqlite_schema;")
    assert "error" not in res_std
    assert len(res_std["rows"]) > 0
    assert "type" in res_std["columns"]
    assert "name" in res_std["columns"]
    assert "sql" in res_std["columns"]

    # Test federated database schema inspection (maps to temp views)
    res_fed = manager.execute_query("federated_recommended", "SELECT * FROM sqlite_schema;")
    assert "error" not in res_fed
    assert len(res_fed["rows"]) >= 8
    fed_names = [r[1] for r in res_fed["rows"]]
    assert "v_all_symbols" in fed_names
    assert "v_all_containers" in fed_names
