import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_grade_lab_query_success():
    req = {
        "query_id": "py_01_strata_and_environments",
        "db_id": "python_recommended",
        "student_sql": """
            SELECT d.dist_name, d.dist_version, d.summary
            FROM distributions d
            WHERE d.stratum = 1
            ORDER BY d.dist_name ASC;
        """
    }
    resp = client.post("/api/lab/grade", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is True
    assert data["score"] == 100
    assert data["xp_earned"] == 50
    assert "🎉" in data["feedback"]
    assert data["diagnostics"]["columns_matched"] is True
    assert data["diagnostics"]["row_count_valid"] is True
    assert data["diagnostics"]["student_row_count"] >= 1

def test_grade_lab_query_missing_columns():
    req = {
        "query_id": "py_01_strata_and_environments",
        "db_id": "python_recommended",
        "student_sql": """
            SELECT d.dist_name, d.dist_version
            FROM distributions d
            WHERE d.stratum = 1;
        """
    }
    resp = client.post("/api/lab/grade", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is False
    assert data["score"] < 100
    assert data["xp_earned"] == 0
    assert "summary" in data["diagnostics"]["missing_columns"]

def test_grade_lab_query_syntax_error():
    req = {
        "query_id": "py_01_strata_and_environments",
        "db_id": "python_recommended",
        "student_sql": "SELECT FROM WHERE !!!;"
    }
    resp = client.post("/api/lab/grade", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is False
    assert data["score"] == 0
    assert "SQL Execution Error" in data["feedback"]

def test_grade_lab_query_empty_sql():
    req = {
        "query_id": "py_01_strata_and_environments",
        "db_id": "python_recommended",
        "student_sql": "   "
    }
    resp = client.post("/api/lab/grade", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is False
    assert data["score"] == 0
    assert "Empty query submitted" in data["feedback"]

def test_grade_lab_query_not_found():
    req = {
        "query_id": "nonexistent_query_xyz",
        "db_id": "python_recommended",
        "student_sql": "SELECT 1;"
    }
    resp = client.post("/api/lab/grade", json=req)
    assert resp.status_code == 404

def test_grade_lab_query_aggregate_challenge():
    req = {
        "query_id": "py_02_container_hierarchy",
        "db_id": "python_recommended",
        "student_sql": """
            SELECT container_kind, COUNT(*) AS container_count
            FROM containers
            GROUP BY container_kind
            ORDER BY container_count DESC;
        """
    }
    resp = client.post("/api/lab/grade", json=req)
    assert resp.status_code == 200
    data = resp.json()
    assert data["passed"] is True
    assert data["score"] == 100
    assert data["xp_earned"] == 100
    assert data["diagnostics"]["student_row_count"] >= 3
