# Block & Function-Level AST Transpiler Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a multi-statement, block- and function-level AST transpiler engine that lowers Python AST into C#, Rust, TypeScript, C++, and Go using verified relational signatures from `utss_universal_bridge.db`, and surface it in an interactive split-pane Monaco transpilation sandbox with empirical catalog provenance tracing.

**Architecture:** Implement `server/analysis/bridge_transpiler.py` which recursively walks Python AST nodes (type annotations, variable declarations, control flow loops, branching, function definitions, context managers, and exception handling), resolves them against `utss_universal_bridge.db`, and emits idiomatic target code with deduplicated imports and catalog provenance. Expose `POST /api/bridge/transpile` in FastAPI, and build `TranspilationSandbox.tsx` in React with Monaco editors, preset suites, and an empirical provenance inspector table.

**Tech Stack:** Python `ast` module, SQLite (`utss_universal_bridge.db`), FastAPI, React 18, TypeScript, Monaco Editor, CSS Variables.

**Spec:** `docs/Ideas/cross lang universal bridge 3.md` (Sections 2, 3, and UI component architecture).

## Global Constraints

- Transpilation lowering must query `utss_universal_bridge.db` in read-only mode (`mode=ro`).
- Generated target code must be valid, idiomatic code for all 5 targets (C# .NET, Rust, TypeScript, C++20, Go) including headers (`using`, `use`, `#include`, `import`).
- Monaco editors must use local bundled workers with zero CDN network access.
- All 4 themes (UTSS Dark, VS Code Dark+, VS Code Light+, Monokai) must be maintained.
- All newly created backend functionality must be verified with automated pytest suites.

## Review Focus

- **Control flow synthesis**: `for ... in ...` correctly emits `foreach` (C#), `for ... in` (Rust), `for ... of` (TS), range-for (C++), and `for _, x := range` (Go).
- **Function signature synthesis**: `def func(a: int, b: str) -> bool:` emits typed method/function signatures with accurate parameter and return types for each language.
- **Generic type instantiation**: Nested generics like `dict[str, list[int]]` recursively map to `Dictionary<string, List<long>>` (C#), `HashMap<String, Vec<i64>>` (Rust), `Map<string, number[]>` (TS), `std::unordered_map<std::string, std::vector<int64_t>>` (C++), and `map[string][]int64` (Go).
- **Deduplicated headers**: Target emissions must collect, normalize, and format imports without duplicates.
- **Catalog provenance trace**: Every lowered construct must carry its matched `concept_key`, `target_language`, `resolved_target`, `verification_status`, and `catalog_signature`.

---

### Task 1: Core AST Transpiler Engine (`server/analysis/bridge_transpiler.py`)

**Files:**
- Create: `server/analysis/bridge_transpiler.py`
- Test: `tests/test_transpiler_engine.py`

**Steps:**
- [x] Write failing test `tests/test_transpiler_engine.py` testing:
  - Transpiling variable declarations with types (`items: list[int] = []`).
  - Transpiling operations (`items.append(42)`, `len(items)`, `scores["alice"] = 100`).
  - Transpiling control flow loops (`for x in items:`).
  - Transpiling branching (`if len(items) > 0: ... else: ...`).
  - Transpiling function signatures (`def calculate(x: int) -> int:`).
  - Transpiling context managers (`with open("test.txt") as f:`).
  - Transpiling exceptions (`raise ValueError("error")`).
  - Verifying all 5 target languages (`csharp`, `rust`, `typescript`, `cpp`, `go`).
- [x] Run `pytest tests/test_transpiler_engine.py` to confirm failure.
- [x] Implement `server/analysis/bridge_transpiler.py`:
  - `BridgeCatalogRepository`: Queries `utss_universal_bridge.db` for type mappings, operation mappings, and protocol mappings.
  - `BridgeTranspiler`:
    - `resolve_type_node`: Recursively maps AST types and generics (`Subscript`, `BinOp` union, `Name`).
    - `transpile_module`: Parses code via `ast.parse`, lowers statements, collects imports, produces formatted code and provenance trace.
    - `_lower_stmt`: Handles `AnnAssign`, `Assign`, `Expr`, `For`, `While`, `If`, `FunctionDef`, `With`, `Raise`, `Return`.
    - `_render_expr`: Recursively renders literals, identifiers, binary ops, compares, calls, method invocations, and collection initializers.
    - Formatters for variable declarations, functions, loops, and target imports.
- [x] Run `pytest tests/test_transpiler_engine.py` and verify all tests pass.
- [x] Commit: `feat(transpiler): implement block and function-level AST transpiler engine with multi-target emission`

---

### Task 2: FastAPI Transpilation Endpoint (`POST /api/bridge/transpile`)

**Files:**
- Modify: `server/routes.py`
- Modify: `tests/test_transpiler_engine.py`

**Steps:**
- [x] Add endpoint test in `tests/test_transpiler_engine.py`:
  - `POST /api/bridge/transpile` with Python code snippet returns 200 with `source_python` and emissions for all target languages.
  - Invalid Python syntax returns 400 with syntax error detail.
- [x] Implement route in `server/routes.py`:
  - Define `TranspileSnippetRequest`: `python_code: str`, `target_languages: Optional[List[str]]`.
  - Expose `POST /api/bridge/transpile`.
  - Connect to `BridgeCatalogRepository` and `BridgeTranspiler`.
- [x] Run `pytest tests/test_transpiler_engine.py` and verify route tests pass.
- [x] Commit: `feat(api): expose POST /api/bridge/transpile endpoint with catalog provenance`

---

### Task 3: TypeScript Types & API Client

**Files:**
- Modify: `React_UI/src/types.ts`
- Modify: `React_UI/src/api.ts`

**Steps:**
- [x] In `React_UI/src/types.ts`, define:
  - `ProvenanceRecord`
  - `TargetSynthesisOutput`
  - `TranspileSnippetResponse`
- [x] In `React_UI/src/api.ts`, add:
  - `transpileSnippet(code: string, targets?: string[]): Promise<TranspileSnippetResponse>`
- [x] Verify types with `(cd React_UI && ./node_modules/.bin/tsc --noEmit)`.
- [x] Commit: `feat(ui): add TypeScript types and API client for AST transpiler`

---

### Task 4: Interactive Transpilation Sandbox & Provenance Inspector UI Components

**Files:**
- Create: `React_UI/src/components/transpiler/TranspilationSandbox.tsx`
- Create: `React_UI/src/components/transpiler/ProvenanceInspector.tsx`
- Modify: `React_UI/src/components/RosettaPlayground.tsx`
- Modify: `React_UI/src/App.css`

**Steps:**
- [x] Implement `ProvenanceInspector.tsx`:
  - Searchable/filterable table showing lowered constructs, concept key, target language, resolved symbol, verification status, and catalog signature.
- [x] Implement `TranspilationSandbox.tsx`:
  - Preset snippet dropdown (Collections, Control Flow Loops, Function Signatures, File I/O & Exceptions).
  - Left pane: Monaco editor with Python syntax highlighting and live editing.
  - Right pane: Target Language tab bar (`C# .NET`, `Rust`, `TypeScript`, `C++20`, `Go`) and Monaco editor in read-only mode with target syntax highlighting.
  - Action bar: "🚀 Transpile (Ctrl+Enter)" button with loading spinner, and presets quick-load.
  - Lower pane: Collapsible Empirical Provenance Inspector table.
- [x] Integrate into `RosettaPlayground.tsx`:
  - Add top sub-nav bar switching between:
    - `[ 🚀 AST Transpiler Sandbox ]`
    - `[ 🗂️ Universal Concept Matrix ]` (the existing concept browser)
- [x] Add CSS styling in `App.css`.
- [x] Commit: `feat(ui): implement split-pane Monaco transpilation sandbox and empirical provenance inspector`

---

### Task 5: Production Build & Automated Verification

**Files:**
- Build: `npm --prefix React_UI run build`
- Verify: `pytest -v`

**Steps:**
- [x] Rebuild React frontend assets and verify zero bundle errors.
- [x] Run complete pytest test suite (all backend and API tests).
- [x] Verify clean git status and commit all changes.
