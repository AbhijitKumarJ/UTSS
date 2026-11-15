import csv
import io
import json
import sqlite3
from pathlib import Path
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from server.config import Config
from server.db_manager import DatabaseManager
from server.query_loader import QueryLoader

router = APIRouter()
db_manager = DatabaseManager()
query_loader = QueryLoader()

class ExecuteRequest(BaseModel):
    db_id: str
    sql: str
    limit: int | None = None

class ExportRequest(BaseModel):
    db_id: str
    sql: str
    limit: int | None = 5000

class TranslateRequest(BaseModel):
    source_language: str
    target_language: str
    concept_key: str
    canonical_op: str | None = None
    receiver: str = "items"
    args: list[str] = []

class TranspileSnippetRequest(BaseModel):
    python_code: str
    target_languages: list[str] | None = None

class GradeLabRequest(BaseModel):
    query_id: str
    db_id: str
    student_sql: str

class AstFlowRequest(BaseModel):
    python_code: str

class PipelinePassesRequest(BaseModel):
    python_code: str
    target_language: str = "rust"

class ProjectExportRequest(BaseModel):
    python_code: str
    target: str = "rust"
    project_name: str = "rosetta_transpiled"

class CustomRuleTestRequest(BaseModel):
    python_code: str
    target_language: str = "rust"
    rule_name: str = "CustomRule"
    base_concept_key: str = "collection.dynamic_array"
    target_type_name: str = "CustomType"
    type_syntax_template: str = "CustomType<{T}>"
    required_import: str | None = None
    memory_model: str = "owned_heap"
    nullability_model: str = "value_default"
    custom_operations: dict[str, str] = {}

class CertificateRequest(BaseModel):
    student_name: str = "Anonymous Scholar"
    completed_query_ids: list[str] = []


@router.get("/")
def serve_index():
    """Serves the main application single-page workbench."""
    index_file = Config.STATIC_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return JSONResponse({"status": "UTSS Platform API active. Static frontend not yet compiled."})

@router.get("/api/dbs")
def list_databases():
    """Lists all discovered SQLite databases and their environment metadata."""
    return db_manager.discover_databases()

@router.get("/api/queries")
def list_queries(
    db_id: str | None = None,
    language: str | None = None,
    suite: str | None = None
):
    """Returns all compatible queries, optionally filtered by language, database, or suite."""
    target_lang = language
    if db_id and not target_lang:
        db_info = db_manager.get_database(db_id)
        if db_info and db_info.get("language") != "unknown":
            target_lang = db_info["language"]

    all_queries = query_loader.get_all_queries()
    filtered = []
    for q in all_queries:
        if suite and q["suite"] != suite:
            continue
        if suite == "comparative":
            filtered.append(q)
            continue
        if target_lang and q["target_language"] not in {"all", "*", target_lang}:
            continue
        filtered.append(q)
    return filtered

@router.get("/api/queries/tree")
def get_queries_tree(
    language: str | None = None,
    suite: str | None = None
):
    """Returns curriculum queries organized hierarchically by suite and level."""
    return query_loader.get_queries_tree(language=language, suite=suite)

@router.get("/api/queries/{query_id}")
def get_query(query_id: str):
    """Fetches full metadata and baseline SQL for a specific query."""
    q = query_loader.get_query_by_id(query_id)
    if not q:
        raise HTTPException(status_code=404, detail=f"Query '{query_id}' not found.")
    return q

@router.post("/api/execute")
def execute_query(req: ExecuteRequest):
    """Executes a user SQL query safely in read-only mode."""
    return db_manager.execute_query(db_id=req.db_id, sql=req.sql, limit=req.limit)

@router.post("/api/export")
def export_query_post(
    req: ExportRequest,
    format: str = Query("csv", pattern="^(csv|json)$")
):
    """Streams export data for user-submitted SQL in CSV or JSON format."""
    res = db_manager.execute_query(db_id=req.db_id, sql=req.sql, limit=req.limit)
    if "error" in res:
        raise HTTPException(status_code=400, detail=res["error"])

    columns = res.get("columns", [])
    rows = res.get("rows", [])

    if format == "json":
        json_str = json.dumps({"columns": columns, "rows": rows}, indent=2)
        return StreamingResponse(
            io.StringIO(json_str),
            media_type="application/json",
            headers={"Content-Disposition": f"attachment; filename=export_{req.db_id}.json"}
        )

    # Format CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(columns)
    for row in rows:
        writer.writerow(row)
    output.seek(0)

    return StreamingResponse(
        output,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=export_{req.db_id}.csv"}
    )

