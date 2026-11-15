import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_get_lab_stats():
    response = client.get("/api/lab/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_challenges" in data
    assert "total_xp_available" in data
    assert "challenges" in data
    assert data["total_challenges"] >= 10
    assert data["total_xp_available"] > 500


def test_generate_certificate_apprentice():
    response = client.post(
        "/api/lab/certificate",
        json={"student_name": "Ada Lovelace", "completed_query_ids": []},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["student_name"] == "Ada Lovelace"
    assert data["mastery_tier"] == "Syntax Apprentice"
    assert "UTSS-" in data["verification_token"]
    assert data["is_graduated"] is False


def test_generate_certificate_graduated():
    # Pick 4 valid challenge IDs
    stats_res = client.get("/api/lab/stats").json()
    qids = [c["id"] for c in stats_res["challenges"][:5]]

    response = client.post(
        "/api/lab/certificate",
        json={"student_name": "Grace Hopper", "completed_query_ids": qids},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["student_name"] == "Grace Hopper"
    assert data["total_solved"] == 5
    assert data["is_graduated"] is True
    assert data["total_xp_earned"] > 200
    assert data["completion_ratio"] > 0
