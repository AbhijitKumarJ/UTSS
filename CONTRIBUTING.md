# Contributing to UTSS

Thank you for your interest in contributing to the **Universal Type & Symbol System (UTSS)**!

UTSS is designed as an empirical, zero-hallucination inventory, symbol cataloging, and cross-language transpilation engine. It powers multi-language code generation across 6 core language ecosystems: Python, C#, Rust, TypeScript, C/C++, and Go.

---

## 1. Core Engineering Principles

1. **Strict Relational Schema Symmetry**:
   - Universal tables (1–9) must remain completely language-agnostic compiler IR concepts.
   - Language-specific mechanics must be isolated in respective Facet tables (10–11).
2. **Safe Static Parsing for User Code**:
   - Stratum 3 workspace harvesting must **never execute user code**. User modules must be parsed exclusively via pure AST/lexical analysis.
3. **Hardened Introspection & Reflection**:
   - Reflection code must be resilient against runtime quirks, macro expansions, and native extension limitations.
4. **Generated Output Freedom**:
   - All emitted bindings and catalog databases belong 100% to the end user under the UTSS Generated Output Exception.

---

## 2. Monorepo Repository Structure

```text
UTSS/
├── harvesters/
│   ├── utss-python/             # Python 3.13+ runtime & typeshed harvester
│   ├── utss-csharp/             # C# .NET 10 Roslyn & BCL reflection harvester
│   ├── utss-rust/               # Rust syn/quote AST & standard library harvester
│   ├── utss-typescript/         # TypeScript compiler API harvester
│   ├── utss-cpp/                # C/C++ ISO C++20 standard header & AST harvester
│   └── utss-go/                 # Go 1.27 go/parser, go/token & std harvester
├── schemas/                     # Core 11-table DDL schemas & universal_bridge.sql
└── workbench/                   # FastAPI backend, React UI, OLAP pipeline & C# bindgen
```

---

## 3. Running Test Suites

Verify all 6 language harvesters locally using the top-level verification script:
```bash
bash verify_all.sh
```

Or test individual harvesters:
- **Python:** `cd harvesters/utss-python && uv run pytest`
- **C#:** `cd harvesters/utss-csharp && dotnet test UTSS.CSharp.slnx`
- **Rust:** `cd harvesters/utss-rust && cargo test`
- **TypeScript:** `cd harvesters/utss-typescript && npm test`
- **C/C++:** `cd harvesters/utss-cpp && make test`
- **Go:** `cd harvesters/utss-go && go test -v ./tests`

---

## 4. Inbound = Outbound Licensing Terms

By contributing to UTSS, you agree that your contributions will be licensed under the project's software license.

> **Inbound = Outbound Clause:**  
> Unless you explicitly state otherwise, any contribution intentionally submitted for inclusion in UTSS by you shall be licensed under the **MIT License with the UTSS Generated Output Exception**, without any additional terms or conditions.

All SQL schema definitions contributed to the `schemas/` directory are dedicated to the Public Domain under **CC0-1.0**.