@router.post("/api/lab/grade")
def grade_lab_query(req: GradeLabRequest):
    """Grades a student-submitted SQL query against challenge benchmarks and criteria."""
    q = query_loader.get_query_by_id(req.query_id)
    if not q:
        raise HTTPException(status_code=404, detail=f"Query '{req.query_id}' not found.")

    lab = q.get("lab_challenge")
    if not lab:
        raise HTTPException(status_code=400, detail=f"Query '{req.query_id}' does not have a lab challenge.")

    if not req.student_sql or not req.student_sql.strip():
        return {
            "passed": False,
            "score": 0,
            "xp_earned": 0,
            "feedback": "Empty query submitted. Please write a SQL query to solve the challenge.",
            "diagnostics": {
                "execution_success": False,
                "columns_matched": False,
                "missing_columns": lab.get("expected_columns", []),
                "row_count_valid": False,
                "student_row_count": 0,
                "expected_min_rows": lab.get("min_rows", 1),
                "error_detail": "No SQL provided."
            }
        }

    student_res = db_manager.execute_query(db_id=req.db_id, sql=req.student_sql, limit=1000)
    if "error" in student_res:
        return {
            "passed": False,
            "score": 0,
            "xp_earned": 0,
            "feedback": f"SQL Execution Error: {student_res['error']}",
            "diagnostics": {
                "execution_success": False,
                "columns_matched": False,
                "missing_columns": lab.get("expected_columns", []),
                "row_count_valid": False,
                "student_row_count": 0,
                "expected_min_rows": lab.get("min_rows", 1),
                "error_detail": student_res["error"]
            }
        }

    raw_student_cols = student_res.get("columns", [])
    student_cols_norm = [c.lower() for c in raw_student_cols]
    expected_cols = lab.get("expected_columns", [])
    missing_cols = [c for c in expected_cols if c.lower() not in student_cols_norm]
    columns_matched = len(missing_cols) == 0

    student_rows = student_res.get("rows", [])
    student_row_count = len(student_rows)
    min_rows = lab.get("min_rows", 1)
    max_rows = lab.get("max_rows")

    row_count_valid = student_row_count >= min_rows
    if max_rows is not None and student_row_count > max_rows:
        row_count_valid = False

    # Check solution SQL reference if available
    ref_matched = True
    ref_row_count = None
    solution_sql = lab.get("solution_sql")
    if solution_sql:
        ref_res = db_manager.execute_query(db_id=req.db_id, sql=solution_sql, limit=1000)
        if "error" not in ref_res:
            ref_row_count = len(ref_res.get("rows", []))
            if ref_row_count > 0:
                if student_row_count == 0 or abs(student_row_count - ref_row_count) > max(1, int(0.2 * ref_row_count)):
                    ref_matched = False

    passed = columns_matched and row_count_valid and ref_matched
    xp_reward = lab.get("xp_reward", 100)

    if passed:
        score = 100
        xp_earned = xp_reward
        feedback = f"🎉 Challenge Solved! Your query produced {student_row_count} rows with all required columns: {', '.join(raw_student_cols)}."
    else:
        xp_earned = 0
        reasons = []
        if not columns_matched:
            reasons.append(f"Missing required columns: {', '.join(missing_cols)} (got: {', '.join(raw_student_cols)})")
        if not row_count_valid:
            if student_row_count < min_rows:
                reasons.append(f"Result returned {student_row_count} rows, but at least {min_rows} was expected.")
            elif max_rows is not None and student_row_count > max_rows:
                reasons.append(f"Result returned {student_row_count} rows, exceeding max limit of {max_rows}.")
        if not ref_matched and ref_row_count is not None:
            reasons.append(f"Expected ~{ref_row_count} rows matching the reference solution, but got {student_row_count}.")

        score = 50 if columns_matched else (30 if student_row_count > 0 else 0)
        feedback = "Almost there! " + "; ".join(reasons)

    return {
        "passed": passed,
        "score": score,
        "xp_earned": xp_earned,
        "feedback": feedback,
        "diagnostics": {
            "execution_success": True,
            "columns_matched": columns_matched,
            "missing_columns": missing_cols,
            "row_count_valid": row_count_valid,
            "student_row_count": student_row_count,
            "expected_min_rows": min_rows,
            "expected_row_count": ref_row_count,
            "reference_matched": ref_matched
        }
    }

