# UTSS Universal Language Analysis & Synthesis Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a high-performance, extensible Universal Language Analysis and Synthesis web platform with an interactive Python internals query tutor, multi-database auto-discovery, live in-place SQL runner, and comparative data science readiness.

**Architecture:** A FastAPI backend provides database auto-discovery for any SQLite database in `dbs/` (introspecting language, runtime, and symbol counts) and serves an indexed tree of YAML-annotated `.sql` curriculum files. A read-only SQLite execution engine executes user queries with a 5.0-second timeout and 500-row preview limit (`has_more: true`), while a responsive vanilla HTML5/CSS3/ES6+ SPA delivers a master-detail curriculum explorer, tutor rationale cards, SQL editor (`Ctrl+Enter`), and exportable data grid.

**Tech Stack:** Python 3.12/3.13, FastAPI, Uvicorn, PyYAML, SQLite3 (read-only URI mode), Vanilla HTML5/CSS3/JavaScript, pytest.

**Spec:** `docs/superpowers/specs/2026-11-12-python-internals-query-tutor-design.md`

## Global Constraints

- Database URI must always be opened read-only: `file:{path}?mode=ro&immutable=1` (fallback to `file:{path}?mode=ro`).
- SQL security filter must strictly allow only `SELECT`, `WITH`, and `EXPLAIN` statements; reject any DDL/DML (`ATTACH`, `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`).
- Query execution timeout is strictly enforced at 5.0 seconds.
- Result preview limit is 500 rows; single-pass fetch (`cursor.fetchmany(501)`) sets `has_more: true` without slow `COUNT(*)` rewriting.
- Zero external build dependencies (no npm, webpack, or vite); frontend is served directly as static files.

## Review Focus

1. **Non-standard or foreign SQLite databases in `dbs/`**: A database without the standard UTSS `environments` table must still register cleanly as `language: "unknown"` and allow arbitrary read-only queries without crashing `/api/dbs`.
2. **Infinite loop / recursive CTE queries**: A student executing `WITH RECURSIVE cnt(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM cnt) SELECT * FROM cnt;` must hit the 5.0-second timeout and return an execution timeout error rather than hanging the server process.
3. **Multiline comments and whitespace in SQL**: A student query with leading comments or blank lines (e.g. `-- inspect symbols\nSELECT ...`) must be recognized as valid `SELECT` statements by the security validator.
4. **Client-side special characters and NULLs**: Result tables must cleanly render `null`, `None`, empty strings, and special characters (e.g. angle brackets `<ambient>`, unicode symbols) without breaking HTML rendering or crashing the CSV generator.
5. **Database switching with modified SQL**: Switching the active database in the UI dropdown must preserve the current query text in the editor, allowing immediate cross-database comparative execution with a single click.

---

### Task 1: Project Scaffolding & Configuration

**Files:**
- Modify: `pyproject.toml`
- Create: `server/__init__.py`
- Create: `server/config.py`
- Create: `server/analysis/__init__.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `server.config.Config` (attributes: `BASE_DIR`, `DBS_DIR`, `QUERIES_DIR`, `STATIC_DIR`, `QUERY_TIMEOUT_SECONDS`, `DEFAULT_PREVIEW_LIMIT`).

- [ ] **Step 1: Write the failing test for configuration**

```python
# tests/test_config.py
from pathlib import Path
from server.config import Config

def test_config_paths():
    assert Config.BASE_DIR.exists()
    assert Config.DBS_DIR.name == "dbs"
    assert Config.QUERIES_DIR.name == "queries"
    assert Config.STATIC_DIR.name == "static"
    assert Config.QUERY_TIMEOUT_SECONDS == 5.0
    assert Config.DEFAULT_PREVIEW_LIMIT == 500
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_config.py -v`
Expected: FAIL with ModuleNotFoundError: No module named 'server'

- [ ] **Step 3: Implement `pyproject.toml` and `server/config.py`**

Update `pyproject.toml` dependencies with `fastapi>=0.115.0`, `uvicorn>=0.30.0`, `pyyaml>=6.0.2`, `pytest>=8.0.0`.
Create `server/__init__.py`, `server/analysis/__init__.py`, and `server/config.py`:
```python
from pathlib import Path

