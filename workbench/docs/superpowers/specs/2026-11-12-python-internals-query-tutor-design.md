# UTSS Universal Language Analysis & Synthesis Platform — Design Document

## 1. Intent & Architectural Vision

The platform is designed as an extensible **Universal Language Analysis & Synthesis Tool** powered by the Universal Type and Symbol System (UTSS). It provides an interactive web-based environment where:

1. **Interactive Language Tutoring**: Students and researchers learn programming language internals (CPython, .NET / C#, Rust, TypeScript, Go) through progressive, annotated SQL queries against deeply indexed AST and runtime symbol databases.
2. **Multi-Database & Multi-Language Exploration**: The tool automatically discovers and manages multiple SQLite databases in `dbs/` (e.g. `python_base_full.db`, and future `csharp_full.db`, `rust_full.db`, as well as task-specific variants like `python_ai_ml.db`, `python_web.db`).
3. **Foundation for Data Science & Comparative Analytics**: The backend and frontend are architected to support future comparative cross-language analyses (e.g., cross-database joins, symbol coverage metrics, parity audits, and Pandas-driven analytical workflows).

---

## 2. Goals, Non-Goals, and Anti-Goals

### Goals
- **Multi-Database Catalog & Auto-Discovery**: Automatically scan `dbs/` for all SQLite databases. Introspect each database's `environments` and `distributions` tables to detect language (`python`, `csharp`, `rust`, etc.), runtime versions, and symbol stats.
- **Hierarchical Query Organization**: Organize queries by language, suite, and progression (e.g. `queries/python/tutoring/01_*.sql`, `queries/csharp/tutoring/...`, `queries/comparative/...`).
- **Target DB Switching in UI**: Provide a top-bar Database Selector dropdown allowing users to seamlessly switch the active DB context or filter query suites relevant to that language/variant.
- **In-Place Query Runner & Experimentation**: For each lesson, display the pedagogical rationale ("Why this query was chosen"), suggested student experiments, an editable SQL runner with keyboard shortcuts (`Ctrl+Enter`), and a formatted result table.
- **Full 8-Lesson Authoring**: The platform ships with a complete, fully authored set of 8 progressive Python internals lessons with verified SQL, rationale, and guided experiments.
- **Execution Safety & Truncation**: Read-only execution engine (`mode=ro`, `SELECT`/`WITH`/`EXPLAIN`, 5.0s timeout) with efficient single-pass 500-row preview limit and truncation flag (`truncated: true`).
- **Data Export**: Instant client-side CSV export from the results grid for fast integration with Pandas or spreadsheet analysis.

### Non-Goals
- Full web-based database editor (strictly read-only analytical access).
- Proprietary or heavyweight frontend frameworks (pure vanilla HTML5/CSS3/ES6+ SPA).
- In V1, executing cross-database joins across non-existent databases (comparative queries will be enabled as multiple `.db` files are added to `dbs/`).

### Anti-Goals
- Hardcoding queries or assuming only `python_base_full.db` will ever exist.
- Slow double-pass `COUNT(*)` query rewriting that risks query timeouts.

---

## 3. Directory Structure

```
UTSS_Analysis/
├── dbs/                                  # Discovered databases
│   ├── python_base_full.db               # CPython 3.13 standard + core
│   ├── csharp_full.db                    # (Incoming) .NET C#
│   ├── rust_full.db                      # (Incoming) Rust crates
│   └── ...                               # Language variants (e.g. python_ai_ml.db)
├── queries/                              # Hierarchical modular queries
│   ├── python/
│   │   └── tutoring/                     # Progressive Python internals curriculum (8 fully authored lessons)
│   │       ├── 01_strata_and_environments.sql
│   │       ├── 02_container_hierarchy.sql
│   │       ├── 03_keywords_and_soft_keywords.sql
│   │       ├── 04_c_vs_python_implementations.sql
│   │       ├── 05_descriptor_protocol_types.sql
│   │       ├── 06_dunder_lifecycle_and_methods.sql
│   │       ├── 07_callable_signatures_and_params.sql
│   │       └── 08_mro_and_class_hierarchies.sql
│   ├── csharp/
│   │   └── tutoring/                     # Ready for incoming C# database
│   └── comparative/
│       └── 01_schema_parity_overview.sql # Comparative multi-db structure
├── static/
│   ├── index.html                        # Universal workbench & tutor UI
│   ├── app.js                            # UI state, DB switcher, query executor, data grid, CSV exporter
│   └── style.css                         # Sleek modern layout & typography
├── server/
│   ├── __init__.py
│   ├── config.py                         # Application configuration & directory paths
│   ├── db_manager.py                     # Catalog discovery, metadata introspection & read-only executor
│   ├── query_loader.py                   # Parser & hierarchical indexer for queries/
│   ├── routes.py                         # FastAPI endpoints (DBs, queries, execute)
│   └── analysis/                         # Extension point for future Pandas / comparative pipelines
│       └── __init__.py
├── main.py                               # Application entry point (uv run main.py)
└── pyproject.toml                        # Dependencies (fastapi, uvicorn, jinja2, pyyaml)
```

---

## 4. Multi-Database Discovery & Introspection

The `DatabaseManager` scans `dbs/` at startup and upon request (`GET /api/dbs`):

1. **File Detection**: Finds all `*.db` files in `dbs/`.
2. **Metadata Introspection**:
   - Queries `environments` table for `language`, `runtime_name`, `language_version`, `platform_triplet`.
   - Counts totals from `containers`, `symbols`, `callables`.
   - Identifies distribution stratum breakdown.
3. **Database Registry Entry**:
   ```json
   {
     "id": "python_base_full",
     "filename": "python_base_full.db",
     "relative_path": "dbs/python_base_full.db",
     "language": "python",
     "runtime": "CPython",
     "version": "3.13.12",
     "variant": "base_full",
     "symbol_count": 29753,
     "container_count": 1824,
     "is_available": true
   }
   ```
4. **Fallback Handling**: If a database lacks the standard UTSS `environments` table, the manager still registers it using its filename and basic table list, ensuring forward compatibility with non-standard variants.

---

## 5. Query File Specification & Hierarchy

Each query is stored as a `.sql` file with a YAML frontmatter header:

```sql
/*---
id: py_01_strata_and_environments
title: "The Runtime Foundations: Environments & Strata"
target_language: "python"
variant_compatibility: ["*"]
suite: "tutoring"
level: "Basic"
sequence: 1
category: "Runtime & Scope"
pedagogical_rationale: >
  Python code never runs in a vacuum. Before executing a single user statement,
  CPython initializes runtime strata: Stratum 0 (Ambient builtins and keywords),
  Stratum 1 (CPython standard library modules shipped with the binary), and
  Stratum 2 (Site-packages and third-party distributions). This query shows the
  foundational boundaries of Python's execution environment.
guided_experiments:
  - "Filter by stratum = 1 to list all standard library distributions."
  - "Join with containers to see how many modules exist per stratum."
---*/
SELECT
    d.stratum,
    CASE d.stratum
        WHEN 0 THEN 'Stratum 0: Ambient Scope'
        WHEN 1 THEN 'Stratum 1: Standard Library'
        WHEN 2 THEN 'Stratum 2: Third-Party Packages'
        WHEN 3 THEN 'Stratum 3: Workspace Code'
    END AS stratum_name,
    d.dist_name,
    d.dist_version,
    d.summary
FROM distributions d
ORDER BY d.stratum ASC, d.dist_name ASC;
```

---

## 6. Initial Python Internals Curriculum (Progressive & Complete)

All 8 lessons are fully authored and tested:

1. **Lesson 1: Runtime Strata & Environments** (*Basic*): Examines ambient scope vs standard library vs site-packages.
2. **Lesson 2: Container Taxonomy & Module Hierarchy** (*Basic*): Explores packages, modules, classes, and ambient scopes.
3. **Lesson 3: Keyword Evolution & Soft Keywords** (*Basic / Intermediate*): Investigates hard keywords vs Python 3.10+ contextual keywords (`match`, `case`, `_`, `type`).
4. **Lesson 4: CPython Under the Hood: C-Extensions vs Bytecode** (*Intermediate*): Analyzes `is_c_implemented`, compiled C function pointers, and Python code flags (`co_flags`).
5. **Lesson 5: The Descriptor Protocol & Attribute Mechanics** (*Advanced*): Demystifies `wrapper_descriptor`, `method_descriptor`, `getset_descriptor`, and `property`.
6. **Lesson 6: Dunder Protocols & CPython Data Model** (*Intermediate / Advanced*): Explores lifecycle, comparison, numeric, context manager, and async protocols.
7. **Lesson 7: Parameter Passing Modes & Keyword-Only Signatures** (*Intermediate*): Inspects positional-only (`/`), keyword-only (`*`), and signature overlays.
8. **Lesson 8: Method Resolution Order (MRO) & Metaclass Dynamics** (*Advanced*): Decodes C3 linearisation arrays and custom metaclasses.

---

## 7. Backend API Specification

### `GET /`
Serves the unified single-page HTML client (`static/index.html`).

### `GET /api/dbs`
Returns all detected databases, their languages, versions, and symbol stats.

### `GET /api/queries?db_id={db_id}&language={language}`
Returns all compatible queries structured by suite and difficulty level.

### `GET /api/queries/{query_id}`
Fetches full details, rationale, hints, and SQL for a single query.

### `POST /api/execute`
Executes SQL against the specified database:
- **Request**:
  ```json
  {
    "db_id": "python_base_full",
    "sql": "SELECT stratum, dist_name FROM distributions LIMIT 10;"
  }
  ```
- **Response (Success)**:
  ```json
  {
    "columns": ["stratum", "dist_name"],
    "rows": [[0, "<ambient>"], [1, "python-stdlib"]],
    "row_count": 2,
    "truncated": false,
    "execution_time_ms": 1.84,
    "db_id": "python_base_full"
  }
  ```
- **Response (Error)**:
  ```json
  {
    "error": "near 'FROMM': syntax error",
    "db_id": "python_base_full"
  }
  ```

### Security & Safety Rules:
- All database connections open strictly with SQLite URI `?mode=ro`.
- Only `SELECT`, `WITH`, and `EXPLAIN` statements are permitted.
- Execution timeout: 5.0 seconds.
- Result truncation: Single-pass fetch with `cursor.fetchmany(501)` returning 500 rows and setting `truncated: true` if additional rows exist.

---

## 8. Frontend UI / UX Architecture

The UI is designed as an interactive, dark/light theme workstation:

1. **Top Navigation Bar**:
   - Platform Title: "UTSS Universal Language Analysis & Synthesis Workbench"
   - **Database Switcher**: Dropdown populated from `/api/dbs` (e.g. `[Python 3.13 - Base Full (29,753 symbols)]`). Shows badge indicating active language and status.
   - **Dimension / Mode Tabs**: `Tutoring & Internals` (active), `Comparative Analytics` (ready for cross-db queries).
   - "Refresh DBs" button for on-the-fly detection when new `.db` files are added to `dbs/`.

2. **Left Sidebar (Curriculum & Queries)**:
   - Search & filter bar.
   - Grouping by Suite and Level (`Basic`, `Intermediate`, `Advanced`).
   - Query cards with title, tags, and status indicator.

3. **Center / Main Workspace**:
   - **Tutor & Research Card**:
     - Lesson Title, Target Language, Level badge.
     - "Why this query was chosen" (Pedagogical / Internal mechanism explanation).
     - "Guided Experiments" (Actionable prompts for student exploration).
   - **Interactive SQL Runner**:
     - Monospace code editor with line numbers.
     - Toolbar: "Run Query" (`Ctrl+Enter`), "Reset to Default", "Copy SQL", "Download CSV".
   - **Execution Stats**:
     - Execution time (ms), rows returned, active database identifier, truncation badge.
   - **Tabular Results Grid**:
     - Clean, responsive data table with sticky headers, striped rows, and NULL indicators.
     - Client-side CSV export button for instant import into Pandas/Jupyter.
     - Exact SQLite error messages rendered with syntax tips.

---

## 9. Data Science & Comparative Analytics Path

1. **Comparative Queries**: Using SQLite `ATTACH DATABASE`, comparative queries in `queries/comparative/` can join tables across `python_base_full.db` and incoming `csharp_full.db` to produce cross-language symbol parity matrices.
2. **Pandas Integration**: The `/server/analysis/` module provides a designated foundation to ingest database tables into Pandas DataFrames, compute summary statistics, and serve chart data to the UI.
