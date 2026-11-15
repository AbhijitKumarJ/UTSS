# Transpiler OOP & Error-Handling Synthesis Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend the `BridgeTranspiler` engine to synthesize Object-Oriented classes, structs, dataclasses with constructors and methods, member attribute access (`self.prop`), and structured error recovery (`try / except / finally`) across C# .NET, Rust, TypeScript, C++20, and Go.

**Architecture:** Extend `server/analysis/bridge_transpiler.py` with AST handlers for `ast.ClassDef`, `ast.Attribute`, `ast.Try`, and `ast.ExceptHandler`. Classes with field annotations are synthesized into typed classes/records (C#), structs with `impl` blocks (Rust), typed interfaces/classes (TS), struct/class with initializer lists (C++), and struct definitions with `New...` constructors (Go). `try/except/finally` constructs are lowered to target-idiomatic try-catch or panic/recover blocks with catalog exception mappings. Expose curated presets in `TranspilationSandbox.tsx`.

**Tech Stack:** Python 3.13 `ast` module, SQLite (`utss_universal_bridge.db`), FastAPI, React 18, TypeScript, Monaco Editor.

**Spec:** `docs/Ideas/cross lang universal bridge 3.md` and Phase 3.3 Transpiler Specification.

## Global Constraints

- Transpilation lowering must query `utss_universal_bridge.db` in read-only mode (`mode=ro`).
- Generated target code must be valid, idiomatic code for all 5 targets (C# .NET, Rust, TypeScript, C++20, Go) including headers (`using`, `use`, `#include`, `import`).
- Monaco editor bundle must remain 100% self-contained with zero external CDN dependencies.
- All 4 themes (UTSS Dark, VS Code Dark+, VS Code Light+, Monokai) must render cleanly without visual glitches.
- Full pytest test suite must maintain 100% pass rate with zero regressions across existing 55 tests.

## Review Focus

- **Class Field Typing**: Python typed class attributes (`id: int`, `name: str`) correctly lower to respective target field types (`long`, `i64`, `number`, `int64_t`, `int64`).
- **Constructor Synthesis**: Dataclasses and classes synthesize target-idiomatic constructors (`public User(...)`, `pub fn new(...) -> Self`, `constructor(...)`, initialization list `User(...) : id(id) {}`, `func NewUser(...) *User`).
- **Method & Self Receiver Mapping**: Instance methods with `self` receiver omit `self` in target call signatures and map `self.prop` to `this.Prop` (C#), `self.prop` (Rust), `this.prop` (TS), `this->prop` (C++), and `receiver.Prop` (Go).
- **Structured Error Handling**: `try ... except ValueError as err: ... finally: ...` correctly lowers to target paradigms (`catch (ArgumentException err)`, `catch (err: any)`, `catch (const std::exception& err)`, Go `defer recover()`, and Rust result/catch block).
- **Catalog Exception Provenance**: Lowered exception types track canonical concept keys (`exception.argument_null`, `exception.io_error`) in the provenance table.

---

### Task 1: Class, Struct & Dataclass Lowering Engine

**Files:**
- Modify: `server/analysis/bridge_transpiler.py`
- Modify: `tests/test_transpiler_engine.py`

**Steps:**
- [x] Write failing test `test_transpile_class_and_dataclass` in `tests/test_transpiler_engine.py`:
  - Python class with typed fields:
    ```python
    class User:
        id: int
        name: str
        is_active: bool
    ```
  - Verify C# emits `public class User` with typed properties and constructor.
  - Verify Rust emits `pub struct User` and `impl User { pub fn new(...) -> Self }`.
  - Verify TypeScript emits `export class User` with constructor.
  - Verify C++ emits `struct User` with constructor initializer list.
  - Verify Go emits `type User struct` and `func NewUser(...) *User`.
- [x] Run `.venv/bin/pytest tests/test_transpiler_engine.py -k test_transpile_class_and_dataclass` to confirm failure.
- [x] Implement `ast.ClassDef` handling in `server/analysis/bridge_transpiler.py`:
  - Extract typed attributes (`ast.AnnAssign` in class body).
  - Extract methods (`ast.FunctionDef` in class body, distinguishing `__init__` from regular instance methods).
  - Synthesize language-specific class/struct definitions, constructors, and method signatures.
  - Collect imports and record catalog provenance.
- [x] Run `.venv/bin/pytest tests/test_transpiler_engine.py` to verify tests pass.
- [x] Commit: `feat(transpiler): implement class, struct, and dataclass synthesis across 5 target languages`

---

### Task 2: Attribute Access & Instance Method Dispatch

**Files:**
- Modify: `server/analysis/bridge_transpiler.py`
- Modify: `tests/test_transpiler_engine.py`

**Steps:**
- [x] Write failing test `test_transpile_class_with_methods_and_attributes` in `tests/test_transpiler_engine.py`:
  - Class with instance method accessing `self.prop`:
    ```python
    class Counter:
        count: int

        def increment(self, step: int) -> int:
            self.count = self.count + step
            return self.count
    ```
  - Verify `self.count` lowers to `this.Count` (C#), `self.count` (Rust), `this.count` (TS), `this->count` (C++), `c.Count` (Go).
  - Verify `self` is stripped from target parameter lists while passing `&mut self` in Rust and pointer receiver `(c *Counter)` in Go.
- [x] Run `.venv/bin/pytest tests/test_transpiler_engine.py -k test_transpile_class_with_methods_and_attributes` to confirm failure.
- [x] Implement `ast.Attribute` in `_render_expr` and receiver handling in `_lower_method`:
  - Detect `self` receiver in Python AST methods.
  - Render attribute access according to target language rules.
  - Handle member assignments (`self.count = ...`).
- [x] Run `.venv/bin/pytest tests/test_transpiler_engine.py` to verify tests pass.
- [x] Commit: `feat(transpiler): implement attribute access and instance method dispatch`

---

### Task 3: Error-Handling Synthesis (`try / except / finally`)

**Files:**
- Modify: `server/analysis/bridge_transpiler.py`
- Modify: `tests/test_transpiler_engine.py`

**Steps:**
- [x] Write failing test `test_transpile_try_except_finally` in `tests/test_transpiler_engine.py`:
  - Code snippet:
    ```python
    try:
        items: list[int] = []
        val: int = items[0]
    except IndexError as err:
        val: int = -1
    finally:
        items.clear()
    ```
  - Verify C# emits `try { ... } catch (IndexOutOfRangeException err) { ... } finally { ... }`.
  - Verify TypeScript emits `try { ... } catch (err) { ... } finally { ... }`.
  - Verify C++ emits `try { ... } catch (const std::exception& err) { ... }`.
  - Verify Go emits deferred cleanup and panic recovery.
  - Verify Rust emits structured error recovery with provenance trace.
- [x] Run `.venv/bin/pytest tests/test_transpiler_engine.py -k test_transpile_try_except_finally` to confirm failure.
- [x] Implement `ast.Try` and `ast.ExceptHandler` in `_lower_stmt`:
  - Resolve Python exception types (`IndexError`, `ValueError`, `KeyError`, `FileNotFoundError`) to canonical concepts via `PYTHON_TYPE_TO_CONCEPT`.
  - Look up concrete target exception symbols and required imports from `utss_universal_bridge.db`.
  - Format target-idiomatic try-catch/finally blocks.
- [x] Run `.venv/bin/pytest tests/test_transpiler_engine.py` to verify all tests pass.
- [x] Commit: `feat(transpiler): implement structured try-except-finally error handling synthesis`

---

### Task 4: UI Presets & Monaco Sandbox Integration

**Files:**
- Modify: `React_UI/src/components/transpiler/TranspilationSandbox.tsx`
- Modify: `React_UI/src/App.css`

**Steps:**
- [x] Add new presets to `PRESETS` dictionary in `TranspilationSandbox.tsx`:
  - **"OOP: Classes & Dataclasses"**: Class with typed fields and constructor/method.
  - **"Error Recovery: Try / Except / Finally"**: Structured error handling with resource clearing.
- [x] Add visual badge tags in `TranspilationSandbox.tsx` to highlight synthesized language constructs (Classes, Methods, Exception Handlers).
- [x] Verify frontend build with `npm --prefix React_UI run build`.
- [x] Commit: `feat(ui): add OOP and error recovery presets to AST transpiler sandbox`

---

### Task 5: Full Regression Testing & Verification

**Files:**
- Run: `.venv/bin/pytest -v`
- Run: `npm --prefix React_UI run build`

**Steps:**
- [x] Run complete pytest test suite (55+ tests) verifying zero regressions.
- [x] Run production Vite bundle build and confirm zero compilation warnings.
- [x] Verify clean git status and landing on `master`.
