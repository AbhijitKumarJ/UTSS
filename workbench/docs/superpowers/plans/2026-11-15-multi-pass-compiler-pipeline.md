# Multi-Pass Transpiler Transformation Pipeline Implementation Plan

This plan establishes Option 1 of the multi-phase roadmap: an interactive multi-pass compiler pipeline visualizer for the Universal Language Architecture platform. It reveals the intermediate compilation stages between source Python code and synthesized target code (C#, Rust, TypeScript, C++, Go).

---

## User Stories & Architecture

### User Experience:
1. Within the **Rosetta Playground & Transpiler Sandbox**, users can select **`⚙️ Multi-Pass Compiler Pipeline`**.
2. An interactive pass stepper displays the 4 classical stages of a multi-language transpiler:
   - **Pass 1 (Frontend)**: AST Parsing, syntax tree structure, node count, and AST textual representation.
   - **Pass 2 (Semantic Analysis)**: Symbol Environment Table displaying inferred variable types (`env_types`), scopes, and matched universal concepts (`user_type`, `collection.dynamic_array`, `primitive.int64`).
   - **Pass 3 (Middle-End IR)**: Memory Model, mutability analysis (`let mut` vs `ref_gc`), receiver pass kind (`mut_ref`, `val`, `pointer`), required standard imports, and impedance notes for the selected target language.
   - **Pass 4 (Backend Emission)**: Final synthesized target code alongside the empirical catalog provenance trace.
3. Users can switch between target languages (Rust, C#, Go, C++, TypeScript) in real time to see how Middle-End and Backend passes adapt to different target language semantics.

### Backend Architecture:
1. **`server/analysis/pipeline_passes.py`**:
   - `run_compiler_pipeline(python_code: str, target_language: str = "rust") -> dict`:
     - Runs Pass 1: parses AST, generates AST dump and stats.
     - Runs Pass 2: performs symbol environment extraction (`env_types`, variable bindings, types, and concept keys).
     - Runs Pass 3: derives target memory models, mutability inference, required imports, and impedance rationale.
     - Runs Pass 4: executes `BridgeTranspiler.transpile_module()` to produce final code and provenance.
2. **`POST /api/bridge/pipeline-passes` Endpoint in `server/routes.py`**:
   - Request: `{ "python_code": str, "target_language": str }`
   - Returns structured `CompilerPipelineResponse`.

### Frontend Architecture:
1. **Types & API**:
   - `CompilerPassInfo`, `CompilerPipelineResponse` in `React_UI/src/types.ts`.
   - `fetchCompilerPipeline(pythonCode, targetLang)` in `React_UI/src/api.ts`.
2. **`React_UI/src/components/transpiler/CompilerPipelineStepper.tsx`**:
   - Stepper header bar with active pass indicator.
   - Pass 1 tab: AST dump & metrics.
   - Pass 2 tab: Symbol Table grid with type badges and concept tags.
   - Pass 3 tab: Memory Model & Mutability card with impedance analysis.
   - Pass 4 tab: Synthesized code view with provenance table.
3. **`TranspilationSandbox.tsx`**:
   - Adds `pipeline` mode to the sandbox mode switcher bar.

---

## Verification Plan
1. Automated API tests in `tests/test_pipeline_passes_api.py`.
2. Run full pytest suite: `.venv/bin/pytest -v`.
3. Compile React UI: `npm --prefix React_UI run build`.
4. Verify interactive stepper and target language switching in browser.
