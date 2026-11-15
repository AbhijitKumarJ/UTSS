# UTSS Universal Language Analysis & Synthesis Platform: Architecture & Roadmap

This document outlines the current architectural implementation, design principles, data structures, and the forward-looking roadmap for the **Universal Type and Symbol System (UTSS)** Analysis & Synthesis Platform.

---

## 1. System Vision

The UTSS Analysis & Synthesis Workbench serves a dual mission:
1. **Interactive Language Internals Tutor**: A pedagogy-driven environment where students, engineers, and researchers can explore compiler and runtime internals across 6 major languages (Python, C#, C++, Go, Rust, TypeScript).
2. **Cross-Language Synthesis & Data Science Foundation**: A unified analytical foundation enabling cross-language AST comparisons, type system mapping, idiom transpilation, and comparative data science.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   UTSS React Workbench (React 18 + TS)                 │
│  TopNav (DB & Theme Switchers) │ Sidebar │ TutorCard │ Monaco │ Table  │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ REST API (/api/*)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        FastAPI Application Server                      │
│   Routes & Exporters  │  Query Loader (YAML)  │  DB Discovery & Engine │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ SQLite URI (mode=ro&immutable=1)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                   UTSS Multi-Language SQLite Databases                 │
│  cpp_*.db │ cs_*.db │ go_*.db │ python_*.db │ rust_*.db │ ts_*.db     │
│  ┌─────────────────────────┐      ┌──────────────────────────────────┐ │
│  │ Unified Core Tables     │      │ Language-Specific Facet Tables   │ │
│  │ environments, dists,    │      │ cpp_symbol_facets, cs_facets,    │ │
│  │ containers, symbols,    │      │ py_facets, rust_facets,          │ │
│  │ callables, parameters   │      │ go_facets, ts_facets             │ │
│  └─────────────────────────┘      └──────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Current Implementation Status

### 2.1 Backend Core (FastAPI & SQLite Engine)
- **Directory Discovery (`server/db_manager.py`)**: Automatically indexes any SQLite database matching `dbs/*.db`. Distinguishes language (`cpp`, `csharp`, `go`, `python`, `rust`, `typescript`), database variant (`recommended` as the curated starting point vs `full` / `base_full`), runtime engine, platform triplet, and symbol/container counts.
- **Safe Read-Only Execution Engine**:
  - Opened via SQLite URI mode: `file:{path}?mode=ro&immutable=1`.
  - Security Query Filter: Strictly permits `SELECT`, `WITH`, and `EXPLAIN` statements. Disallows all DDL/DML keywords (`ATTACH`, `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`), while safely stripping quoted string literals so legitimate queries like `WHERE name IN ('insert', 'update')` execute without false positives.
  - Progress Handler Timeout: Native SQLite progress handler aborts queries exceeding 5.0 seconds.
  - Efficient 500-Row Single-Pass Preview: Fetches 501 rows to set `has_more: true` without expensive `COUNT(*)` table scans.
- **Modular Curriculum Loader (`server/query_loader.py`)**:
  - Parses modular `.sql` curriculum files with YAML frontmatter headers (`/*--- ... ---*/`).
  - Dynamically constructs query trees grouped by suite and sequence.

### 2.2 Frontend Workbench (`React_UI/` & `static/`)
- **React 18 + TypeScript + Vite**: Client-only single-page application compiled into `static/` and served directly by FastAPI.
- **Home & Default User Guide (`HomeOverview.tsx`)**:
  - Serves as the landing view by default and can be reached anytime via the top-left clickable `UTSS Workbench` brand button or the `🏠 Overview` mode tab.
  - Contains complete platform documentation, 4 interactive quick-launch cards (Tutoring, Comparative Analytics, Rosetta Playground, Schema Discovery), database tier hierarchy breakdowns, relational schema guides, and keyboard shortcut references.
- **Compact Ergonomic Navigation (`TopNav.tsx`)**:
  - Replaced the wide subtitle header with an interactive compact brand button, freeing up over 350px of horizontal space for mode tabs and controls.
  - Mode tabs for `🏠 Overview`, `🎓 Tutoring & Internals`, `📊 Comparative Analytics`, and `🔄 Rosetta Playground`.
  - Guaranteed visible theme selector (`🎨 Theme:`) with `flex-shrink: 0`, preventing viewport clipping across all screen sizes.
- **Interactive SQL Runner & Schema Discovery (`SqlEditor.tsx`)**:
  - Monaco editor with local bundling via `loader.config({ monaco })` from `"monaco-editor": "^0.57.0"`, eliminating external CDN dependencies.
  - `🔍 Show Schema` toolbar button: Immediately loads and executes `SELECT * FROM sqlite_schema;` against the active target (transparently mapped to `sqlite_temp_schema` on federated in-memory databases).
  - Interactive SQL execution with `Ctrl+Enter` / `Cmd+Enter` shortcuts via mutable closure references.
  - Editor auto-layout and 100% height utilization with full syntax highlighting.
- **Multi-Theme Engine**:
  - 4 complete theme token palettes: **UTSS Slate Dark**, **VS Code Dark+**, **VS Code Light+**, and **Monokai**.
  - Synchronized CSS custom properties (`--bg-main`, `--bg-surface`, `--bg-card`, `--accent-primary`, etc.) paired with custom registered Monaco themes (`monaco.editor.defineTheme`).
  - Pre-render FOUC-prevention script restoring theme preferences from `localStorage`.
- **Anti-Squish Ergonomic Layout**:
  - Collapsible `TutorCard` component (`[− Collapse Notes]` / `[+ Expand Notes]`) allowing students to expand their workspace.
  - Fixed-minimum heights on Monaco editor and results table (`min-height: 260px`) with scroll containers preventing layout squishing.
  - Preserves student-modified SQL in the editor when toggling databases.
- **Accessible Data Table & CSV Exporter**:
  - Sticky table headers (`position: sticky; top: 0`), distinct italicized `NULL` indicators, and instant RFC 4180 client-side CSV downloads.

### 2.3 Curricula & Language Coverage (39 Lessons Total)
All 12 databases across 6 languages are fully supported with progressive lessons:
1. **Python** (`queries/python/tutoring/` - 8 lessons): Strata/Environments, Container Hierarchy, Keywords vs Soft Keywords, C-implemented vs Python symbols, Descriptor Protocol, Dunder Lifecycle, Callable Signatures, and C3 MRO Linearization.
2. **C#** (`queries/csharp/tutoring/` - 6 lessons): .NET 10 Runtime Strata, Type Taxonomy (Class/Struct/Record/Interface), `readonly` & stack-only `ref struct` (`Span<T>`), Extension Methods & Async State Machines, Init-Only Properties (`init`), and Polymorphic V-Table / Interface Contracts.
3. **C++** (`queries/cpp/tutoring/` - 6 lessons): ISO Fundamental Types & Compilation Strata, Header/Namespace Containment, Template Metaprogramming & Parameters, `constexpr` / `noexcept` / `const` Guarantees, Virtual Method Dispatch & Pure Interfaces, and Parameter Passing Semantics (`pass_by`).
4. **Go** (`queries/go/tutoring/` - 6 lessons): Predeclared Builtins & `std` Packages, Package Boundaries & Export Casing Rules, Anonymous Struct Embedding over Inheritance, Implicit Interface Satisfaction, Value vs Pointer Receivers (`*T`), and Variadic Signatures.
5. **Rust** (`queries/rust/tutoring/` - 6 lessons): Standard Prelude & Crate Strata (`core`/`alloc`/`std`), Module Trees & `pub(crate)` Visibility, Algebraic Data Types (Structs & Enum Variant Payloads), Traits & Compiler Auto-Traits (`Send`/`Sync`), Ownership & Receiver Kinds (`&self`, `&mut self`, `self`), and Built-in Macros & Reserved Keywords.
6. **TypeScript** (`queries/typescript/tutoring/` - 6 lessons): Ambient Scope & ECMAScript Standard Globals, Built-in Utility Types (`Partial`, `Readonly`, `Record`, `Pick`), Erased Interfaces vs Runtime Classes, Type Modifiers (`readonly`, `?`, `abstract`), Class Heritage Clauses (`extends`, `implements`), and ES Module Export Patterns.
7. **Comparative Analytics** (`queries/comparative/` - 1 lesson): Cross-language symbol density, container distribution, and environment metrics.

---

## 3. Database Architecture & Facet Schema

Each UTSS SQLite database exposes two tiers of relational data:

### 3.1 Unified Core Tables (Universal Schema)
- `environments`: Compiler/interpreter identification, version numbers, platform triplets, capture timestamps.
- `distributions`: Architectural strata (0: Ambient/Predeclared, 1: Standard Library, 2: Third-Party Packages, 3: Workspace Code).
- `containers`: Lexical and organizational units (namespaces, modules, classes, structs, packages, crates, headers).
- `symbols`: Declared entities (functions, methods, properties, variables, constants, keywords, types).
- `callables`: Signatures, return type expressions, overload counts, async/static flags.
- `parameters`: Ordered parameter metadata, type annotations, default value flags.

### 3.2 Language-Specific Facet Tables
- `py_container_facets` & `py_symbol_facets`: C-implementation flags, descriptor kinds, dunder categories, Python runtime types, MRO JSON.
- `cs_container_facets` & `cs_symbol_facets`: `is_readonly_struct`, `is_ref_struct`, `is_extension_method`, `is_init_only`, `generic_type_parameters_json`, `operator_kind`.
- `cpp_container_facets` & `cpp_symbol_facets`: `is_template`, `template_params_json`, `is_constexpr`, `is_noexcept`, `is_const`, `is_virtual`, `is_pure_virtual`, `pass_by`.
- `go_container_facets` & `go_symbol_facets`: `package_name`, `embedded_fields_json`, `is_exported`, `receiver_kind`, `receiver_type`, `is_variadic`.
- `rust_container_facets` & `rust_symbol_facets`: `is_pub`, `is_pub_crate`, `is_auto_trait`, `where_clause_json`, `self_kind`, `is_unsafe`, `abi`.
- `ts_container_facets` & `ts_symbol_facets`: `is_ambient`, `is_export`, `is_default_export`, `is_readonly`, `is_optional`, `is_abstract`, `heritage_clauses_json`.

---

## 4. Future Roadmap & Phased Evolution

For full technical specifications and implementation details, see:
- [docs/CROSS_LANGUAGE_SYNTHESIS_ROADMAP.md](CROSS_LANGUAGE_SYNTHESIS_ROADMAP.md) — Comprehensive execution roadmap for cross-language federation, profiling, and bridge synthesis.
- [docs/SPEC_CROSS_LANGUAGE_CURRICULUM.md](SPEC_CROSS_LANGUAGE_CURRICULUM.md) — Detailed 10-lesson cross-language curriculum across 4 tracks.
- [docs/SPEC_UNIVERSAL_BRIDGE_SCHEMA.md](SPEC_UNIVERSAL_BRIDGE_SCHEMA.md) — Universal Bridge database schema, 4-pass populator, and canonical IR concepts.

```
┌────────────────────────────────────────────────────────────────────────┐
│                        UTSS ROADMAP PHASES                             │
├─────────────────────┬───────────────────┬──────────────────────────────┤
│ Phase 1 (Delivered) │ Phase 2 (Active)  │ Phase 3 & 4 (Future)         │
│ Core Workbench &    │ Federation, Data  │ Visual AST, Transpilation,   │
│ 6-Lang Curricula    │ Science & Bridge  │ Multi-Lang Ecosystem Slices  │
└─────────────────────┴───────────────────┴──────────────────────────────┘
```

### Phase 2: Cross-Language Synthesis & Universal Bridge Engine

#### Phase 2.1: Multi-Database Federation & 10-Lesson Curriculum (Delivered)
- [x] **Multi-Database SQLite Federation in `DatabaseManager`**:
  - Expose `federated_recommended` and `federated_full` targets in `server/db_manager.py` using SQLite `:memory:` connections attaching all 6 catalogs (`py`, `cs`, `cpp`, `go`, `rust`, `ts`).
  - Compile in-memory master views: `v_all_environments`, `v_all_containers`, `v_all_symbols`, `v_all_callables`, `v_all_parameters`, `v_all_distributions`, `v_all_state_members`, `v_all_symbol_aliases`.
- [x] **10 Cross-Language Curriculum Lessons (`queries/comparative/`)**:
  - Implemented the 10 progressive lessons across the 4 structural tracks (Scope & Packaging, Memory & Passing, Polymorphism, Execution & Safety) per [SPEC_CROSS_LANGUAGE_CURRICULUM.md](file:///home/abhijit/Videos/transpilers/UTSS/workbench/docs/SPEC_CROSS_LANGUAGE_CURRICULUM.md).
- [x] **Activate "Comparative Analytics" Tab in React Workbench**:
  - Interactive mode switching between single-language tutoring and federated multi-language comparative exploration, automatic database resolution to `federated_recommended`, and full Monaco Editor integration.

#### Phase 2.2: Automated Empirical Data Science Profiling (Delivered)
- [x] **Comparative Analysis Suite (`tools/utss_comparative_analysis.py`)**:
  - Standalone CLI & programmatic analysis engine aggregating Layer 1 core tables and cross-language metrics.
  - Generates multi-language symbol census, mutability matrices, parameter passing distributions, overload multiplicities, error handling models, and asymmetric pairwise transpiler impedance matrices.
- [x] **Comprehensive Empirical Report (`docs/EMPIRICAL_TRANSPILER_IMPEDANCE_REPORT.md`)**:
  - Detailed empirical analysis document reporting quantitative impedance scores and architectural takeaways across Python, C#, C++, Go, Rust, and TypeScript.

#### Phase 2.3: Universal Bridge Database & Rosetta Crosswalk Engine (Delivered)
- [x] **Automated 4-Pass Populator (`tools/build_universal_bridge.py`)**:
  - Implemented 4-pass scanner extracting empirical bindings for canonical IR concepts into [dbs/utss_universal_bridge.db](file:///home/abhijit/Videos/transpilers/UTSS/workbench/dbs/utss_universal_bridge.db).
  - Populates `universal_concepts`, `universal_type_mappings`, `universal_operation_mappings`, `universal_protocol_mappings`, and `discovered_stdlib_taxonomy` per [SPEC_UNIVERSAL_BRIDGE_SCHEMA.md](file:///home/abhijit/Videos/transpilers/UTSS/workbench/docs/SPEC_UNIVERSAL_BRIDGE_SCHEMA.md).
- [x] **Bridge Database Catalog Discovery**:
  - Auto-discovered by `DatabaseManager` with language `"universal"` and fully queryable through the workbench.
- [x] **Rosetta Translation REST API**:
  - Endpoints `/api/bridge/concepts`, `/api/bridge/lookup`, and `/api/bridge/translate` to look up cross-language type templates, memory models, and method signatures.

#### Phase 2.4: Interactive Visual Transpilation Playground (Delivered)
- [x] **Rosetta Matrix Card Explorer**:
  - Interactive 6-column matrix view displaying syntax, memory models, nullability models, required imports, and verification badges side by side across Python, C#, C++, Go, Rust, and TypeScript.
- [x] **Transpilation Verification Sandbox**:
  - Live sandbox translating operations between Source and Target languages (e.g. Python `items.append(42)` $\to$ Rust `items.push(42)` or Go `items = append(items, 42)`).
  - Generates architectural impedance guidance detailing borrow checking (`&mut`), slice re-binding, and required module imports.
- [x] **UI Mode Switcher Integration**:
  - Top navigation tab for "Rosetta Playground" enabling seamless switching between single-language tutoring, federated analytics, and transpiler playground.

---

### Phase 3: Advanced Visual Analytics & Synthesis

#### Phase 3.1: Interactive AST & Container Hierarchy Graph Visualizer (Delivered)
- [x] **Backend Graph API Endpoints (`server/routes.py` & `server/db_manager.py`)**:
  - `/api/graph/containers`: Extracts lexical containment trees with parent-child edges and symbol density counts.
  - `/api/graph/inheritance`: Extracts type inheritance and interface implementation DAGs (`extends`, `implements`, `embeds`) from language facet tables across all 6 targets.
  - `/api/graph/concept-cluster`: Extracts radial star graphs linking universal compiler IR concepts to concrete language types.
- [x] **Interactive Graph Canvas & Layout Engine (`React_UI/src/components/graph/`)**:
  - Interactive SVG canvas with smooth pan, zoom, fit-to-view, and search filtering.
  - Multi-tiered hierarchical layout for tree/DAG structures and radial layout for concept clusters.
  - Node color-coding by container kind (`class`, `interface`, `trait`, `namespace`, `concept`, `target_type`) and stratum.
- [x] **Node Inspector & Direct SQL Bridge (`GraphInspector.tsx`)**:
  - Side inspector displaying container metadata, qualified names, stratum, visibility, and memory models.
  - Direct 1-click **`⚡ Query in SQL Runner`** button pre-populating and executing queries for that container in the interactive editor.
- [x] **TopNav Integration (`TopNav.tsx`)**:
  - Added compact `🌳 AST Graph` mode tab with zero layout squishing and guaranteed visible `🎨 Theme` selector.

#### Phase 3.2: Embedded Empirical Data Science & Impedance Dashboard (Delivered)
- [x] **Backend Comparative Analysis & Report Endpoints**:
  - `GET /api/analysis/comparative`: Computes multi-language symbol census, state mutability matrices, parameter passing spectra, overload multiplicity, error handling models, and 6×6 pairwise directional transpiler impedance matrix.
  - `GET /api/analysis/report`: Generates downloadable GitHub-Flavored Markdown analytical reports.
- [x] **Interactive 6×6 Transpiler Impedance Heatmap & Penalty Inspector**:
  - Color-graded directional impedance grid (0.0 to 1.0) with directional asymmetry notes.
  - Dimensional breakdown modal detailing memory models, type rigidity, overloads, and error handling with actionable compiler generator guidance.
- [x] **Visual Empirical Charts**:
  - Standard library surface area bar charts with callable density metrics.
  - Stacked parameter passing spectrum visualizer across all calling conventions.
  - State mutability boundary comparison highlighting compile-time constants and immutable fields.
  - Overload multiplicity and error handling paradigm side-by-side visualizers.
- [x] **Sub-Mode Switcher in Comparative Analytics**:
  - Seamless toggle between `[ 📈 Empirical Metrics & Impedance ]` and `[ 📖 Federated SQL Curriculum ]`.

#### Phase 3.3: Block & Function-Level AST Transpiler Engine (Delivered)
- [x] **Multi-Statement AST Transpiler Engine (`server/analysis/bridge_transpiler.py`)**:
  - Recursively lowers Python AST into C#, Rust, TypeScript, C++, and Go using verified relational signatures from `utss_universal_bridge.db`.
  - Normalizes collections (`list`, `dict`, `set`), control flow loops (`for ... in`, `while`), branching (`if/elif/else`), function definitions (`def ... -> ...`), context managers (`with open(...) as f:`), and exceptions (`raise Exc(...)`).
  - Emits idiomatic target code with deduplicated imports (`using`, `use`, `#include`, `import`).
- [x] **FastAPI Transpilation REST API (`POST /api/bridge/transpile`)**:
  - Accepts Python AST snippets and returns multi-target code emissions with verified catalog provenance records.
- [x] **Interactive Transpilation Sandbox & Provenance Inspector (`React_UI/src/components/transpiler/`)**:
  - Split-pane Monaco editor (Python source input on left, multi-target output tabs on right).
  - 4 curated canonical presets (Full Rosetta Suite, Collections & Sets, Control Flow & Loops, Function Signatures).
  - Empirical Catalog Provenance Inspector table tracking verified catalog signatures and pass semantics from `utss_universal_bridge.db`.
  - Sub-mode navigation in `Rosetta Playground` toggling between AST Transpiler Sandbox and Universal Concept Matrix.


---

### Phase 4: Long-Term Ecosystem Expansion
- [ ] **Extended Language Catalogs**: Java (OpenJDK 21+), Swift 6, Kotlin, Zig.
- [ ] **Curated Ecosystem Slices**: `python_ai_ml.db`, `cs_aspnet_full.db`, `rust_tokio_embedded.db`.
- [ ] **Classroom Assignment Packs & Query Grading**: Automated test assertions for grading student SQL solutions against expected output schemas.
