import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_comparative_analysis_recommended():
    res = client.get("/api/analysis/comparative?variant=recommended")
    assert res.status_code == 200
    data = res.json()
    assert "languages" in data
    assert len(data["languages"]) == 6
    assert set(data["languages"]) == {"python", "csharp", "cpp", "go", "rust", "typescript"}

    assert "symbol_census" in data
    assert len(data["symbol_census"]) == 6

    assert "mutability_matrix" in data
    assert len(data["mutability_matrix"]) >= 5

    assert "parameter_passing" in data
    assert len(data["parameter_passing"]) >= 5

    assert "overloading_metrics" in data
    assert len(data["overloading_metrics"]) == 6

    assert "error_handling" in data
    assert len(data["error_handling"]) == 6

    assert "pairwise_impedance" in data
    assert len(data["pairwise_impedance"]) == 6
    assert data["pairwise_impedance"]["python"]["rust"] > 0.3

def test_get_comparative_analysis_default():
    # Calling without variant should default to recommended
    res = client.get("/api/analysis/comparative")
    assert res.status_code == 200
    data = res.json()
    assert "languages" in data
    assert len(data["symbol_census"]) == 6

def test_get_analysis_report():
    res = client.get("/api/analysis/report?variant=recommended")
    assert res.status_code == 200
    content = res.text
    assert "# Empirical Transpiler Impedance & Cross-Language Parity Report" in content
    assert "## 1. Multi-Language Symbol Census" in content
    assert "## 6. Pairwise Transpiler Impedance Matrix" in content

def test_get_comparative_analysis_full():
    res = client.get("/api/analysis/comparative?variant=full")
    assert res.status_code == 200
    data = res.json()
    assert data["variant"] == "full"
    assert len(data["symbol_census"]) == 6

def test_pairwise_impedance_asymmetry():
    res = client.get("/api/analysis/comparative?variant=recommended")
    assert res.status_code == 200
    matrix = res.json()["pairwise_impedance"]
    # Python to Rust (lowering dynamic to strict borrow-check) > Rust to Python
    assert matrix["python"]["rust"] > matrix["rust"]["python"]
    # Diagonal should be 0.0
    for lang in ["python", "rust", "csharp", "go", "cpp", "typescript"]:
        assert matrix[lang][lang] == 0.0

