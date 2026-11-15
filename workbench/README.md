# UTSS Universal Language Analysis, Synthesis & Transpiler Workbench

An extensible, interactive web workbench, pedagogical research tool, and transpilation engine powered by the **Universal Type and Symbol System (UTSS)**.

The platform enables students, engineers, and compiler authors to explore programming language internals (CPython, .NET C#, C++20, Go, Rust, and TypeScript), test custom SQL queries against deeply indexed AST and symbol databases, perform cross-language comparative analysis, and synthesize strongly-typed C# bindings.

---

## 🌟 Key Features

1. **Multi-Language Interactive Internals Tutor (48 Lessons)**:
   - Dedicated progressive curricula for **Python**, **C#**, **C++**, **Go**, **Rust**, and **TypeScript** (6 to 8 lessons per language).
   - **Cross-Language Synthesis Curriculum (10 Lessons)**: In-depth comparative tracks covering Scope & Packaging, Memory & Passing, Polymorphism & Contracts, and Execution & Safety.
   - Each lesson includes a **Tutor Rationale ("Why This Query Matters")** explaining compiler/runtime mechanics, and **Guided Experiments** encouraging students to explore the schema.
   - Interactive SQL editor powered by **Monaco Editor** with `Ctrl+Enter` execution shortcuts, local asset bundling (offline/intranet safe), copy SQL, and reset options.
   - Ergonomic anti-squish layout with collapsible Tutor Notes, sticky table headers, `NULL` representation badges, and client-side RFC 4180 CSV export.

2. **Multi-Database Federation & Universal Bridge Engine**:
   - Supports 6 programming languages across two tiers of databases (Curated Starting Points and Full Standard Libraries).
   - **Federated Multi-DB Engine (`federated_recommended` & `federated_full`)**: Mounts all 6 catalogs concurrently with SQLite in-memory temporary views (`v_all_symbols`, `v_all_containers`, `v_all_callables`, `v_all_parameters`, `v_all_environments`, `v_all_distributions`, `v_all_state_members`, `v_all_symbol_aliases`).
   - **Universal Transpilation Bridge (`dbs/utss_universal_bridge.db`)**: 4-pass compiled bridge linking canonical compiler IR concepts (primitives, collections, control flow, exceptions, I/O streams, protocols) to empirical target types and signatures.
   - **Empirical Analysis CLI (`tools/utss_comparative_analysis.py`)**: Computes multi-language censuses, mutability metrics, parameter passing distributions, overload multiplicities, and pairwise transpiler impedance matrices.
   - **Automated C# Binding Generator (`tools/utss_csharp_bindgen.py`)**: Automatically synthesizes strongly-typed C# wrapper classes and invoker stubs (`UtssPackages.g.cs`) from any catalog.

3. **Multi-Theme Engine**:
   - 4 built-in themes: **UTSS Slate Dark**, **VS Code Dark+**, **VS Code Light+**, and **Monokai**.
   - Custom Monaco theme token definitions synchronized with CSS custom properties.
   - FOUC-prevention script restoring theme preferences from `localStorage` before render.

4. **Modular Query Architecture**:
   - Curriculum lessons live as clean, modular `.sql` files with YAML frontmatter headers under `queries/<language>/tutoring/`.
   - Adding or modifying a `.sql` file makes it instantly accessible in the UI without server restarts.

5. **Safe Read-Only Execution Engine**:
   - SQLite opened strictly in read-only URI mode (`file:{path}?mode=ro&immutable=1`).
   - Query filter strictly permitting `SELECT`, `WITH`, and `EXPLAIN` (disallowing DDL/DML while preserving string literal keywords).
   - Progress handler execution timeout (5.0s) protecting against runaway queries.
   - Single-pass 500-row preview limit with truncation indicators.

---

## 🚀 Quick Start

Start the FastAPI application:

```bash
cd workbench
uv run main.py
```

Or via Uvicorn:

```bash
cd workbench
uv run uvicorn main:app --reload --port 8000
```

Open your browser to:
**http://localhost:8000**

### Frontend Development (Optional)

The frontend is a client-only React 18 + TypeScript SPA inside `ui/` that compiles its production bundle directly into `static/`:

```bash
cd ui
npm install        # install dependencies
npm run dev        # start local Vite dev server at http://localhost:5173 (proxies /api to :8000)
npm run build      # cleans static/assets and builds production bundle to ../static
```

---

## 📁 Directory Structure

```text
workbench/
├── dbs/                                  # Symlinked multi-language SQLite databases (pointing to harvesters/)
│   ├── cpp_recommended.db / cpp_full.db  # C++20 ISO types, libstdc++, commerce_engine
│   ├── cs_recommended.db / cs_base_full  # .NET 10 CoreCLR BCL, readonly/ref structs, commerce_engine
│   ├── go_recommended.db / go_full.db    # Go 1.27 predeclared builtins, std packages
│   ├── python_recommended.db / base_full # CPython 3.13 stdlib, dunders, MRO, third-party packages
│   ├── rust_recommended.db / base_full   # Rust 1.85 prelude, crates, traits, syn AST
│   ├── ts_recommended.db / ts_full.db    # TypeScript 5.9 / Node 24 ambient globals, utility types
│   └── utss_universal_bridge.db          # 4-pass compiled universal transpilation bridge
├── queries/                              # Modular curriculum query files (48+ lessons)
│   ├── cpp/tutoring/                     # C++ progressive lessons
│   ├── csharp/tutoring/                  # C# progressive lessons
│   ├── go/tutoring/                      # Go progressive lessons
│   ├── python/tutoring/                  # Python progressive lessons
│   ├── rust/tutoring/                    # Rust progressive lessons
│   ├── typescript/tutoring/              # TypeScript progressive lessons
│   └── comparative/                      # Cross-language comparative analytics queries
├── tools/                                # Transpiler & Analysis CLI tools
│   ├── build_universal_bridge.py         # 4-pass universal bridge compiler
│   ├── utss_comparative_analysis.py      # Typing census & impedance matrices
│   └── utss_csharp_bindgen.py            # Strongly-typed C# binding generator
├── ui/                                   # Client-only React 18 + TypeScript + Vite project (from React_UI)
├── server/                               # FastAPI backend services
│   ├── config.py                         # App configuration and directory paths
│   ├── db_manager.py                     # Multi-DB discovery & safe read-only SQL executor
│   ├── query_loader.py                   # YAML frontmatter parser and query tree indexer
│   ├── routes.py                         # FastAPI REST endpoints & streaming CSV exporter
│   └── analysis/                         # Extension foundation for Pandas / comparative pipelines
├── static/                               # Compiled web frontend assets served by FastAPI
├── docs/                                 # Architectural documentation and roadmap
└── tests/                                # Automated pytest test suite (93 passing tests)
```

---

## ⚖️ Licensing & Generated Output Waiver
- Workbench code is licensed under the **MIT License**.
- **Important:** As specified in [LICENSE-GENERATED-OUTPUT.md](../LICENSE-GENERATED-OUTPUT.md), all output files emitted by the workbench and bindgen tools (such as `*.g.cs` files, bridge databases, and Parquet exports) are 100% owned by the user and free from any licensing restrictions or attribution mandates.

---

## 🗺️ Roadmap & Next Steps

See the comprehensive specifications in `docs/`:
- **[docs/CROSS_LANGUAGE_SYNTHESIS_ROADMAP.md](docs/CROSS_LANGUAGE_SYNTHESIS_ROADMAP.md)**: Full 4-phase master execution plan.
- **[docs/SPEC_CROSS_LANGUAGE_CURRICULUM.md](docs/SPEC_CROSS_LANGUAGE_CURRICULUM.md)**: Complete 10-lesson cross-language curriculum with exact SQL queries.
- **[docs/SPEC_UNIVERSAL_BRIDGE_SCHEMA.md](docs/SPEC_UNIVERSAL_BRIDGE_SCHEMA.md)**: Universal Bridge database DDL schema and 4-pass automated populator.

### Current Implementation & Active Roadmap
- **Phase 1 (Delivered)**: Core FastAPI backend, multi-DB catalog discovery, safe read-only execution engine, React 18 + Monaco Editor workbench with 4 themes, comprehensive curricula for all 6 languages (48 lessons).
- **Phase 2.1 (Delivered)**: Multi-database SQLite federation (`v_all_*` master views via `:memory:` multi-db `ATTACH`), 10 cross-language comparative lessons across 4 tracks, and React UI "Comparative Analytics" tab activation.
- **Phase 2.2 (Delivered)**: Automated comparative data science suite (`tools/utss_comparative_analysis.py`), generating empirical impedance matrices, typing censuses, and cross-language mutability reports.
- **Phase 2.3 (Delivered)**: Universal Bridge database (`dbs/utss_universal_bridge.db`), compiled via 4-pass scanner in `tools/build_universal_bridge.py` with `/api/bridge/*` REST endpoints and `/api/bindgen/csharp` synthesis.
- **Phase 2.4 (Delivered)**: Interactive Rosetta matrix explorer and transpilation sandbox verified by 93 automated tests.
- **Next Phase (Planned)**: Domain-specific ecosystem expansion (DataFrames, Tensors, ML Pipelines, NLP Tokenizers, Scientific Visualization, Quantum Computing) and on-demand local harvesting. See [docs/NEXT_PHASE_DOMAIN_EXPANSION_PLAN.md](../docs/NEXT_PHASE_DOMAIN_EXPANSION_PLAN.md).

---

## 🧪 Running the Tests

To run the complete automated test suite (including verification of all 39 queries across both recommended and full database variants):

```bash
uv run pytest -v
```
