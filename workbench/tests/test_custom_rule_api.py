import pytest
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_custom_rule_success_low_impedance():
    payload = {
        "python_code": "items: list[int] = []\nitems.append(42)",
        "target_language": "rust",
        "rule_name": "FastVecRule",
        "base_concept_key": "collection.dynamic_array",
        "target_type_name": "FastVec",
        "type_syntax_template": "FastVec<{T}>",
        "required_import": "crate::collections::FastVec",
        "memory_model": "owned_heap",
        "nullability_model": "value_default",
        "custom_operations": {
            "append": "{receiver}.push_fast({item})"
        }
    }
    response = client.post("/api/bridge/test-custom-rule", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["rule_name"] == "FastVecRule"
    assert data["target_language"] == "rust"
    assert data["impedance_risk"] == "LOW"
    assert data["impedance_score"] >= 85
    assert "FastVec" in data["emitted_code"]
    assert "push_fast(42)" in data["emitted_code"]
    assert "crate::collections::FastVec" in data["emitted_code"]
    assert data["score_factors"]["memory_safety"] == 30
    assert data["score_factors"]["template_integrity"] == 25


def test_custom_rule_mismatched_memory_model_medium_impedance():
    payload = {
        "python_code": "items: list[int] = []\nitems.append(42)",
        "target_language": "rust",
        "rule_name": "BadMemoryModelRule",
        "base_concept_key": "collection.dynamic_array",
        "target_type_name": "GcVector",
        "type_syntax_template": "GcVector<{T}>",
        "memory_model": "ref_gc",  # Invalid in standard Rust without smart pointers
        "nullability_model": "nullable_ref",
        "custom_operations": {
            "append": "{receiver}.push({item})"
        }
    }
    response = client.post("/api/bridge/test-custom-rule", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert data["impedance_score"] < 90
    assert any("garbage collector" in d.lower() or "rc<refcell" in d.lower() for d in data["diagnostics"])


def test_custom_rule_csharp_target():
    payload = {
        "python_code": "items: list[int] = []\nitems.append(100)",
        "target_language": "csharp",
        "rule_name": "ConcurrentListRule",
        "base_concept_key": "collection.dynamic_array",
        "target_type_name": "SynchronizedCollection",
        "type_syntax_template": "SynchronizedCollection<{T}>",
        "required_import": "System.Collections.Generic",
        "memory_model": "ref_gc",
        "nullability_model": "nullable_ref",
        "custom_operations": {
            "append": "{receiver}.AddSafe({item})"
        }
    }
    response = client.post("/api/bridge/test-custom-rule", json=payload)
    assert response.status_code == 200
    data = response.json()

    assert "SynchronizedCollection" in data["emitted_code"]
    assert "AddSafe(100)" in data["emitted_code"]
    assert data["impedance_score"] >= 85


def test_custom_rule_empty_code_returns_400():
    response = client.post(
        "/api/bridge/test-custom-rule",
        json={"python_code": "   ", "target_language": "rust"},
    )
    assert response.status_code == 400
