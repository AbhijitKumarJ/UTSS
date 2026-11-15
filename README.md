# UTSS: Universal Type & Symbol System

[![License: MIT with Exception](https://img.shields.io/badge/License-MIT%20w%2F%20Exception-blue.svg)](LICENSE)
[![Schemas: CC0-1.0](https://img.shields.io/badge/Schemas-CC0--1.0-brightgreen.svg)](LICENSE-GENERATED-OUTPUT.md)
[![Tests: All 152 Passing](https://img.shields.io/badge/tests-152%2F152%20passing-brightgreen.svg)](verify_all.sh)
[![Languages: 6](https://img.shields.io/badge/languages-Python%20%7C%20C%23%20%7C%20Rust%20%7C%20TypeScript%20%7C%20C%2B%2B%20%7C%20Go-orange.svg)]()

> **An empirical, zero-hallucination symbol cataloging, cross-language inventory, and transpilation ecosystem across 6 core programming languages into a standardized Dual-Layer Relational SQLite architecture.**

UTSS provides compiler frontends, language transpilers (such as Python-to-C# transpilers), and code-generation pipelines with an authoritative, cross-language symbol table that maps runtime behavior, static types, AST syntax nodes, and compiler IR primitives across languages.

---

## 🏛️ Monorepo Architecture

```text
UTSS/
├── LICENSE                      # MIT with UTSS Generated Output Exception
├── LICENSE-GENERATED-OUTPUT.md  # Explicit waiver: users own emitted .db & .g.cs files
├── THIRD_PARTY_NOTICES.md       # Upstream runtime, typeshed, & bundled library notices
├── CONTRIBUTING.md              # Inbound = Outbound contribution terms
├── harvest_all.sh               # Unified multi-language catalog harvester & bridge compiler
├── verify_all.sh                # Unified multi-language test verification runner
│
├── harvesters/                  # 6 Standalone Language Catalog Harvesters
│   ├── utss-python/             # Python 3.13+ runtime, site-packages, AST & typeshed
│   ├── utss-csharp/             # C# .NET 10 Roslyn syntax & CoreCLR BCL reflection
│   ├── utss-rust/               # Rust syn/quote AST & standard library harvester
│   ├── utss-typescript/         # TypeScript compiler API & ambient declaration stubs
│   ├── utss-cpp/                # ISO C++20 standard headers & lexical AST harvester
│   └── utss-go/                 # Go 1.27 go/parser, go/token & std harvester
│
├── schemas/                     # Central Relational SQL Schemas (CC0-1.0)
│   ├── python.sql               # Python 11-table DDL schema
│   ├── csharp.sql               # C# .NET 11-table DDL schema
│   ├── rust.sql                 # Rust 11-table DDL schema
│   ├── typescript.sql           # TypeScript 11-table DDL schema
│   ├── cpp.sql                  # C/C++ 11-table DDL schema
│   ├── go.sql                   # Go 11-table DDL schema
│   └── universal_bridge.sql     # Cross-language type mapping & symbol equivalence
│
└── workbench/                   # Universal Analysis, Synthesis & Transpiler Workbench
    ├── main.py                  # FastAPI server entrypoint (port 8000)
    ├── server/                  # Federated multi-DB engine, query loader, REST API
    ├── queries/                 # 48 Internals Lessons + 10 Comparative Synthesis Tracks
    ├── tools/                   # Universal bridge compiler, comparative analysis & C# bindgen
    ├── ui/                      # React 18 + Monaco Editor interactive studio
    ├── static/                  # Pre-compiled static assets (zero-build local serving)
    └── tests/                   # 93 automated test suites for workbench features
```

---

## 📊 Language Harvesters & Matrix

Every language harvester strictly enforces the **11-table Dual-Layer Relational Architecture**:
- **Layer 1 (Tables 1–9)**: Universal language-agnostic tables (`environments`, `distributions`, `containers`, `symbols`, `callables`, `callable_overloads`, `parameters`, `state_members`, `symbol_aliases`).
- **Layer 2 (Tables 10–11)**: Language fidelity facet tables (`*_container_facets`, `*_symbol_facets`).

| Language | Directory | Toolchain | Facet Tables (10 & 11) | Quick Link |
| :--- | :--- | :--- | :--- | :--- |
| **Python** | `harvesters/utss-python/` | Python 3.13+ (`uv` / `pytest`) | `py_container_facets`<br>`py_symbol_facets` | [utss-python](harvesters/utss-python/README.md) |
| **C# .NET** | `harvesters/utss-csharp/` | .NET 10 / Roslyn (`dotnet test`) | `cs_container_facets`<br>`cs_symbol_facets` | [utss-csharp](harvesters/utss-csharp/README.md) |
| **Rust** | `harvesters/utss-rust/` | Rust 1.85+ (`cargo test`) | `rust_container_facets`<br>`rust_symbol_facets` | [utss-rust](harvesters/utss-rust/README.md) |
| **TypeScript** | `harvesters/utss-typescript/` | Node 24+ / TS 5.7+ (`npm test`) | `ts_container_facets`<br>`ts_symbol_facets` | [utss-typescript](harvesters/utss-typescript/README.md) |
| **C/C++** | `harvesters/utss-cpp/` | ISO C++20 / g++ 13+ (`make test`) | `cpp_container_facets`<br>`cpp_symbol_facets` | [utss-cpp](harvesters/utss-cpp/README.md) |
| **Go** | `harvesters/utss-go/` | Go 1.27+ (`go test`) | `go_container_facets`<br>`go_symbol_facets` | [utss-go](harvesters/utss-go/README.md) |

---

## ⚡ Quickstart: Run All Tests

To verify that all 6 language harvesters and the workbench test clean:

```bash
# Clone the repository
git clone https://github.com/transpilers/UTSS.git
cd UTSS

# Run the unified test runner
./verify_all.sh
```

Sample output:
```text
==============================================================================
    UTSS MONOREPO VERIFICATION: ALL 6 LANGUAGE HARVESTERS + WORKBENCH        
==============================================================================

[Testing utss-python] Directory: harvesters/utss-python
✓ [utss-python] PASSED (36 tests)

[Testing utss-csharp] Directory: harvesters/utss-csharp
✓ [utss-csharp] PASSED (7 tests)

[Testing utss-rust] Directory: harvesters/utss-rust
✓ [utss-rust] PASSED (4 tests)

[Testing utss-typescript] Directory: harvesters/utss-typescript
✓ [utss-typescript] PASSED (4 tests)

[Testing utss-cpp] Directory: harvesters/utss-cpp
✓ [utss-cpp] PASSED (4 tests)

[Testing utss-go] Directory: harvesters/utss-go
✓ [utss-go] PASSED (4 tests)

[Testing utss-workbench] Directory: workbench/server
✓ [utss-workbench] PASSED (Bindgen + OLAP metrics)

==============================================================================
 [ALL PASSED] All 7 components verified successfully!
==============================================================================
```

---

## 🌾 Quickstart: Harvest Catalogs & Universal Bridge

To harvest local SQLite catalogs from your installed compilers and compile the Universal Bridge:

```bash
# Harvest all 6 languages + compile universal bridge
./harvest_all.sh

# Or harvest specific languages selectively
./harvest_all.sh python go rust
```

---

## 🛠️ Workbench & C# Code Generation

The workbench provides cross-database analytics and automated C# binding synthesis:

```bash
# Start the interactive Workbench UI & API server (port 8000)
cd workbench
uv run main.py

# Generate C# wrapper bindings from any harvested catalog:
python3 workbench/tools/utss_csharp_bindgen.py \
    --db harvesters/utss-python/catalog_base_full.db \
    --out UtssPackages.g.cs \
    --namespace MyProject.Bindings

# Run multi-catalog OLAP analytics:
python3 workbench/server/olap_pipeline.py
```

---

## 🗺️ Next Phase: Domain-Specific Ecosystems

UTSS is designed to expand beyond standard libraries to provide dedicated comparative tracks and on-demand harvesting for:
- **Tabular Data & DataFrames:** Pandas, Polars, `Microsoft.Data.Analysis`
- **Tensors & N-D Arrays:** PyTorch, NumPy, `System.Numerics.Tensors`, TorchSharp, Candle
- **Machine Learning Pipelines:** Scikit-learn, ML.NET (`Microsoft.ML`), Linfa
- **NLP & Tokenization:** Hugging Face `tokenizers`, `Microsoft.ML.Tokenizers`
- **Scientific Visualization:** Matplotlib, `Plotly.NET`, ScottPlot, Plotters
- **Quantum Computing:** Qiskit, Cirq, PennyLane, Microsoft Q# / QDK

See [docs/NEXT_PHASE_DOMAIN_EXPANSION_PLAN.md](docs/NEXT_PHASE_DOMAIN_EXPANSION_PLAN.md) for the complete post-publishing architectural specification.

---

## ⚖️ Open-Source Licensing & Generated Output Waiver

UTSS is 100% open-source software under the **MIT License** with the **UTSS Generated Output Exception**:

> **UTSS GENERATED OUTPUT EXCEPTION**  
> *As an additional permission, any output files generated by executing the Software—including SQLite catalog databases (`*.db`), universal bridge databases, Parquet/Arrow exports, and generated source code bindings (such as `*.g.cs`, `*.rs`, `*.go`, `*.ts`, or `*.cpp` files)—are not considered copies or substantial portions of the Software. Users may distribute, modify, and license such generated outputs under any license terms of their choice without restriction or attribution requirements.*

- **Your Generated Code is Yours:** You own 100% of emitted `.db` catalogs and `.g.cs` bindings without notice propagation or copyleft requirements.
- **Relational Schemas in Public Domain:** All `.sql` DDL definitions in `schemas/` are dedicated to the Public Domain under **CC0-1.0**.

See [LICENSE](LICENSE) and [LICENSE-GENERATED-OUTPUT.md](LICENSE-GENERATED-OUTPUT.md) for full legal text.