class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent
    DBS_DIR = BASE_DIR / "dbs"
    QUERIES_DIR = BASE_DIR / "queries"
    STATIC_DIR = BASE_DIR / "static"
    QUERY_TIMEOUT_SECONDS = 5.0
    DEFAULT_PREVIEW_LIMIT = 500
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml server/ tests/test_config.py
git commit -m "feat(core): setup project dependencies and configuration paths"
```

---

### Task 2: Database Catalog Discovery & Read-Only Execution Engine

**Files:**
- Create: `server/db_manager.py`
- Test: `tests/test_db_manager.py`

**Interfaces:**
- Consumes: `server.config.Config`
- Produces:
  - `DatabaseManager.discover_databases() -> list[dict]`
  - `DatabaseManager.get_database(db_id: str) -> dict | None`
  - `DatabaseManager.execute_query(db_id: str, sql: str, limit: int = 500) -> dict`

- [ ] **Step 1: Write the failing tests for DatabaseManager**

```python
# tests/test_db_manager.py
import pytest
from server.db_manager import DatabaseManager

def test_discover_databases():
    manager = DatabaseManager()
    dbs = manager.discover_databases()
    assert len(dbs) >= 1
    py_db = next(d for d in dbs if d["id"] == "python_base_full")
    assert py_db["language"] == "python"
    assert py_db["symbol_count"] > 25000
    assert py_db["container_count"] > 1000

def test_execute_query_valid():
    manager = DatabaseManager()
    res = manager.execute_query("python_base_full", "SELECT stratum, dist_name FROM distributions LIMIT 2;")
    assert "error" not in res
    assert res["columns"] == ["stratum", "dist_name"]
    assert len(res["rows"]) == 2
    assert res["row_count"] == 2
    assert res["has_more"] is False
    assert "execution_time_ms" in res

def test_execute_query_truncation():
    manager = DatabaseManager()
    res = manager.execute_query("python_base_full", "SELECT symbol_id FROM symbols;", limit=10)
    assert len(res["rows"]) == 10
    assert res["has_more"] is True

def test_execute_query_security_rejection():
    manager = DatabaseManager()
    res = manager.execute_query("python_base_full", "DROP TABLE symbols;")
    assert "error" in res
    assert "Disallowed statement" in res["error"]

def test_execute_query_with_comment():
    manager = DatabaseManager()
    res = manager.execute_query("python_base_full", "-- note\nSELECT 1 AS num;")
    assert "error" not in res
    assert res["rows"][0][0] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_db_manager.py -v`
Expected: FAIL with ModuleNotFoundError: No module named 'server.db_manager'

- [ ] **Step 3: Implement `DatabaseManager` in `server/db_manager.py`**

Implement:
- `discover_databases()`: Scans `Config.DBS_DIR` for `*.db`. Opens each with `sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)`. Queries `environments` table for `language`, `runtime_name`, `language_version`, `platform_triplet`. Queries `SELECT count(*) FROM containers`, `symbols`, `callables`. Graceful fallback on missing table.
- SQL statement safety validator: Strips comments and leading whitespace; asserts query starts with `SELECT`, `WITH`, or `EXPLAIN`. Blocks DDL/DML.
- `execute_query(db_id, sql, limit)`: Runs query within timeout handler. Measures duration. Fetches `limit + 1` rows via `cursor.fetchmany(limit + 1)`. If `len(rows) > limit`, sets `has_more = True` and truncates to `limit`. Returns structured dictionary with column names, rows, `has_more`, and duration.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_db_manager.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/db_manager.py tests/test_db_manager.py
git commit -m "feat(db): implement multi-database discovery and safe read-only executor"
```

---

### Task 3: Query Loader & Frontmatter Parser

**Files:**
- Create: `server/query_loader.py`
- Test: `tests/test_query_loader.py`

