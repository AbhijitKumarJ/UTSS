import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_get_bridge_concepts():
    res = client.get("/api/bridge/concepts")
    assert res.status_code == 200
    concepts = res.json()
    assert len(concepts) >= 15
    keys = [c["concept_key"] for c in concepts]
    assert "collection.dynamic_array" in keys
    assert "collection.hash_map" in keys
    assert "protocol.iteration" in keys

def test_lookup_bridge_concept():
    res = client.get("/api/bridge/lookup?concept_key=collection.dynamic_array")
    assert res.status_code == 200
    data = res.json()
    assert "concept" in data
    assert data["concept"]["concept_key"] == "collection.dynamic_array"

    assert "type_mappings" in data
    types = data["type_mappings"]
    assert "python" in types
    assert "rust" in types
    assert "csharp" in types
    assert "go" in types
    assert types["python"]["type_syntax_template"] == "list[{T}]"
    assert types["rust"]["type_syntax_template"] == "Vec<{T}>"
    assert types["rust"]["memory_model"] == "owned_heap"

    assert "operation_mappings" in data
    ops = data["operation_mappings"]
    assert "append" in ops
    assert "len" in ops
    assert ops["append"]["rust"]["target_symbol_name"] == "push"
    assert ops["append"]["rust"]["call_syntax_template"] == "{receiver}.push({item})"
    assert ops["append"]["go"]["target_symbol_name"] == "append"
    assert ops["append"]["go"]["call_syntax_template"] == "{receiver} = append({receiver}, {item})"

def test_translate_operation_python_to_rust():
    payload = {
        "source_language": "python",
        "target_language": "rust",
        "concept_key": "collection.dynamic_array",
        "canonical_op": "append",
        "receiver": "users",
        "args": ["new_user"]
    }
    res = client.post("/api/bridge/translate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["source_expression"] == "users.append(new_user)"
    assert data["target_expression"] == "users.push(new_user)"
    assert data["target_type"] == "Vec<{T}>"
    assert data["memory_model"] == "owned_heap"
    assert data["receiver_pass_kind"] == "mut_ref"
    assert "mut" in data["impedance_note"]

def test_translate_operation_python_to_go():
    payload = {
        "source_language": "python",
        "target_language": "go",
        "concept_key": "collection.dynamic_array",
        "canonical_op": "append",
        "receiver": "items",
        "args": ["val"]
    }
    res = client.post("/api/bridge/translate", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["source_expression"] == "items.append(val)"
    assert data["target_expression"] == "items = append(items, val)"
    assert data["receiver_pass_kind"] == "free_fn"

def test_lookup_nonexistent_concept_returns_404():
    res = client.get("/api/bridge/lookup?concept_key=nonexistent.concept")
    assert res.status_code == 404

def test_string_and_set_crosswalk_translations():
    # 1. Test collection.hash_set lookup has newly populated operations
    res = client.get("/api/bridge/lookup?concept_key=collection.hash_set")
    assert res.status_code == 200
    data = res.json()
    assert "add" in data["operation_mappings"]
    assert "remove" in data["operation_mappings"]
    assert "contains" in data["operation_mappings"]

    # 2. Test translate hash_set add from Python to Rust
    payload = {
        "source_language": "python",
        "target_language": "rust",
        "concept_key": "collection.hash_set",
        "canonical_op": "add",
        "receiver": "seen",
        "args": ["token"]
    }
    t_res = client.post("/api/bridge/translate", json=payload)
    assert t_res.status_code == 200
    assert t_res.json()["source_expression"] == "seen.add(token)"
    assert t_res.json()["target_expression"] == "seen.insert(token)"

    # 3. Test string_utf8 to_lowercase from Python to Go
    str_payload = {
        "source_language": "python",
        "target_language": "go",
        "concept_key": "primitive.string_utf8",
        "canonical_op": "to_lowercase",
        "receiver": "name",
        "args": []
    }
    s_res = client.post("/api/bridge/translate", json=str_payload)
    assert s_res.status_code == 200
    assert s_res.json()["source_expression"] == "name.lower()"
    assert s_res.json()["target_expression"] == "strings.ToLower(name)"

