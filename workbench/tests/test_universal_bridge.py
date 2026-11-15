import sqlite3
from pathlib import Path
import pytest
from server.db_manager import DatabaseManager
from tools.build_universal_bridge import build_bridge_database

def test_build_universal_bridge_database(tmp_path):
    # Test building bridge database to temporary or target path
    db_file = tmp_path / "test_bridge.db"
    build_bridge_database(output_path=db_file)
    assert db_file.exists()

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Check concepts
    cursor.execute("SELECT count(*) FROM universal_concepts;")
    concept_count = cursor.fetchone()[0]
    assert concept_count >= 15

    # Check type mappings
    cursor.execute("SELECT count(*) FROM universal_type_mappings;")
    mapping_count = cursor.fetchone()[0]
    assert mapping_count >= 50

    # Check operation mappings
    cursor.execute("SELECT count(*) FROM universal_operation_mappings;")
    op_count = cursor.fetchone()[0]
    assert op_count >= 30

    # Check protocol mappings
    cursor.execute("SELECT count(*) FROM universal_protocol_mappings;")
    proto_count = cursor.fetchone()[0]
    assert proto_count >= 12

    # Check taxonomy
    cursor.execute("SELECT count(*) FROM discovered_stdlib_taxonomy;")
    tax_count = cursor.fetchone()[0]
    assert tax_count >= 30

    # Check environment metadata
    cursor.execute("SELECT language, runtime_name FROM environments LIMIT 1;")
    env = cursor.fetchone()
    assert env[0] == "universal"
    assert "Bridge" in env[1]

    conn.close()

def test_target_bridge_db_discovered_by_manager():
    # Verify main dbs/utss_universal_bridge.db is discovered
    mgr = DatabaseManager()
    bridge_db = mgr.get_database("utss_universal_bridge")
    assert bridge_db is not None
    assert bridge_db["language"] == "universal"
    assert bridge_db["is_available"] is True

    # Test executing a query on utss_universal_bridge
    query = """
    SELECT c.concept_key, m.language, m.target_qualified_name
    FROM universal_concepts c
    JOIN universal_type_mappings m ON c.concept_id = m.concept_id
    WHERE c.concept_key = 'collection.dynamic_array'
    ORDER BY m.language ASC;
    """
    res = mgr.execute_query("utss_universal_bridge", query)
    assert "error" not in res, f"Query failed: {res.get('error')}"
    assert len(res["rows"]) == 6
    languages = [r[1] for r in res["rows"]]
    assert set(languages) == {"python", "csharp", "cpp", "go", "rust", "typescript"}