**Interfaces:**
- Consumes: `server.config.Config`
- Produces:
  - `QueryLoader.load_query_file(file_path: Path) -> dict`
  - `QueryLoader.get_all_queries() -> list[dict]`
  - `QueryLoader.get_query_by_id(query_id: str) -> dict | None`
  - `QueryLoader.get_queries_tree(language: str | None, suite: str | None) -> dict`

- [ ] **Step 1: Write the failing tests for QueryLoader**

```python
# tests/test_query_loader.py
import pytest
from pathlib import Path
from server.query_loader import QueryLoader

def test_parse_frontmatter_and_sql(tmp_path):
    sql_file = tmp_path / "test_query.sql"
    sql_file.write_text("""/*---
id: test_01
title: "Test Lesson"
target_language: "python"
suite: "tutoring"
level: "Basic"
sequence: 1
category: "Basics"
pedagogical_rationale: "Explains basic test."
guided_experiments:
  - "Experiment 1"
---*/
SELECT 1 AS test;
""")
    loader = QueryLoader(queries_dir=tmp_path)
    q = loader.load_query_file(sql_file)
    assert q["id"] == "test_01"
    assert q["title"] == "Test Lesson"
    assert q["target_language"] == "python"
    assert q["level"] == "Basic"
    assert q["sequence"] == 1
    assert q["pedagogical_rationale"] == "Explains basic test."
    assert q["guided_experiments"] == ["Experiment 1"]
    assert q["sql"].strip() == "SELECT 1 AS test;"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_query_loader.py -v`
Expected: FAIL with ModuleNotFoundError: No module named 'server.query_loader'

- [ ] **Step 3: Implement `QueryLoader` in `server/query_loader.py`**

Implement:
- Frontmatter parser supporting `/*--- ... ---*/` block extraction using `pyyaml`.
- File scanner discovering all `*.sql` files under `Config.QUERIES_DIR`.
- Query hierarchy indexer: organizes queries by `target_language`, `suite`, and sorted by `sequence` and `level`.
- Retrieval methods: `get_all_queries()`, `get_query_by_id(id)`, `get_queries_tree(language, suite)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_query_loader.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/query_loader.py tests/test_query_loader.py
git commit -m "feat(queries): implement query loader and frontmatter metadata parser"
```

---

### Task 4: Complete Curriculum Authoring (8 Python Lessons + Comparative Query)

**Files:**
- Create: `queries/python/tutoring/01_strata_and_environments.sql`
- Create: `queries/python/tutoring/02_container_hierarchy.sql`
- Create: `queries/python/tutoring/03_keywords_and_soft_keywords.sql`
- Create: `queries/python/tutoring/04_c_vs_python_implementations.sql`
- Create: `queries/python/tutoring/05_descriptor_protocol_types.sql`
- Create: `queries/python/tutoring/06_dunder_lifecycle_and_methods.sql`
- Create: `queries/python/tutoring/07_callable_signatures_and_params.sql`
- Create: `queries/python/tutoring/08_mro_and_class_hierarchies.sql`
- Create: `queries/comparative/cross_language_summary.sql`
- Test: `tests/test_curriculum.py`

**Interfaces:**
- Consumes: `DatabaseManager`, `QueryLoader`
- Produces: 8 production-grade Python internals SQL lessons + 1 cross-language summary query.

- [ ] **Step 1: Write curriculum validation test**

```python
# tests/test_curriculum.py
import pytest
from server.db_manager import DatabaseManager
from server.query_loader import QueryLoader

def test_curriculum_queries_valid_and_executable():
    loader = QueryLoader()
    db_mgr = DatabaseManager()
    queries = loader.get_all_queries()
    assert len(queries) >= 9

    py_queries = [q for q in queries if q["target_language"] == "python"]
    assert len(py_queries) == 8

    # Ensure all 8 execute cleanly against python_base_full.db
    for q in py_queries:
        res = db_mgr.execute_query("python_base_full", q["sql"])
        assert "error" not in res, f"Query {q['id']} failed: {res.get('error')}"
        assert len(res["columns"]) > 0
        assert len(res["rows"]) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_curriculum.py -v`
Expected: FAIL with "assert len(queries) >= 9" (0 found)

- [ ] **Step 3: Author the 8 Python Internals lessons & Comparative query**

