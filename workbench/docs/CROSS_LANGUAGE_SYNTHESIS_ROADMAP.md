# Cross-Language Synthesis & Universal Bridge: Phased Development Roadmap

This document synthesizes the strategic and technical vision from:
- `docs/Ideas/cross lang and analysis plans.md`
- `docs/Ideas/cross lang analysis 2.md`
- `docs/Ideas/cross lang universal bridge 3.md`

It lays out the phased roadmap to transform the **Universal Type and Symbol System (UTSS)** from isolated single-language AST catalogs into an empirical **Cross-Language Synthesis, Impedance Analysis & Universal Bridge Engine**.

---

## 1. Executive Summary & Core Paradigm

The 6 language catalogs in `dbs/` (Python, C#, C++, Go, Rust, TypeScript) share an identical **Layer 1 Universal Core** schema:
- `environments`
- `distributions` (Strata 0 to 3)
- `containers`
- `symbols`
- `callables`
- `callable_overloads`
- `parameters`
- `state_members`
- `symbol_aliases`

Beside this core sit the **Layer 2 Language-Fidelity Facet** tables (`py_symbol_facets`, `cs_container_facets`, `cpp_symbol_facets`, `rust_symbol_facets`, `go_container_facets`, `ts_symbol_facets`).

By treating all 6 catalogs as a **federated multi-language dataset**, we can:
1. **Quantify Impedance Mismatches**: Measure how parameter passing, mutability, function overloading, and protocol mechanics differ mathematically across language ecosystems.
2. **Build an Empirical Rosetta Stone**: Compile a verified bridge database (`utss_universal_bridge.db`) mapping universal compiler IR concepts (primitives, dynamic arrays, hash maps, result/option wrappers, iteration protocols) to exact stdlib symbols and signatures in all 6 targets.
3. **Power Unified Transpilation**: Provide the exact lookup and lowering rules needed for high-fidelity code generators and transpilers.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           THE THREE-STAGE SYNTHESIS PIPELINE                    │
├─────────────────────────┬───────────────────────────┬───────────────────────────┤
│ Stage 1: Federated SQL  │ Stage 2: Data Science     │ Stage 3: Universal Bridge │
│ Workbench (Exploration) │ Profiling (Quantification)│ Engine (Codification)     │
│                         │                           │                           │
│ • ATTACH 6 Databases    │ • utss_comparative_       │ • build_bridge_db.py      │
│ • v_all_* Master Views  │   analysis.py             │ • utss_universal_bridge.db│
│ • 10-Lesson Cross-Lang  │ • 5 Empirical PNG Charts  │ • Concept, Type, Op &     │
│   Curriculum (4 Tracks) │ • Rosetta CSV Exports     │   Protocol Mappings       │
│ • Live Monaco Execution │ • Impedance Metrics       │ • Transpilation Lowering  │
└─────────────────────────┴───────────────────────────┴───────────────────────────┘
```

---

## 2. Phased Development Plan

The development is divided into **four discrete phases**, each delivering verifiable milestones.

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                               PHASED EXECUTION MATRIX                           │
├──────────────┬────────────────────────────────────────────────┬─────────────────┤
│ Phase        │ Focus Area                                     │ Key Deliverable │
├──────────────┼────────────────────────────────────────────────┼─────────────────┤
│ Phase 2.1    │ Federated Engine & Cross-Language Curriculum   │ In-memory ATTACH│
│              │ • Backend Multi-DB ATTACH & Unified Views      │ master views &  │
│              │ • 10 Cross-Language Lessons across 4 Tracks    │ 10 new queries  │
│              │ • Frontend Comparative Analytics Tab Activation│ in React UI     │
├──────────────┼────────────────────────────────────────────────┼─────────────────┤
│ Phase 2.2    │ Automated Data Science & Impedance Profiling   │ Matplotlib &    │
│              │ • Pipeline in server/analysis/comparative.py   │ Seaborn suite,  │
│              │ • 5 Empirical Visualizations & Metrics CSVs    │ REST endpoints, │
│              │ • Interactive Dashboard in React UI            │ visual metrics  │
├──────────────┼────────────────────────────────────────────────┼─────────────────┤
│ Phase 2.3    │ The Universal Bridge Database & Rosetta Engine │ Automated DB    │
│              │ • Automated Populator (build_bridge_db.py)     │ populator,      │
│              │ • dbs/utss_universal_bridge.db Generation      │ 5 bridge tables,│
│              │ • Rosetta Translation API (/api/bridge/*)      │ Bridge queries  │
├──────────────┼────────────────────────────────────────────────┼─────────────────┤
│ Phase 2.4    │ Visual AST Graph & Transpilation Playground    │ Side-by-side    │
│              │ • Interactive Rosetta Concept Cards in React   │ IR explorer &   │
│              │ • Cytoscape/D3 Container Graph Visualizer      │ Transpilation   │
│              │ • Transpilation Signature Verification Sandbox │ sandbox         │
└──────────────┴────────────────────────────────────────────────┴─────────────────┘
```

---

## 3. Phase 2.1: Federated Multi-Database Engine & Cross-Language Curriculum

### 3.1 Objective
Provide a single unified query target where students and researchers can query across all 6 language databases simultaneously in the Monaco SQL Runner without manual `UNION ALL` or cross-file joins.

### 3.2 Backend Implementation
1. **Multi-Database SQLite Federation in `DatabaseManager` (`server/db_manager.py`)**:
   - Register virtual database targets:
     - `federated_recommended`: In-memory SQLite connection attaching `cpp_recommended`, `cs_recommended`, `go_recommended`, `python_recommended`, `rust_recommended`, `ts_recommended`.
     - `federated_full`: Attaches the full/base_full variants of all 6 catalogs.
   - On initialization of the connection, execute SQLite attachments:
     ```sql
     ATTACH DATABASE 'file:dbs/python_recommended.db?mode=ro' AS py;
     ATTACH DATABASE 'file:dbs/cs_recommended.db?mode=ro' AS cs;
     ATTACH DATABASE 'file:dbs/cpp_recommended.db?mode=ro' AS cpp;
     ATTACH DATABASE 'file:dbs/go_recommended.db?mode=ro' AS go;
     ATTACH DATABASE 'file:dbs/rust_recommended.db?mode=ro' AS rust;
     ATTACH DATABASE 'file:dbs/ts_recommended.db?mode=ro' AS ts;
     ```
   - Automatically compile in-memory convenience views:
     - **`v_all_containers`**: Unions `containers` across all 6 databases with `language`, `dist_name`, `stratum`.
     - **`v_all_symbols`**: Unions `symbols` across all 6 databases with `language`, `symbol_kind`, `visibility`.
     - **`v_all_callables`**: Unions `callables` across all 6 databases joined with `symbols` and `environments`.
     - **`v_all_parameters`**: Unions `parameters` across all 6 databases with `pass_kind`, `type_expr`.

2. **Cross-Language Curriculum (10 Progressive Lessons in `queries/comparative/`)**:
   Organized across 4 core structural transpiler tracks:
   - **Track I: Scope & Packaging**:
     - *Lesson 1*: The Ambient Baseline (Stratum 0 Globals & Zero-Import Surface).
     - *Lesson 2*: Namespace Topology, Nesting Depth & Re-Export Facades.
   - **Track II: Memory & Parameter Passing**:
     - *Lesson 3*: Parameter Passing & Ownership Matrix (Val vs Ref vs Pointer vs Move).
     - *Lesson 4*: Mutability Guarantees: Default Immutability vs Explicit Modifiers.
   - **Track III: Polymorphism & Contracts**:
     - *Lesson 5*: Static Overload Multiplicity vs Dynamic Dispatch.
     - *Lesson 6*: Structural Duck Typing vs Nominal Interface Contracts.
     - *Lesson 7*: Generic Type Parameters & Bound Constraints.
   - **Track IV: Execution & Safety**:
     - *Lesson 8*: Async Coroutines, State Machines & Event Loop Mechanics.
     - *Lesson 9*: Error Handling Paradigms: Exceptions vs Algebraic Result Types.
     - *Lesson 10*: The Rosetta Crosswalk (Canonical Sequence & Map Equivalents).

3. **Frontend React UI Activation**:
   - Enable the **Comparative Analytics** tab in `TopNav`.
   - When active, the sidebar loads the 10 cross-language lessons.
   - The database selector automatically defaults to `Federated Multi-DB (Recommended)` with badge `6 LANGUAGES FEDERATED`.

---

## 4. Phase 2.2: Automated Data Science & Impedance Profiling Suite

### 4.1 Objective
Transform empirical database data into quantified statistical distributions and high-resolution visualizations that reveal structural laws governing language design and transpilation complexity.

### 4.2 Implementation
1. **Research Suite Module (`server/analysis/comparative_analysis.py`)**:
   - Port the comprehensive script from `docs/Ideas/cross lang analysis 2.md` into the platform backend.
   - Connects in read-only mode to all 6 databases using standard `pandas`, `matplotlib`, and `seaborn`.
   - Generates 5 analytical figures in `static/analysis/`:
     - **Figure 1 (`01_strata_and_depth.png`)**: Log-scale Stratum 0 vs Stratum 1 symbol counts and boxplot of container nesting depth (`parent_container_id` recursion).
     - **Figure 2 (`02_parameter_passing_spectrum.png`)**: 100% stacked horizontal bar chart of parameter pass kinds (`val`, `ref`, `mut_ref`, `const_ref`, `pointer`, `out`, `variadic`).
     - **Figure 3 (`03_arity_defaults_overloads.png`)**: Arity distributions, default argument percentages, and overload counts.
     - **Figure 4 (`04_mutability_and_typing.png`)**: State mutability proportions and static type annotation completeness.
     - **Figure 5 (`05_layer2_facets_and_protocols.png`)**: Method receiver mechanics (`self_kind`, `receiver_kind`, `is_const`) and Python dunder alignment to target language interfaces.
   - Exports CSV summaries:
     - `analysis_output/rosetta_sequence_crosswalk.csv`
     - `analysis_output/summary_metrics.csv`

2. **FastAPI Endpoints (`server/routes.py`)**:
   - `GET /api/analysis/summary`: Returns precomputed comparative metrics as JSON.
   - `POST /api/analysis/run`: Triggers a background recalculation of the analysis suite.
   - `GET /api/analysis/figures/{figure_name}`: Streams generated analysis charts.

3. **React UI Analytics View**:
   - Add a sub-view in the Comparative Analytics mode to view the interactive metrics table and preview the generated figures with zoom and download capabilities.

---

## 5. Phase 2.3: The Universal Bridge Database & Rosetta Engine

### 5.1 Objective
Codify cross-language relationships into an automated, verified SQLite database (`dbs/utss_universal_bridge.db`) that maps language-agnostic compiler IR concepts directly to concrete symbols and signatures across all 6 targets.

### 5.2 Implementation
1. **Automated Bridge Populator (`server/analysis/build_bridge_db.py`)**:
   - Port the 4-pass scanner from `docs/Ideas/cross lang universal bridge 3.md`.
   - **Pass 1: Concept & Type Resolution**: Resolves universal concepts (primitives, collections, control flow, exceptions, I/O, protocols) to target types.
   - **Pass 2: Operation & Signature Binding**: Resolves operations (`append`, `push`, `get`, `set`, `len`, `clear`) against live `callables` and `parameters`.
   - **Pass 3: Protocol & Contract Verification**: Verifies protocol implementations (`iteration`, `resource_cleanup`, `comparison`) against facet tables.
   - **Pass 4: Autonomous Stdlib Taxonomist**: Harvests all unmapped collections, exceptions, and streams into `discovered_stdlib_taxonomy`.
   - Writes `dbs/utss_universal_bridge.db` with 5 relational tables:
     1. `universal_concepts`
     2. `universal_type_mappings`
     3. `universal_operation_mappings`
     4. `universal_protocol_mappings`
     5. `discovered_stdlib_taxonomy`

2. **Catalog Registration**:
   - `DatabaseManager` discovers and registers `utss_universal_bridge` in the database dropdown.
   - Author a dedicated curriculum track (`queries/bridge/`) with lessons exploring concept lowering, syntax templates, and memory model impedance.

3. **Bridge REST API**:
   - `GET /api/bridge/concepts`: Returns all canonical compiler IR concepts.
   - `GET /api/bridge/lookup?concept={concept_key}`: Returns the complete 6-language crosswalk (target types, syntax templates, memory models, and method signatures).
   - `GET /api/bridge/translate?source_lang={s}&target_lang={t}&symbol={qname}`: Translates a concrete symbol in Language A to its equivalent in Language B.

---

## 6. Phase 2.4: Interactive Visual Transpilation & AST Sandbox

### 6.1 Objective
Provide an interactive visual environment in the React workbench for browsing the Rosetta Stone, inspecting container and inheritance graphs, and testing transpilation rules.

### 6.2 Implementation
1. **Rosetta Concept Explorer Component (`React_UI/src/components/RosettaExplorer.tsx`)**:
   - Interactive card-grid where selecting a concept (e.g. `collection.dynamic_array`) renders a 6-column matrix:
     - **Python**: `builtins.list[T]` | `ref_gc` | `append(x)` | `[x]`
     - **C#**: `System.Collections.Generic.List<T>` | `ref_gc` | `Add(item)` | `[i]`
     - **C++**: `std::vector<T>` | `value_stack` | `push_back(val)` | `[i]`
     - **Go**: `[]T` | `slice_header` | `append(s, x)` | `s[i]`
     - **Rust**: `alloc::vec::Vec<T>` | `owned_heap` | `push(val)` | `[i]`
     - **TypeScript**: `Array<T>` | `ref_gc` | `push(item)` | `[i]`
2. **Container & Type Hierarchy Graph**:
   - Lightweight interactive node-link graph (using Cytoscape.js or SVG) visualizing module hierarchies, class inheritance (`extends`), and interface implementations.
3. **Transpilation Verification Sandbox**:
   - Side-by-side Monaco editors: input code in Language A, view IR lowering and translated syntax in Language B, backed by verified signatures from `utss_universal_bridge.db`.

---

## 7. Immediate Next Steps & Milestones

1. **Step 1**: Implement Phase 2.1 Backend SQLite Federation (`v_all_*` views in `DatabaseManager`).
2. **Step 2**: Author the 10 Cross-Language Curriculum queries in `queries/comparative/`.
3. **Step 3**: Integrate `utss_comparative_analysis.py` into `server/analysis/` and verify chart generation.
4. **Step 4**: Integrate `build_bridge_db.py` to generate `dbs/utss_universal_bridge.db`.
5. **Step 5**: Update the React UI to surface the Comparative Analytics dashboard and Rosetta explorer.
