# UTSS Phase 2 (Static .pyi / Typeshed Overlay) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 2 (`Ideation/2.md`): Static `.pyi` Typeshed AST Overlay pass to enrich opaque C-builtins, store polymorphic `@overload` families, restore erased generic variable types, and evaluate static `sys.version_info` / `sys.platform` guards without code execution.

**Architecture:** Extend SQLite schema with `callable_overloads` and overload-aware parameter relations. Implement `src/utss/overlay.py` with `StaticPyiOverlayCataloger`, supporting embedded demo stubs (`builtins`, `sys`, `os`, `json`), custom typeshed directories, and auto-discovery. Update `src/utss/cataloger.py`, `src/utss/queries.py`, and `src/utss/cli.py` to expose overlay commands and diagnostic queries.

**Tech Stack:** Python 3.13, SQLite3 (WAL mode), `ast`, `inspect`, `pytest`, `uv`.

**Spec:** `Ideation/2.md`, `docs/PRD.md`

## Global Constraints

- Zero external runtime dependencies (pure Python standard library: `ast`, `sqlite3`, `inspect`, `sys`, `platform`, `pathlib`).
- Pure AST analysis for `.pyi` files: Never import or execute `.pyi` files.
- Resilient condition evaluation: Static guards (`if sys.version_info >= (3, 12):`) must be evaluated purely against `sys.version_info` and `sys.platform`.
- Full relational integrity for `@overload` signatures: `callable_overloads` must reference `callables(symbol_id)` and parameter sets must track their `overload_id`.

## Review Focus

1. **`@overload` Parameter Isolation**: Parameters belonging to an `@overload` must have `overload_id` set, while primary callable parameters have `overload_id IS NULL`.
2. **Generic Type Restoration**: Module variables like `sys.argv` must update `declared_type_expr = 'list[str]'` and update `provenance = 'pyi_enriched'`.
3. **Static Guard Pruning**: Statements inside `if sys.version_info < (3, 0):` must be skipped on Python 3.13, and statements inside `if sys.version_info >= (3, 12):` must be included.
4. **C-Builtin Enrichment**: C-builtins whose runtime signatures lack parameter types (`len`, `print`, `max`) must receive typed parameters and return types from `.pyi`.
5. **Class-Level Instance Attributes**: Attributes declared in `.pyi` class bodies without runtime `__dict__` presence must be registered as `provenance = 'pyi_stub_only'`.

---

### Task 1: Schema Updates for Overloads & Typeshed Metadata

**Files:**
- Modify: `src/utss/schema.py`
- Test: `tests/test_schema.py`

- [ ] Write failing test in `tests/test_schema.py` checking new table `callable_overloads`, updated columns in `environments` (`sys_platform`), `containers` (`stub_path`), `callables` (`has_overloads`, `overload_count`, `type_params_json`), and `parameters` (`overload_id`, `type_source`).
- [ ] Run `uv run pytest tests/test_schema.py` to confirm failure.
- [ ] Update `SCHEMA_SQL` and `EXPECTED_TABLES` in `src/utss/schema.py`.
- [ ] Run `uv run pytest tests/test_schema.py` to confirm pass.
- [ ] Git commit Task 1.

---

### Task 2: Static Guard Evaluator & Embedded Demo Stubs

**Files:**
- Create: `src/utss/overlay.py` (Part 1: `EMBEDDED_DEMO_STUBS`, `_eval_static_guard`, `_flatten_active_statements`)
- Test: `tests/test_overlay.py`

- [ ] Write failing test in `tests/test_overlay.py` testing static evaluation of `sys.version_info` comparisons (e.g. `>= (3, 12)` vs `< (3, 8)`) and `sys.platform` checks, plus embedded demo stubs availability.
- [ ] Run `uv run pytest tests/test_overlay.py` to confirm failure.
- [ ] Implement embedded stubs dictionary and AST condition evaluation methods in `src/utss/overlay.py`.
- [ ] Run `uv run pytest tests/test_overlay.py` to confirm pass.
- [ ] Git commit Task 2.

---

### Task 3: Static `.pyi` Overlay Cataloger Engine

**Files:**
- Modify: `src/utss/overlay.py` (Part 2: `StaticPyiOverlayCataloger`)
- Modify: `src/utss/cataloger.py`
- Test: `tests/test_overlay.py`

- [ ] Write failing test in `tests/test_overlay.py` for:
  - Enriching ambient scope (`builtins.len`, `open`, `max`, `str.split`) using embedded demo stubs.
  - Verifying `@overload` records in `callable_overloads` and `parameters`.
  - Verifying generic type enrichment on `sys.argv` (`list[str]`) and `os.environ`.
  - Verifying `sys.version_info >= (3, 12)` branch inclusion on Python 3.13 (`getunicodeinternedsize`).
- [ ] Run `uv run pytest tests/test_overlay.py` to confirm failure.
- [ ] Implement `StaticPyiOverlayCataloger` in `src/utss/overlay.py` and hook `apply_pyi_overlay` into `PythonSpectrumCataloger`.
- [ ] Run `uv run pytest tests/test_overlay.py` to confirm pass.
- [ ] Git commit Task 3.

---

### Task 4: Diagnostic Queries, CLI Commands & End-to-End Verification

**Files:**
- Modify: `src/utss/queries.py`
- Modify: `src/utss/cli.py`
- Test: `tests/test_cli.py`, `tests/test_overlay.py`

- [ ] Write failing test in `tests/test_cli.py` for `utss harvest --demo-stubs`, `utss query --overloads`, and `utss query --pyi-enriched`.
- [ ] Run `uv run pytest tests/test_cli.py` to confirm failure.
- [ ] Implement Query D (`query_overloads`) and Query E (`query_pyi_enrichment`) in `src/utss/queries.py`.
- [ ] Update `src/utss/cli.py` to add `--demo-stubs`, `--typeshed-dir`, `--overloads`, and `--pyi-enriched`.
- [ ] Run full test suite: `uv run pytest`.
- [ ] Run end-to-end harvest and overload query.
- [ ] Git commit Task 4.
