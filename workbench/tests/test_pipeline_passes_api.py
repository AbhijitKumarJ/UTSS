import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_pipeline_passes_all_4_stages_success():
    code = """
class Storage:
    def __init__(self, capacity: int):
        self.capacity = capacity

items: list[int] = []
items.append(10)
items.append(20)
"""
    resp = client.post("/api/bridge/pipeline-passes", json={"python_code": code, "target_language": "rust"})
    assert resp.status_code == 200
    data = resp.json()
    assert "passes" in data
    assert len(data["passes"]) == 4

    p1, p2, p3, p4 = data["passes"]
    assert p1["pass_id"] == "pass_1_frontend"
    assert "ast_dump" in p1["artifacts"]
    assert p1["metrics"]["total_ast_nodes"] >= 5

    assert p2["pass_id"] == "pass_2_semantic"
    assert any(s["identifier"] == "Storage" for s in p2["artifacts"]["symbol_table"])
    assert any(s["identifier"] == "items" for s in p2["artifacts"]["symbol_table"])

    assert p3["pass_id"] == "pass_3_ir_memory"
    assert p3["metrics"]["target_memory_model"] == "owned_heap_or_stack"
    assert "alloc::vec::Vec" in p3["artifacts"]["required_imports"]

    assert p4["pass_id"] == "pass_4_codegen"
    assert "pub struct Storage" in p4["artifacts"]["emitted_code"]
    assert len(p4["artifacts"]["provenance_records"]) >= 1

def test_pipeline_passes_target_language_switching():
    code = """
items: list[int] = []
items.append(42)
"""
    # Test Rust: requires alloc::vec::Vec and let mut
    resp_rust = client.post("/api/bridge/pipeline-passes", json={"python_code": code, "target_language": "rust"})
    assert resp_rust.status_code == 200
    p3_rust = resp_rust.json()["passes"][2]
    assert "alloc::vec::Vec" in p3_rust["artifacts"]["required_imports"]
    assert p3_rust["artifacts"]["mutability_map"]["items"]["mutated"] is True

    # Test C#: requires System.Collections.Generic
    resp_cs = client.post("/api/bridge/pipeline-passes", json={"python_code": code, "target_language": "csharp"})
    assert resp_cs.status_code == 200
    p3_cs = resp_cs.json()["passes"][2]
    assert "System.Collections.Generic" in p3_cs["artifacts"]["required_imports"]

def test_pipeline_passes_syntax_error():
    resp = client.post("/api/bridge/pipeline-passes", json={"python_code": "def oops(:"})
    assert resp.status_code == 422
    assert "Syntax Error" in resp.json()["detail"]["message"]

def test_pipeline_passes_empty_code():
    resp = client.post("/api/bridge/pipeline-passes", json={"python_code": "  "})
    assert resp.status_code == 400