@router.get("/api/lab/stats")
def get_lab_stats():
    """Returns curriculum stats, total challenges, and XP rewards."""
    all_queries = query_loader.get_all_queries()
    challenges = []
    total_xp = 0
    for q in all_queries:
        lab = q.get("lab_challenge")
        if lab:
            xp = lab.get("xp_reward", 50)
            total_xp += xp
            challenges.append({
                "id": q["id"],
                "title": q["title"],
                "suite": q["suite"],
                "level": q["level"],
                "category": q.get("category", "General"),
                "xp_reward": xp,
                "objective": lab.get("objective", "")
            })
    return {
        "total_challenges": len(challenges),
        "total_xp_available": total_xp,
        "challenges": challenges
    }

@router.post("/api/lab/certificate")
def generate_certificate(req: CertificateRequest):
    """Generates a cryptographic Certificate of Mastery in Compilers & Language Impedance."""
    import hashlib
    from datetime import date

    all_queries = query_loader.get_all_queries()
    challenge_map = {q["id"]: q.get("lab_challenge") for q in all_queries if q.get("lab_challenge")}
    
    total_challenges = len(challenge_map)
    total_available_xp = sum(c.get("xp_reward", 50) for c in challenge_map.values())
    
    valid_solved = [qid for qid in req.completed_query_ids if qid in challenge_map]
    total_xp_earned = sum(challenge_map[qid].get("xp_reward", 50) for qid in valid_solved)
    
    solved_ratio = len(valid_solved) / max(total_challenges, 1)
    
    if solved_ratio >= 0.75:
        tier = "Principal Compiler Fellow"
    elif solved_ratio >= 0.5:
        tier = "Senior Language Architect"
    elif solved_ratio >= 0.25:
        tier = "Systems Compiler Engineer"
    else:
        tier = "Syntax Apprentice"

    payload = f"{req.student_name}|{date.today()}|{len(valid_solved)}|{total_xp_earned}|UTSS_ACCREDITED"
    sig = hashlib.sha256(payload.encode()).hexdigest()[:24].upper()

    return {
        "student_name": req.student_name.strip() or "Anonymous Scholar",
        "issue_date": date.today().strftime("%B %d, %Y"),
        "total_solved": len(valid_solved),
        "total_challenges": total_challenges,
        "total_xp_earned": total_xp_earned,
        "total_xp_available": total_available_xp,
        "mastery_tier": tier,
        "completion_ratio": round(solved_ratio * 100, 1),
        "verification_token": f"UTSS-{sig[:4]}-{sig[4:8]}-{sig[8:12]}-{sig[12:16]}",
        "badges": [
            {"title": "AST Ingestion & Parsing", "icon": "🌳"},
            {"title": "Crosswalk & Rosetta IR", "icon": "🔄"},
            {"title": "Memory Models & Mutability", "icon": "🛡️"},
            {"title": "Empirical Impedance Verification", "icon": "⚡"}
        ],
        "is_graduated": len(valid_solved) >= 3,
    }

