# Phase 3: Deep Pure-AST Workspace Harvester (Stratum 3) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 3 (`Ideation/3.md`) to provide zero-execution, pure-AST harvesting of local project workspaces (Stratum 3), featuring constructor attribute synthesis with parameter type propagation, scope-bounded generator detection, package layout/relative import resolution, static `__all__` evaluation, AST coordinates, and `--demo-workspace` testing fixtures.

**Architecture:** Pure static AST analysis (`ast.parse`) using visitor and statement walker passes. Resolves relative imports against module hierarchy without running user code. Synthesizes `self.<attr>` symbols in `symbols` and `state_members` from `__init__`, `__new__`, and `__post_init__` bodies, propagating parameter type annotations. Records 1-indexed line and 0-indexed column spans (`start_line`, `start_col`, `end_line`, `end_col`).

**Tech Stack:** Python 3.13+, `sqlite3`, `ast`, `pathlib`, `tempfile`, `pytest`. Zero external runtime dependencies.

**Spec:** `Ideation/3.md` and `Ideation/3.py`.

## Global Constraints
- **Zero external runtime dependencies**: Pure standard library only.
- **Zero code execution for Stratum 3**: Local workspace files must never be imported via `importlib` or executed via `exec`/`eval`.
- **Dual-Layer Schema**: Retain the 11-table relational structure (WAL mode, foreign keys ON).
- **100% test pass rate**: All existing 27 tests must continue to pass; all new tests must pass.

---

## Tasks

### Task 1: Schema Updates for AST Coordinates & Callable Modifiers
- [x] Write failing test in `tests/test_schema.py` verifying new columns on `containers` (`start_line`, `start_col`, `end_line`, `end_col`), `symbols` (`start_line`, `start_col`, `end_line`, `end_col`), and `callables` (`is_static`, `is_class_bound`, `signature_source`).
- [x] Run `pytest tests/test_schema.py` to confirm test failure.
- [x] Update `src/utss/schema.py` DDL with new columns and indexes.
- [x] Run `pytest tests/test_schema.py` to confirm test passes.
- [x] Commit Task 1 changes.

### Task 2: Embedded Demo Workspace Fixtures & Utilities
- [x] Write test in `tests/test_workspace.py` verifying `EMBEDDED_DEMO_WORKSPACE_FILES` structure and discovery helper `discover_workspace_py_files`.
- [x] Run test to confirm failure.
- [x] Implement `EMBEDDED_DEMO_WORKSPACE_FILES` and layout discovery logic (handling `src/` layout, flat layout, and ignored directories) in `src/utss/workspace.py`.
- [x] Run test to confirm test passes.
- [x] Commit Task 2 changes.

### Task 3: Deep AST Walker with Init Attribute Synthesis & Generator Detection
- [x] Write tests in `tests/test_workspace.py`:
  - `__init__` `self.<attr>` synthesis with parameter type propagation (e.g. `subtotal: float`).
  - Private mangling for `self.__secret_token` (`private_mangled`).
  - Scope-bounded generator detection (`yield` inside function, but not when inside nested lambda/function).
  - PEP 695 `type CustomerId = int` alias extraction.
  - Relative import resolution (`from .models import Order` -> target `commerce_engine.models`).
  - Static `__all__` evaluation and `is_in_dunder_all` tracking.
  - AST span coordinates (`start_line`, `start_col`, `end_line`, `end_col`).
- [x] Run tests to confirm failures.
- [x] Implement `WorkspaceAstCataloger` in `src/utss/workspace.py` integrating with `PythonSpectrumCataloger`.
- [x] Run tests to confirm all workspace tests pass.
- [x] Commit Task 3 changes.

### Task 4: CLI Integration & Diagnostic Queries (Queries F, G, H)
- [x] Write tests in `tests/test_cli.py` for:
  - `utss harvest --demo-workspace`
  - `utss query --workspace-symbols`
  - `utss query --workspace-generators`
  - `utss query --workspace-imports`
- [x] Run tests to confirm failure.
- [x] Update `src/utss/queries.py` to add `query_workspace_symbols`, `query_workspace_generators`, and `query_workspace_imports`.
- [x] Update `src/utss/cli.py` to add `--demo-workspace` flag to `harvest` and new flags to `query`.
- [x] Run full test suite (`uv run pytest`) and end-to-end verification.
- [x] Commit Task 4 changes.

### Task 5: Documentation & PRD Updates
- [x] Update `docs/SCHEMA.md`, `docs/CLI.md`, `docs/ARCHITECTURE.md`, `docs/PRD.md`, and `README.md` to document Stratum 3 deep AST harvesting capabilities.
- [x] Create `3.sh` verification script.
- [x] Commit documentation updates.
