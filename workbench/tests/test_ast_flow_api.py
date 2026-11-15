import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_ast_flow_valid_module():
    code = """
class Task:
    def __init__(self, title: str):
        self.title = title

def process_items(items: list[int]) -> int:
    total = 0
    for x in items:
        total = total + x
    return total
"""
    resp = client.post("/api/bridge/ast-flow", json={"python_code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert "root" in data
    assert data["root"]["node_type"] == "Module"
    assert data["node_count"] >= 5
    assert data["max_depth"] >= 2
    assert "user_type" in data["concepts_detected"]
    assert "control_flow.for_loop" in data["concepts_detected"]

    # Verify children
    children = data["root"]["children"]
    class_node = next((c for c in children if c["node_type"] == "ClassDef"), None)
    assert class_node is not None
    assert class_node["label"] == "class Task"
    assert class_node["ir_concept"] == "user_type"
    assert "csharp" in class_node["lowering_previews"]

def test_ast_flow_ir_concept_detection_collections_and_try():
    code = """
try:
    nums = [1, 2, 3]
    nums.append(4)
except Exception as e:
    pass
"""
    resp = client.post("/api/bridge/ast-flow", json={"python_code": code})
    assert resp.status_code == 200
    data = resp.json()
    assert "collection.dynamic_array" in data["concepts_detected"]
    assert "exception.try_catch" in data["concepts_detected"]

def test_ast_flow_empty_code():
    resp = client.post("/api/bridge/ast-flow", json={"python_code": "   "})
    assert resp.status_code == 400

def test_ast_flow_syntax_error():
    resp = client.post("/api/bridge/ast-flow", json={"python_code": "def broken_func(:"})
    assert resp.status_code == 422
    err = resp.json()
    assert "detail" in err
    assert "line" in err["detail"]
    assert "Syntax Error" in err["detail"]["message"]