Create each `.sql` file with full YAML frontmatter, pedagogical rationale ("Why this query was chosen"), guided experiment suggestions, and tuned SQL:
1. `01_strata_and_environments.sql`: Distributions, strata (0 ambient, 1 stdlib, 2 third-party), platform triplets.
2. `02_container_hierarchy.sql`: Module tree, packages, classes, parent-child container links.
3. `03_keywords_and_soft_keywords.sql`: Hard keywords vs 3.10+ contextual soft keywords (`match`, `case`, `_`, `type`).
4. `04_c_vs_python_implementations.sql`: `is_c_implemented` vs pure Python bytecode (`co_flags`).
5. `05_descriptor_protocol_types.sql`: Descriptor taxonomy (`wrapper_descriptor`, `method_descriptor`, `getset_descriptor`, `property`).
6. `06_dunder_lifecycle_and_methods.sql`: Dunder categorisation (lifecycle, comparison, numeric, context_manager, async).
7. `07_callable_signatures_and_params.sql`: Positional-only (`/`), keyword-only (`*`), type annotations and defaults.
8. `08_mro_and_class_hierarchies.sql`: `mro_json`, `base_classes_json`, and metaclass specialization.
9. `cross_language_summary.sql`: Stratum and symbol counts ready for cross-language inspection.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_curriculum.py -v`
Expected: PASS (all 9 queries execute and return rows)

- [ ] **Step 5: Commit**

```bash
git add queries/ tests/test_curriculum.py
git commit -m "feat(curriculum): author complete 8-lesson Python internals progression and comparative query"
```

---

### Task 5: FastAPI REST API & Streaming Export Endpoints

**Files:**
- Create: `server/routes.py`
- Modify: `main.py`
- Test: `tests/test_routes.py`

**Interfaces:**
- Consumes: `DatabaseManager`, `QueryLoader`, `Config`
- Produces:
  - `GET /` -> serves `static/index.html`
  - `GET /api/dbs` -> list of database registries
  - `GET /api/queries` -> hierarchical or filtered query list
  - `GET /api/queries/{query_id}` -> single query details
  - `POST /api/execute` -> query runner endpoint
  - `POST /api/export` -> streaming CSV/JSON export endpoint
  - `main.app` -> FastAPI instance runnable via `uvicorn main:app` or `uv run main.py`

- [ ] **Step 1: Write integration tests for API routes**

```python
# tests/test_routes.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_api_dbs():
    res = client.get("/api/dbs")
    assert res.status_code == 200
    data = res.json()
    assert any(db["id"] == "python_base_full" for db in data)

def test_api_queries():
    res = client.get("/api/queries")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 9

