import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_container_graph_valid():
    res = client.get("/api/graph/containers?db_id=python_recommended")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0
    # Check node structure
    first_node = data["nodes"][0]
    assert "id" in first_node
    assert "name" in first_node
    assert "qualified_name" in first_node
    assert "kind" in first_node
    assert "symbol_count" in first_node

def test_get_inheritance_graph_cs():
    res = client.get("/api/graph/inheritance?db_id=cs_recommended")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data
    assert len(data["nodes"]) > 0
    # There should be interface or class inheritance edges in C#
    edge_types = {e.get("relation_kind") for e in data["edges"]}
    assert "implements" in edge_types or "extends" in edge_types

def test_get_inheritance_graph_python():
    res = client.get("/api/graph/inheritance?db_id=python_recommended")
    assert res.status_code == 200
    data = res.json()
    assert "nodes" in data
    assert "edges" in data
    # Check that Exception hierarchy exists in python
    node_names = {n["name"] for n in data["nodes"]}
    assert any("Exception" in name or "Error" in name for name in node_names)

def test_get_concept_cluster():
    res = client.get("/api/graph/concept-cluster?concept_key=collection.dynamic_array")
    assert res.status_code == 200
    data = res.json()
    assert data["concept"] == "collection.dynamic_array"
    assert "nodes" in data
    assert "edges" in data
    # Should have target languages represented
    langs = {n.get("language") for n in data["nodes"] if "language" in n}
    assert "python" in langs
    assert "rust" in langs

def test_get_graph_nonexistent_db():
    res = client.get("/api/graph/containers?db_id=nonexistent_db")
    assert res.status_code == 404
