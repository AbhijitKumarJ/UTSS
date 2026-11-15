# Expand Universal Bridge Operation Mappings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expand `dbs/utss_universal_bridge.db` operation mappings across `primitive.string_utf8`, `collection.hash_set`, `collection.fifo_queue`, and `io.file_handle`, re-running the 4-pass empirical catalog scanner and connecting new operations into the Crosswalk Simulator and AST Transpiler.

**Architecture:** Extend `tools/build_universal_bridge.py` with canonical operation definitions for String methods (`contains`, `starts_with`, `ends_with`, `to_lowercase`, `to_uppercase`, `trim`, `replace`, `split`), Hash Set methods (`add`, `remove`, `contains`, `len`, `clear`), FIFO Queue methods (`enqueue`, `dequeue`, `peek`, `len`, `clear`), and File I/O methods (`read`, `write`, `flush`, `close`). Run `tools/build_universal_bridge.py` to bind these operations against empirical language catalogs. Update `server/analysis/bridge_transpiler.py` to map Python AST calls into these canonical concepts.

**Tech Stack:** Python 3.13, SQLite, FastAPI, React 18, TypeScript.

**Spec:** `docs/SPEC_UNIVERSAL_BRIDGE_SCHEMA.md` and Phase 2.3 Bridge Specification.

## Global Constraints

- Transpilation and crosswalk queries must operate against `utss_universal_bridge.db` in read-only mode (`mode=ro`).
- Populator must preserve existing 22 concepts and all type mappings.
- All new operation templates must be valid for all 6 languages (Python, C#, C++, Go, Rust, TypeScript).
- All 58 existing automated pytest tests must pass without regressions.

## Review Focus

- **String Operation Lowering**: `strings.Contains` (Go), `includes` (TS), `contains` (Rust/C#), and `find != npos` (C++) correctly synthesize.
- **Hash Set Lowering**: `add`/`insert`/`delete`/`has`/`contains` operate with appropriate pass semantics (`mut_ref`, `operator`).
- **Queue Lowering**: `push`/`enqueue` and `pop`/`dequeue`/`shift`/`popleft` preserve FIFO conventions.
- **File I/O Lowering**: `read`/`write`/`flush`/`close` correctly synthesize across streams and file descriptors.
- **Crosswalk Simulator Integration**: The UI simulator automatically enables these operations without rendering unnecessary argument inputs for zero-arg methods (`clear`, `flush`, `close`).

---

### Task 1: Expand Operation Definitions in `tools/build_universal_bridge.py`

**Files:**
- Modify: `tools/build_universal_bridge.py`

**Steps:**
- [x] Add `primitive.string_utf8` operation definitions to `OPERATION_MAPPINGS_DEF`:
  - `contains`, `starts_with`, `ends_with`, `to_lowercase`, `to_uppercase`, `trim`, `replace`, `split`.
- [x] Add `collection.hash_set` operation definitions:
  - `add`, `remove`, `contains`, `len`, `clear`.
- [x] Add `collection.fifo_queue` operation definitions:
  - `enqueue`, `dequeue`, `peek`, `len`, `clear`.
- [x] Add `io.file_handle` operation definitions:
  - `read`, `write`, `flush`, `close`.
- [x] Verify syntax template correctness across all 6 targets.

---

### Task 2: Recompile `dbs/utss_universal_bridge.db` & Verify Catalog Bindings

**Files:**
- Run: `.venv/bin/python3 tools/build_universal_bridge.py`
- Verify: `dbs/utss_universal_bridge.db`

**Steps:**
- [x] Run `tools/build_universal_bridge.py` to regenerate `dbs/utss_universal_bridge.db`.
- [x] Verify that `universal_operation_mappings` row count increases from 48 to 150+ rows.
- [x] Confirm catalog bindings (Layer 1 symbol and callable resolution) for all new operations.

---

### Task 3: Connect Operations into AST Transpiler Engine

**Files:**
- Modify: `server/analysis/bridge_transpiler.py`
- Modify: `tests/test_transpiler_engine.py`

**Steps:**
- [x] In `server/analysis/bridge_transpiler.py`, extend `PYTHON_OP_TO_CANONICAL`:
  - Map string methods: `lower`, `upper`, `strip`, `startswith`, `endswith`, `replace`, `split`.
  - Map set methods: `add`, `discard`, `remove`, `clear`.
  - Map file methods: `read`, `write`, `flush`, `close`.
- [x] Write test `test_transpile_string_and_set_operations` in `tests/test_transpiler_engine.py`.
- [x] Run `.venv/bin/pytest tests/test_transpiler_engine.py` to verify passing.
- [x] Commit: `feat(bridge): expand universal operation mappings for strings, sets, queues, and file IO`

---

### Task 4: Verify Crosswalk Simulator & API Integration

**Files:**
- Modify: `tests/test_bridge_api.py`

**Steps:**
- [x] Add test `test_string_and_set_crosswalk_translations` in `tests/test_bridge_api.py`.
- [x] Verify `/api/bridge/lookup?concept_key=collection.hash_set` returns newly populated operations.
- [x] Verify `/api/bridge/lookup?concept_key=primitive.string_utf8` returns newly populated operations.
- [x] Run `.venv/bin/pytest tests/test_bridge_api.py`.

---

### Task 5: Full Regression Testing & Production Build

**Files:**
- Run: `.venv/bin/pytest -v`
- Run: `npm --prefix React_UI run build`

**Steps:**
- [x] Run complete pytest test suite (all tests passing).
- [x] Rebuild React frontend assets and verify clean bundle compilation.
- [x] Verify clean git status and commit to `master`.