def test_api_execute_valid():
    payload = {"db_id": "python_base_full", "sql": "SELECT 42 AS answer;"}
    res = client.post("/api/execute", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["rows"] == [[42]]

def test_api_execute_error():
    payload = {"db_id": "python_base_full", "sql": "SELECT FROM invalid;"}
    res = client.post("/api/execute", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "error" in data

def test_api_export_csv():
    payload = {"db_id": "python_base_full", "sql": "SELECT 1 AS colA, 2 AS colB;"}
    res = client.post("/api/export?format=csv", json=payload)
    assert res.status_code == 200
    assert "text/csv" in res.headers["content-type"]
    assert "colA,colB" in res.text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_routes.py -v`
Expected: FAIL with ImportError / 404

- [ ] **Step 3: Implement `server/routes.py` and `main.py`**

- Create `server/routes.py` registering all endpoints and mounting `StaticFiles(directory=Config.STATIC_DIR)`.
- Implement `POST /api/export` using `StreamingResponse` with an iterator-based CSV generator.
- Update `main.py` to instantiate FastAPI, include the router, and run `uvicorn.run(app, host="0.0.0.0", port=8000)` under `if __name__ == "__main__":`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_routes.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/routes.py main.py tests/test_routes.py
git commit -m "feat(api): implement REST API endpoints, streaming CSV exporter, and app entrypoint"
```

---

### Task 6: Frontend Workbench SPA

**Files:**
- Create: `static/index.html`
- Create: `static/style.css`
- Create: `static/app.js`
- Test: `tests/test_frontend.py`

**Interfaces:**
- Consumes: REST endpoints (`/api/dbs`, `/api/queries`, `/api/execute`, `/api/export`)
- Produces: Polished interactive web application with:
  - Top navigation bar: title, database dropdown with live symbol stats, tab switchers (Tutoring vs Comparative).
  - Left sidebar: search filter, category/level pills (`Basic`, `Intermediate`, `Advanced`), query cards.
  - Tutor card: Title, level badge, language badge, "Why this query was chosen" pedagogical callout, "Guided Experiments".
  - Monospace SQL editor: line numbers, "Run Query (`Ctrl+Enter`)", "Reset to Default", "Copy SQL".
  - Execution stats: runtime duration (ms), row count, `has_more` warning badge.
  - Interactive table: sticky headers, striped rows, distinct NULL representation, "Download CSV" local export button.
  - Syntax error callout banner with clear diagnostic messages.

- [ ] **Step 1: Write static file presence and contract test**

```python
# tests/test_frontend.py
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_static_index_serves_html():
    res = client.get("/")
    assert res.status_code == 200
    assert "<!DOCTYPE html>" in res.text
    assert "UTSS Universal Language Analysis" in res.text

def test_static_assets_serve():
    css = client.get("/static/style.css")
    assert css.status_code == 200
    js = client.get("/static/app.js")
    assert js.status_code == 200
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_frontend.py -v`
Expected: FAIL with 404

- [ ] **Step 3: Implement `static/index.html`, `static/style.css`, and `static/app.js`**

- `index.html`: Responsive layout with semantic header, main grid (sidebar + workspace), modal/toast support.
- `style.css`: Clean dark theme aesthetic (slate/indigo palette), high contrast typography for SQL code, responsive scrolling tables.
- `app.js`: State management (active DB, active query, unmodified default SQL, active suite), keyboard event listeners (`Ctrl+Enter` / `Cmd+Enter`), fetch calls, DOM table rendering with XSS-safe textContent, and client-side CSV Blob generator.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_frontend.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add static/ tests/test_frontend.py
git commit -m "feat(ui): implement interactive single-page workbench and SQL runner"
```

---

### Task 7: End-to-End Verification & Documentation

**Files:**
- Create: `tests/test_e2e.py`
- Modify: `README.md`

- [ ] **Step 1: Write comprehensive End-to-End test**

```python
# tests/test_e2e.py
import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_full_user_flow():
    # 1. Discover databases
    dbs = client.get("/api/dbs").json()
    assert len(dbs) > 0
    active_db = dbs[0]["id"]

    # 2. Get queries for that language
    queries = client.get(f"/api/queries?db_id={active_db}").json()
    assert len(queries) >= 8

    # 3. Pick the first query and execute its default SQL
    first_q = queries[0]
    exec_res = client.post("/api/execute", json={"db_id": active_db, "sql": first_q["sql"]}).json()
    assert "error" not in exec_res
    assert exec_res["row_count"] > 0

    # 4. Modify SQL with an intentional error and verify friendly error handling
    err_res = client.post("/api/execute", json={"db_id": active_db, "sql": "SELECT non_existent_col FROM distributions;"}).json()
    assert "error" in err_res

    # 5. Execute a modified student experiment and verify result
    exp_res = client.post("/api/execute", json={"db_id": active_db, "sql": "SELECT count(*) AS total_dists FROM distributions;"}).json()
    assert exp_res["rows"][0][0] > 0
```

- [ ] **Step 2: Run all unit and integration tests**

Run: `pytest -v`
Expected: All tests PASS

- [ ] **Step 3: Update `README.md`**

Document:
- Project overview & UTSS universal language analysis vision.
- Quick start instructions (`uv run main.py`).
- Adding new SQLite databases into `dbs/` (e.g. `csharp_full.db`, `python_ai_ml.db`).
- Authoring new `.sql` lessons in `queries/`.

- [ ] **Step 4: Commit**

```bash
git add tests/test_e2e.py README.md
git commit -m "docs: complete end-to-end verification and documentation"
```
