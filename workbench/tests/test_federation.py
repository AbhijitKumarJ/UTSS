import pytest
from server.db_manager import DatabaseManager

def test_federated_databases_discovered():
    mgr = DatabaseManager()
    dbs = mgr.discover_databases()
    db_ids = [d["id"] for d in dbs]
    assert "federated_recommended" in db_ids
    assert "federated_full" in db_ids

    fed_rec = mgr.get_database("federated_recommended")
    assert fed_rec is not None
    assert fed_rec["language"] == "federated"
    assert fed_rec["variant"] == "recommended"
    assert fed_rec["symbol_count"] > 7000

    fed_full = mgr.get_database("federated_full")
    assert fed_full is not None
    assert fed_full["language"] == "federated"
    assert fed_full["variant"] == "full"
    assert fed_full["symbol_count"] > 40000

def test_federated_connection_views():
    mgr = DatabaseManager()
    conn = mgr._get_federated_connection("recommended")
    cursor = conn.cursor()

    views = [
        "v_all_environments",
        "v_all_distributions",
        "v_all_containers",
        "v_all_symbols",
        "v_all_callables",
        "v_all_parameters",
        "v_all_state_members",
        "v_all_symbol_aliases",
    ]
    for view in views:
        cursor.execute(f"SELECT count(*) FROM {view};")
        row = cursor.fetchone()
        assert row is not None
        assert row[0] >= 0
    conn.close()

def test_execute_query_on_federated_db():
    mgr = DatabaseManager()
    sql = """
    SELECT language, count(*) as sym_count
    FROM v_all_symbols
    GROUP BY language
    ORDER BY language ASC;
    """
    res = mgr.execute_query("federated_recommended", sql)
    assert "error" not in res, f"Query failed: {res.get('error')}"
    assert len(res["rows"]) == 6
    languages = [r[0] for r in res["rows"]]
    assert set(languages) == {"python", "csharp", "cpp", "go", "rust", "typescript"}

def test_federated_api_endpoints():
    from fastapi.testclient import TestClient
    from main import app
    client = TestClient(app)

    # 1. Fetch comparative queries
    comp_res = client.get("/api/queries?suite=comparative")
    assert comp_res.status_code == 200
    comp_queries = comp_res.json()
    assert len(comp_queries) == 10

    # 2. Execute each comparative query on federated_recommended
    for q in comp_queries:
        exec_res = client.post("/api/execute", json={
            "db_id": "federated_recommended",
            "sql": q["sql"]
        })
        assert exec_res.status_code == 200
        data = exec_res.json()
        assert "error" not in data, f"Query {q['id']} failed via API: {data.get('error')}"
        assert data["row_count"] > 0
        assert len(data["columns"]) > 0

    # 3. Test CSV export on federated query
    export_res = client.post("/api/export?format=csv", json={
        "db_id": "federated_recommended",
        "sql": comp_queries[0]["sql"]
    })
    assert export_res.status_code == 200
    assert "text/csv" in export_res.headers.get("content-type", "")
    assert "language" in export_res.text