@router.get("/api/bridge/concepts")
def list_bridge_concepts(category: str | None = None):
    """Returns canonical universal concepts available in the bridge database."""
    bridge_db = Config.DBS_DIR / "utss_universal_bridge.db"
    if not bridge_db.exists():
        raise HTTPException(status_code=404, detail="Universal bridge database not found.")
    conn = sqlite3.connect(f"file:{bridge_db.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = "SELECT concept_id, concept_key, category, type_arity, description FROM universal_concepts"
    params = []
    if category:
        query += " WHERE category = ?"
        params.append(category)
    query += " ORDER BY category ASC, concept_key ASC;"
    cursor.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

@router.get("/api/bridge/lookup")
def lookup_bridge_concept(concept_key: str = Query(...)):
    """Looks up 6-language type, operation, and protocol mappings for a given canonical concept."""
    bridge_db = Config.DBS_DIR / "utss_universal_bridge.db"
    if not bridge_db.exists():
        raise HTTPException(status_code=404, detail="Universal bridge database not found.")
    conn = sqlite3.connect(f"file:{bridge_db.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM universal_concepts WHERE concept_key = ? LIMIT 1;", (concept_key,))
    concept_row = cursor.fetchone()
    if not concept_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Concept '{concept_key}' not found.")

    concept = dict(concept_row)
    cid = concept["concept_id"]

    cursor.execute("SELECT * FROM universal_type_mappings WHERE concept_id = ? ORDER BY language ASC;", (cid,))
    type_mappings = {r["language"]: dict(r) for r in cursor.fetchall()}

    cursor.execute("SELECT * FROM universal_operation_mappings WHERE concept_id = ? ORDER BY canonical_op ASC, language ASC;", (cid,))
    op_mappings = {}
    for r in cursor.fetchall():
        d = dict(r)
        op = d["canonical_op"]
        lang = d["language"]
        if op not in op_mappings:
            op_mappings[op] = {}
        op_mappings[op][lang] = d

    cursor.execute("SELECT * FROM universal_protocol_mappings WHERE concept_id = ? ORDER BY language ASC;", (cid,))
    proto_mappings = {r["language"]: dict(r) for r in cursor.fetchall()}

    conn.close()
    return {
        "concept": concept,
        "type_mappings": type_mappings,
        "operation_mappings": op_mappings,
        "protocol_mappings": proto_mappings
    }

@router.post("/api/bridge/translate")
def translate_operation(req: TranslateRequest):
    """Translates a high-level canonical operation or type between source and target languages."""
    bridge_db = Config.DBS_DIR / "utss_universal_bridge.db"
    if not bridge_db.exists():
        raise HTTPException(status_code=404, detail="Universal bridge database not found.")
    conn = sqlite3.connect(f"file:{bridge_db.resolve()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("SELECT concept_id FROM universal_concepts WHERE concept_key = ? LIMIT 1;", (req.concept_key,))
    c_row = cursor.fetchone()
    if not c_row:
        conn.close()
        raise HTTPException(status_code=404, detail=f"Concept '{req.concept_key}' not found.")
    cid = c_row[0]

    cursor.execute("SELECT * FROM universal_type_mappings WHERE concept_id = ? AND language = ? LIMIT 1;", (cid, req.target_language))
    tgt_type_row = cursor.fetchone()
    tgt_type = dict(tgt_type_row) if tgt_type_row else {}

    source_op = None
    target_op = None
    if req.canonical_op:
        cursor.execute(
            "SELECT * FROM universal_operation_mappings WHERE concept_id = ? AND canonical_op = ? AND language = ? LIMIT 1;",
            (cid, req.canonical_op, req.source_language)
        )
        s_row = cursor.fetchone()
        source_op = dict(s_row) if s_row else None

        cursor.execute(
            "SELECT * FROM universal_operation_mappings WHERE concept_id = ? AND canonical_op = ? AND language = ? LIMIT 1;",
            (cid, req.canonical_op, req.target_language)
        )
        t_row = cursor.fetchone()
        target_op = dict(t_row) if t_row else None

    conn.close()

    receiver = req.receiver if req.receiver else "items"

    # Handle multi-argument operations (e.g. key and value for hash maps)
    key_val = req.args[0] if len(req.args) > 0 and req.args[0] else "key"
    val_val = req.args[1] if len(req.args) > 1 and req.args[1] else (req.args[0] if len(req.args) > 0 and req.args[0] else "val")
    item_val = req.args[0] if len(req.args) > 0 and req.args[0] else "item"

    def format_op_template(template: str) -> str:
        s = template.replace("{receiver}", receiver)
        s = s.replace("{item}", item_val)
        s = s.replace("{key}", key_val)
        s = s.replace("{val}", val_val)
        s = s.replace("{out}", "val")
        return s

    if source_op:
        source_expr = format_op_template(source_op["call_syntax_template"])
    elif req.canonical_op:
        source_expr = f"{receiver}.{req.canonical_op}({', '.join(req.args)})"
    else:
        source_expr = receiver

    if target_op:
        target_expr = format_op_template(target_op["call_syntax_template"])
        pass_kind = target_op["receiver_pass_kind"]
    elif req.canonical_op:
        target_expr = f"{receiver}.{req.canonical_op}({', '.join(req.args)})"
        pass_kind = "val"
    else:
        target_expr = receiver
        pass_kind = "val"

    notes = []
    if req.target_language == "rust" and pass_kind == "mut_ref":
        notes.append(f"Requires exclusive mutable borrow (&mut {receiver}). In Rust, ensure '{receiver}' is declared with 'let mut'.")
    elif req.target_language == "go" and pass_kind == "free_fn":
        sym = target_op["target_symbol_name"] if target_op and "target_symbol_name" in target_op else "append"
        notes.append(f"Go implements this operation as a built-in universe function ({sym}), re-binding the slice header.")
    elif req.target_language == "cpp" and pass_kind == "mut_ref":
        notes.append(f"C++ modifies {receiver} in-place via lvalue reference.")
    elif req.target_language == "csharp" and pass_kind == "mut_ref":
        sym = target_op["target_symbol_name"] if target_op and "target_symbol_name" in target_op else "Add"
        notes.append(f"C# executes instance method {sym} modifying internal buffer.")
    elif req.target_language == "python" and pass_kind == "mut_ref":
        notes.append(f"Python mutates {receiver} in-place via reference semantics.")
    elif req.target_language == "typescript" and pass_kind == "mut_ref":
        notes.append(f"TypeScript mutates {receiver} in-place via reference semantics.")
    else:
        notes.append(f"Lowered using {pass_kind} semantics.")

    return {
        "source_language": req.source_language,
        "target_language": req.target_language,
        "concept_key": req.concept_key,
        "canonical_op": req.canonical_op,
        "source_expression": source_expr,
        "target_expression": target_expr,
        "target_type": tgt_type.get("type_syntax_template", ""),
        "required_import": tgt_type.get("required_import"),
        "memory_model": tgt_type.get("memory_model", "value_default"),
        "receiver_pass_kind": pass_kind,
        "impedance_note": " ".join(notes),
    }

@router.post("/api/bridge/transpile")
def transpile_snippet(req: TranspileSnippetRequest):
    """Transpiles a multi-statement Python code snippet into C#, Rust, TypeScript, C++, and Go using utss_universal_bridge.db."""
    bridge_db = Config.DBS_DIR / "utss_universal_bridge.db"
    if not bridge_db.exists():
        raise HTTPException(status_code=404, detail="Universal bridge database not found.")

    from server.analysis.bridge_transpiler import BridgeCatalogRepository, BridgeTranspiler, TARGET_LANGUAGES
    from dataclasses import asdict

    repo = BridgeCatalogRepository(bridge_db)
    transpiler = BridgeTranspiler(repo)
    try:
        targets = {}
        target_langs = req.target_languages if req.target_languages else list(TARGET_LANGUAGES)
        for lang in target_langs:
            lang_key = lang.lower().strip()
            if lang_key in TARGET_LANGUAGES:
                out = transpiler.transpile_module(req.python_code, lang_key)
                targets[lang_key] = asdict(out)
        return {
            "source_python": req.python_code,
            "targets": targets
        }
    except SyntaxError as exc:
        raise HTTPException(status_code=400, detail=f"Python SyntaxError: {exc}")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transpilation failed: {exc}")
    finally:
        repo.close()

@router.post("/api/bridge/ast-flow")
def get_ast_flow(req: AstFlowRequest):
    """Builds a structured visual AST flow graph and per-node lowering previews from Python source code."""
    if not req.python_code or not req.python_code.strip():
        raise HTTPException(status_code=400, detail="Python code cannot be empty.")
    try:
        from server.analysis.ast_flow import build_ast_flow
        return build_ast_flow(req.python_code)
    except SyntaxError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"Syntax Error: {e.msg}",
                "line": e.lineno,
                "offset": e.offset,
                "text": e.text
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/bridge/pipeline-passes")
def get_pipeline_passes(req: PipelinePassesRequest):
    """Executes and records the 4 classical compilation passes (Frontend AST, Semantic Symbol Binding, IR Memory Model, and Codegen)."""
    if not req.python_code or not req.python_code.strip():
        raise HTTPException(status_code=400, detail="Python code cannot be empty.")
    try:
        from server.analysis.pipeline_passes import run_compiler_pipeline
        return run_compiler_pipeline(req.python_code, req.target_language)
    except SyntaxError as e:
        raise HTTPException(
            status_code=422,
            detail={
                "message": f"Syntax Error: {e.msg}",
                "line": e.lineno,
                "offset": e.offset,
                "text": e.text
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/bridge/export-project")
def export_project_archive(req: ProjectExportRequest):
    """Generates and downloads a complete runnable project archive (.zip) for the chosen target or all targets."""
    if not req.python_code or not req.python_code.strip():
        raise HTTPException(status_code=400, detail="Python code cannot be empty.")
    try:
        from server.analysis.project_exporter import build_project_zip
        zip_bytes = build_project_zip(req.python_code, req.target, req.project_name)
        filename = f"{req.project_name}_{req.target}.zip"
        return StreamingResponse(
            io.BytesIO(zip_bytes),
            media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'}
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/bridge/stdlib-coverage")
def get_stdlib_coverage_endpoint():
    """Returns empirical 6-language standard library taxonomy coverage and unmapped candidate constructs."""
    try:
        from server.analysis.stdlib_taxonomist import get_stdlib_coverage_report
        return get_stdlib_coverage_report()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/bridge/crawl-stdlib")
def crawl_stdlib_endpoint():
    """Triggers an autonomous harvesting pass across all 6 language databases."""
    try:
        from server.analysis.stdlib_taxonomist import harvest_stdlib_taxonomy
        return harvest_stdlib_taxonomy()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/bridge/test-custom-rule")
def test_custom_rule_endpoint(req: CustomRuleTestRequest):
    """Executes empirical impedance testing on a user-defined custom lowering rule."""
    if not req.python_code or not req.python_code.strip():
        raise HTTPException(status_code=400, detail="Python code cannot be empty.")
    try:
        from server.analysis.custom_rule_tester import test_custom_rule
        rule_dict = {
            "rule_name": req.rule_name,
            "target_language": req.target_language,
            "base_concept_key": req.base_concept_key,
            "target_type_name": req.target_type_name,
            "type_syntax_template": req.type_syntax_template,
            "required_import": req.required_import,
            "memory_model": req.memory_model,
            "nullability_model": req.nullability_model,
            "custom_operations": req.custom_operations,
        }
        return test_custom_rule(req.python_code, req.target_language, rule_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/graph/containers")
def get_container_graph_endpoint(db_id: str):
    """Returns container containment hierarchy as nodes and edges."""
    try:
        return db_manager.get_container_graph(db_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/graph/inheritance")
def get_inheritance_graph_endpoint(db_id: str):
    """Returns type inheritance and interface implementation DAG."""
    try:
        return db_manager.get_inheritance_graph(db_id)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/graph/concept-cluster")
def get_concept_cluster_endpoint(concept_key: str):
    """Returns star graph linking a universal concept to its 6-language implementations."""
    try:
        return db_manager.get_concept_cluster(concept_key)
    except (FileNotFoundError, ValueError) as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------------------------------------------------------
# Empirical Data Science & Transpiler Impedance Analysis Endpoints
# ----------------------------------------------------------------------------
_analysis_cache: dict[str, dict] = {}

@router.get("/api/analysis/comparative")
def get_comparative_analysis(variant: str = "recommended"):
    """Returns multi-language empirical metrics, parity matrix, and pairwise impedance data."""
    v = variant.lower().strip()
    if v not in ("recommended", "full"):
        v = "recommended"
    if v not in _analysis_cache:
        from tools.utss_comparative_analysis import run_comparative_analysis
        try:
            _analysis_cache[v] = run_comparative_analysis(variant=v)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to execute comparative analysis: {e}")
    return _analysis_cache[v]


@router.get("/api/analysis/report")
def get_analysis_report(variant: str = "recommended"):
    """Generates and returns the complete Markdown report for the empirical analysis."""
    from fastapi.responses import PlainTextResponse
    from tools.utss_comparative_analysis import generate_markdown_report

    v = variant.lower().strip()
    if v not in ("recommended", "full"):
        v = "recommended"
    data = get_comparative_analysis(variant=v)
    report_md = generate_markdown_report(data)
    return PlainTextResponse(
        content=report_md,
        media_type="text/markdown",
        headers={"Content-Disposition": f'attachment; filename="utss_comparative_report_{v}.md"'}
    )


@router.post("/api/bindgen/csharp")
def generate_csharp_bindings(
    db_name: str = "cs_recommended.db",
    target_namespace: str = "Utss.Generated"
):
    """Generates strongly-typed C# wrapper classes and invoker stubs (*.g.cs) from any catalog database."""
    from tools.utss_csharp_bindgen import CSharpBindgen
    
    db_path = Config.DBS_DIR / db_name
    if not db_path.exists():
        # Fallback check
        found = list(Config.DBS_DIR.glob(f"*{db_name}*"))
        if found:
            db_path = found[0]
        else:
            raise HTTPException(status_code=404, detail=f"Database '{db_name}' not found in {Config.DBS_DIR}")

    try:
        bindgen = CSharpBindgen(db_path)
        code = bindgen.generate(target_namespace=target_namespace)
        return {
            "database": db_path.name,
            "target_namespace": target_namespace,
            "line_count": len(code.splitlines()),
            "code": code,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bindgen error: {e}")


