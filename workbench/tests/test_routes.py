import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_api_dbs():
    res = client.get("/api/dbs")
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data, list)
    assert any(db["id"] == "python_base_full" for db in data)

def test_api_queries():
    res = client.get("/api/queries")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 9

def test_api_queries_filtered_by_language():
    res = client.get("/api/queries?language=python")
    assert res.status_code == 200
    data = res.json()
    assert all(q["target_language"] in {"python", "all", "*"} for q in data)

def test_api_query_by_id():
    res = client.get("/api/queries/py_01_strata_and_environments")
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "py_01_strata_and_environments"
    assert "SELECT" in data["sql"]

def test_api_query_by_id_not_found():
    res = client.get("/api/queries/non_existent_query_id")
    assert res.status_code == 404

def test_api_execute_valid():
    payload = {"db_id": "python_base_full", "sql": "SELECT 42 AS answer;"}
    res = client.post("/api/execute", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["columns"] == ["answer"]
    assert data["rows"] == [[42]]
    assert data["row_count"] == 1
    assert data["has_more"] is False

def test_api_execute_error():
    payload = {"db_id": "python_base_full", "sql": "SELECT FROM invalid syntax;"}
    res = client.post("/api/execute", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "error" in data

def test_api_export_csv():
    payload = {"db_id": "python_base_full", "sql": "SELECT 100 AS alpha, 'bravo' AS beta;"}
    res = client.post("/api/export?format=csv", json=payload)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "alpha,beta" in res.text
    assert "100,bravo" in res.text
