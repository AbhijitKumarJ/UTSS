# UTSS Phase 1 PoC Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the complete UTSS (Universal Type & Symbol System) Phase 1 PoC as a modular Python package indexing Strata 0, 1, 2, and 3 into a Dual-Layer SQLite database with diagnostic queries and CLI.

**Architecture:** A clean modular architecture in `src/utss/` separating SQLite DDL (`schema.py`), runtime classification and hardened signature extraction (`introspect.py`), central orchestration engine (`cataloger.py`), static workspace AST parsing (`workspace.py`), diagnostic reporting (`queries.py`), and CLI interface (`cli.py`), verified with pytest.

**Tech Stack:** Python 3.13, SQLite3 (WAL mode), `ast`, `inspect`, `importlib`, `pkgutil`, `pytest`, `uv`.

**Spec:** `Ideation/1.md`, `docs/PRD.md`

## Global Constraints

- Zero external third-party runtime dependencies (only standard library modules: `sqlite3`, `ast`, `inspect`, `importlib`, `sys`, `platform`, `pathlib`, etc.).
- Dev dependencies: `pytest` only.
- Strict isolation for Stratum 3: Must parse workspace source via `ast` without executing module code.
- Resilient introspection: Python 3.13 default parameter symbolic evaluation errors (`AttributeError`, `NameError`) must be caught and gracefully degraded.
- SQLite WAL mode and foreign key integrity enabled.

## Review Focus

1. **Python 3.13 C-Extension Signature Errors**: Default parameter AST evaluation in `_curses`, `select`, etc., must not abort harvesting.
2. **Namespace Pollution Rejection**: Imported foreign modules inside a module (e.g. `shutil.os`) must be recorded as `symbol_aliases` and never duplicated into `symbols`.
3. **Differential Pure Builtins**: `site`-injected builtins (`help`, `exit`, `quit`, etc.) must have `provenance = 'site_injected'` while pure builtins have `provenance = 'defined_here'`.
4. **Stratum 3 Static Safety**: Syntactically invalid files or side-effect-heavy workspace scripts must not crash the harvester or execute arbitrary code.
5. **Class Inheritance & MRO Integrity**: Class hierarchies, base classes, and MRO tuples must be serialized as valid JSON arrays in `py_container_facets`.

---

### Task 1: Package Scaffolding & Dual-Layer SQLite Schema

**Files:**
- Modify: `pyproject.toml`
- Create: `src/utss/__init__.py`
- Create: `src/utss/schema.py`
- Test: `tests/conftest.py`, `tests/test_schema.py`

- [ ] Write failing test in `tests/test_schema.py` testing database creation, foreign key constraints, table existence (10 tables), and indexes.
- [ ] Run `uv run pytest tests/test_schema.py` to confirm failure.
- [ ] Implement `pyproject.toml` configuration (`[build-system]`, package configuration, scripts entry point).
- [ ] Implement `src/utss/__init__.py` and `src/utss/schema.py` with `SCHEMA_SQL` and `init_db(conn, reset=False)`.
- [ ] Run `uv run pytest tests/test_schema.py` to confirm pass.
- [ ] Git commit Task 1.

---

### Task 2: Hardened Runtime Introspection & Classification

**Files:**
- Create: `src/utss/introspect.py`
- Test: `tests/test_introspect.py`

- [ ] Write failing test in `tests/test_introspect.py` for `classify_identifier_visibility`, `safe_repr`, `compute_file_sha256`, `get_pure_builtins_without_site`, and `extract_callable_signature` (including resilience to `AttributeError`/`NameError` on C builtins).
- [ ] Run `uv run pytest tests/test_introspect.py` to confirm failure.
- [ ] Implement `src/utss/introspect.py` with DUNDER categories, visibility classification, safe string representation, and hardened signature extraction with fallback chain.
- [ ] Run `uv run pytest tests/test_introspect.py` to confirm pass.
- [ ] Git commit Task 2.

---

### Task 3: Core Cataloger & Stratum 0 (Ambient Scope)

**Files:**
- Create: `src/utss/cataloger.py`
- Test: `tests/test_stratum_0.py`

- [ ] Write failing test in `tests/test_stratum_0.py` checking Stratum 0 registration (`<ambient>` container, keywords, soft keywords, pure vs site builtins, implicit module dunders).
- [ ] Run `uv run pytest tests/test_stratum_0.py` to confirm failure.
- [ ] Implement `PythonSpectrumCataloger` in `src/utss/cataloger.py` with `register_environment`, `register_distribution`, `register_container`, and `harvest_stratum_0_ambient`.
- [ ] Run `uv run pytest tests/test_stratum_0.py` to confirm pass.
- [ ] Git commit Task 3.

---

### Task 4: Stratum 1 (Stdlib) & Stratum 2 (Third-Party) Harvesting

**Files:**
- Modify: `src/utss/cataloger.py`
- Test: `tests/test_stratum_1.py`, `tests/test_stratum_2.py`

- [ ] Write failing test in `tests/test_stratum_1.py` for stdlib module discovery, public facade vs C-accelerator re-exports (`io` $\to$ `_io`, `json` $\to$ `_json`), and class hierarchy harvesting.
- [ ] Write failing test in `tests/test_stratum_2.py` for third-party package discovery via `importlib.metadata`.
- [ ] Run `uv run pytest tests/test_stratum_1.py tests/test_stratum_2.py` to confirm failure.
- [ ] Implement `discover_stdlib_modules`, `harvest_stratum_1_stdlib`, `harvest_stratum_2_third_party`, `harvest_module_by_name`, and member inspection in `src/utss/cataloger.py`.
- [ ] Run `uv run pytest tests/test_stratum_1.py tests/test_stratum_2.py` to confirm pass.
- [ ] Git commit Task 4.

---

### Task 5: Stratum 3 (Workspace Source AST Harvester)

**Files:**
- Create: `src/utss/workspace.py`
- Modify: `src/utss/cataloger.py`
- Test: `tests/test_stratum_3.py`

- [ ] Write failing test in `tests/test_stratum_3.py` for scanning a directory of Python files, parsing AST without execution, and cataloging modules, classes, functions, arguments, type annotations, and module-level variables.
- [ ] Run `uv run pytest tests/test_stratum_3.py` to confirm failure.
- [ ] Implement `WorkspaceASTHarvester` in `src/utss/workspace.py` using `ast.parse` and connect `harvest_stratum_3_workspace` to `PythonSpectrumCataloger`.
- [ ] Run `uv run pytest tests/test_stratum_3.py` to confirm pass.
- [ ] Git commit Task 5.

---

### Task 6: Diagnostic Queries, Reporting & CLI Interface

**Files:**
- Create: `src/utss/queries.py`
- Create: `src/utss/cli.py`
- Modify: `main.py`
- Test: `tests/test_cli.py`

- [ ] Write failing test in `tests/test_cli.py` testing CLI invocation (`harvest`, `report`, `query`).
- [ ] Run `uv run pytest tests/test_cli.py` to confirm failure.
- [ ] Implement `src/utss/queries.py` (summary report generator, verification queries A/B/C from `1.md`, interactive symbol lookup).
- [ ] Implement `src/utss/cli.py` with `argparse` subcommands.
- [ ] Wire `main.py` to call `utss.cli.main()`.
- [ ] Run `uv run pytest tests/test_cli.py` to confirm pass.
- [ ] Run full test suite: `uv run pytest`.
- [ ] Run end-to-end harvest test against active environment.
- [ ] Git commit Task 6.
