# Visual AST Pipeline & Transpilation Flow Graph Implementation Plan

This plan establishes Option 4: a Visual AST Pipeline & Transpilation Flow Graph linking the parser/AST infrastructure with the multi-target code generation engine. It enables developers and students to visually inspect Python Abstract Syntax Tree (AST) node hierarchies, trace AST lowering decisions, and view per-node cross-language synthesis fragments.

---

## User Stories & Architecture

### User Experience:
1. Within the **Rosetta Playground & AST Transpiler Sandbox**, users can switch between:
   - **`💻 Multi-Target Code Generator`**: Side-by-side Monaco editor and generated C#, Rust, Go, C++, TypeScript tabs.
   - **`🌳 Visual AST Pipeline & Lowering Flow`**: An interactive hierarchical AST node tree and lowering inspector.
2. The Visual AST view parses the active Python code and displays an interactive node graph/tree (e.g. `Module` $\to$ `ClassDef` $\to$ `FunctionDef` $\to$ `Assign` / `Call` / `Try`).
3. Each node displays:
   - Node Type badge (`ClassDef`, `FunctionDef`, `Call`, `Assign`, `Try`, `For`, etc.).
   - Source code snippet / label with line coordinates (`L1:C0 - L8:C20`).
   - Universal IR Concept tag if recognized (`user_type`, `collection.dynamic_array`, `primitive.string_utf8`, `error_recovery`).
4. Clicking any AST node opens the **Node Lowering Inspector**:
   - Displays exact AST node fields and source code extract.
   - Shows targeted lowering preview tabs (C#, Rust, Go, C++, TypeScript) demonstrating how that specific node is lowered into each target language.
   - Includes "Jump to Source Line" and Expand/Collapse branch controls.

### Backend Architecture:
1. **`server/analysis/ast_flow.py`**:
   - AST Visitor / Tree builder that converts `ast.parse(python_code)` into a serializable hierarchical AST flow graph:
     - Node IDs, types, labels, line start/end, column offsets.
     - Universal IR concept categorization.
     - Per-node lowering generation using isolated sub-tree lowering or synthesis extraction.
2. **`POST /api/bridge/ast-flow` Endpoint**:
   - Request: `{ "python_code": str }`
   - Returns: `{ "root": AstFlowNode, "node_count": int, "max_depth": int, "concepts_detected": list[str] }`
   - Handles `SyntaxError` gracefully with line and offset indicators.

---

## Proposed Changes

### 1. Backend: AST Flow Generator & Route
- Create `server/analysis/ast_flow.py`:
  - `build_ast_flow(python_code: str) -> dict`
  - Traverses AST, builds recursive dictionary:
    - `id`: unique node identifier (`node_1`, `node_2`, ...)
    - `node_type`: e.g. `ClassDef`, `FunctionDef`, `Assign`, `Call`, `Try`, `For`, etc.
    - `label`: formatted summary label (e.g. `def process_items(count: int) -> list[int]`)
    - `line_start`, `line_end`, `col_offset`
    - `children`: list of child `AstFlowNode`
    - `ir_concept`: matched concept key if applicable
    - `lowering_previews`: dictionary mapping target languages to rendered snippets
- In `server/routes.py`:
  - Add `AstFlowRequest(BaseModel)` and `POST /api/bridge/ast-flow` endpoint.

### 2. Frontend: Types, API & Visualizer Component
- In `React_UI/src/types.ts`:
  - Add `AstFlowNode`, `AstFlowResponse`, `AstFlowRequest`.
- In `React_UI/src/api.ts`:
  - Add `fetchAstFlow(pythonCode: string): Promise<AstFlowResponse>`.
- In `React_UI/src/components/transpiler/`:
  - Create `AstFlowVisualizer.tsx`:
    - Tree navigation view with expand/collapse and filtering by node type.
    - Inspector panel displaying selected node details, source lines, and per-target lowering snippets.
- In `React_UI/src/components/transpiler/TranspilationSandbox.tsx`:
  - Add view switcher header: `[ 💻 Multi-Target Transpiler ]` vs `[ 🌳 Visual AST Pipeline & Lowering Flow ]`.

### 3. Automated Tests: `tests/test_ast_flow_api.py`
- Test parsing valid classes, functions, and loops into AST flow tree.
- Test line number and column coordinate precision.
- Test detection of IR concepts (e.g. `user_type`, collections).
- Test syntax error handling.

---

## Verification Plan
1. Run pytest: `.venv/bin/pytest tests/test_ast_flow_api.py -v`.
2. Run full pytest suite: `.venv/bin/pytest -v`.
3. Compile React UI: `npm --prefix React_UI run build`.
4. Verify interactive flow tree and lowering tabs in UI.
