import pytest
from server.db_manager import DatabaseManager
from server.query_loader import QueryLoader

def test_curriculum_queries_valid_and_executable():
    loader = QueryLoader()
    db_mgr = DatabaseManager()
    queries = loader.get_all_queries()
    assert len(queries) >= 39

    lang_db_map = {
        "python": ["python_recommended", "python_base_full"],
        "csharp": ["cs_recommended", "cs_base_full"],
        "cpp": ["cpp_recommended", "cpp_full"],
        "go": ["go_recommended", "go_full"],
        "rust": ["rust_recommended", "rust_base_full"],
        "typescript": ["ts_recommended", "ts_full"],
    }

    for lang, db_ids in lang_db_map.items():
        lang_queries = [q for q in queries if q["target_language"] == lang]
        assert len(lang_queries) >= 6, f"Expected at least 6 queries for {lang}, found {len(lang_queries)}"

        for db_id in db_ids:
            for q in lang_queries:
                res = db_mgr.execute_query(db_id, q["sql"])
                assert "error" not in res, f"Query {q['id']} failed on {db_id}: {res.get('error')}"
                assert len(res["columns"]) > 0, f"Query {q['id']} returned no columns on {db_id}"
                assert len(res["rows"]) > 0, f"Query {q['id']} returned no rows on {db_id}"

    # Test the comparative cross-language queries against federated databases
    comp_queries = [q for q in queries if q["suite"] == "comparative"]
    assert len(comp_queries) == 10, f"Expected 10 comparative queries, found {len(comp_queries)}"
    for cq in comp_queries:
        for fed_db in ["federated_recommended", "federated_full"]:
            res = db_mgr.execute_query(fed_db, cq["sql"])
            assert "error" not in res, f"Comparative Query {cq['id']} failed on {fed_db}: {res.get('error')}"
            assert len(res["columns"]) > 0, f"Query {cq['id']} returned no columns on {fed_db}"
            assert len(res["rows"]) > 0, f"Query {cq['id']} returned no rows on {fed_db}"
