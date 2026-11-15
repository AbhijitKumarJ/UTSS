import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_full_user_flow_and_student_experimentation():
    # 1. Discover databases in catalog
    dbs_res = client.get("/api/dbs")
    assert dbs_res.status_code == 200
    dbs = dbs_res.json()
    assert len(dbs) > 0
    py_db = next((d for d in dbs if d["id"] == "python_base_full"), None)
    assert py_db is not None
    assert py_db["symbol_count"] > 25000

    # 2. Query list for python tutoring
    queries_res = client.get(f"/api/queries?db_id={py_db['id']}&suite=tutoring")
    assert queries_res.status_code == 200
    queries = queries_res.json()
    assert len(queries) == 8

    # 3. Student selects Lesson 1 and executes baseline SQL
    lesson_1 = queries[0]
    assert lesson_1["sequence"] == 1
    assert "strata" in lesson_1["id"]

    exec_res = client.post("/api/execute", json={
        "db_id": py_db["id"],
        "sql": lesson_1["sql"]
    })
    assert exec_res.status_code == 200
    data = exec_res.json()
    assert "error" not in data
    assert data["row_count"] > 0
    assert "stratum" in data["columns"]
    assert "stratum_name" in data["columns"]

    # 4. Student enters a typo / invalid syntax -> verify clear error reporting
    typo_res = client.post("/api/execute", json={
        "db_id": py_db["id"],
        "sql": "SELECT FROM distributions WHERE stratum = 1;"
    })
    assert typo_res.status_code == 200
    typo_data = typo_res.json()
    assert "error" in typo_data
    assert "syntax error" in typo_data["error"].lower()

    # 5. Student modifies query following Guided Experiments: count containers per stratum
    experiment_sql = """
    SELECT
        d.stratum,
        d.dist_name,
        count(c.container_id) AS total_containers
    FROM distributions d
    LEFT JOIN containers c ON c.dist_id = d.dist_id
    GROUP BY d.stratum, d.dist_name
    ORDER BY total_containers DESC;
    """
    exp_res = client.post("/api/execute", json={
        "db_id": py_db["id"],
        "sql": experiment_sql
    })
    assert exp_res.status_code == 200
    exp_data = exp_res.json()
    assert "error" not in exp_data
    assert exp_data["row_count"] > 0
    assert exp_data["columns"] == ["stratum", "dist_name", "total_containers"]
    # Python stdlib should have the most containers
    top_dist = exp_data["rows"][0]
    assert top_dist[1] == "python-stdlib"
    assert top_dist[2] > 1000

    # 6. Student downloads CSV export of their modified experiment
    export_res = client.post("/api/export?format=csv", json={
        "db_id": py_db["id"],
        "sql": experiment_sql
    })
    assert export_res.status_code == 200
    assert "python-stdlib" in export_res.text
    assert "total_containers" in export_res.text

    # 7. Student switches to Comparative Analytics suite
    comp_res = client.get(f"/api/queries?db_id={py_db['id']}&suite=comparative")
    assert comp_res.status_code == 200
    comp_queries = comp_res.json()
    assert len(comp_queries) >= 1

    comp_exec = client.post("/api/execute", json={
        "db_id": py_db["id"],
        "sql": comp_queries[0]["sql"]
    })
    assert comp_exec.status_code == 200
    comp_data = comp_exec.json()
    assert "error" not in comp_data
    assert comp_data["row_count"] > 0
