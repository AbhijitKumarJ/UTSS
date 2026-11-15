# UTSS Rust - Universal Type & Symbol System Cataloger

An implementation of the **Universal Type & Symbol System (UTSS)** for **Rust**, providing cross-language relational type and symbol introspection across Strata 0–3 using the standardized 11-table SQLite catalog architecture.

---

## 1. Dual-Layer Relational Architecture

The SQLite catalog maintains strict structural parity with universal UTSS standards:

### Layer 1: Universal Language-Agnostic Core Tables (1–9)
| # | Table Name | Purpose |
|---|------------|---------|
| 1 | `environments` | Host platform triplet (`linux-x86_64`), runtime (`rustc`), language version (`1.85.0`). |
| 2 | `distributions` | Strata packaging units (`<ambient>`, `std`, `commerce_engine`). |
| 3 | `containers` | Hierarchy: `ambient_scope`, `crate`, `module`, `struct`, `enum`, `trait`. |
| 4 | `symbols` | Functions, methods, struct fields, enum variants, constants, keywords, macros. |
| 5 | `callables` | Signature metadata, `is_async`, `is_static`, `return_type_expr`, `raw_signature`. |
| 6 | `callable_overloads` | Trait implementations and polymorphic macro variants. |
| 7 | `parameters` | Parameter names, pass kinds (`val`, `ref`, `mut_ref`, `self_val`, `self_ref`, `self_mut_ref`). |
| 8 | `state_members` | Struct fields, constants, statics, access modes (`read_only`, `read_write`). |
| 9 | `symbol_aliases` | Re-exports (`pub use a::b;`), use aliases, and prelude imports. |

### Layer 2: Rust Fidelity Facet Tables (10–11, 1:1 with Core)
| # | Table Name | Purpose |
|---|------------|---------|
| 10 | `rust_container_facets` | `item_kind` (`struct`, `enum`, `trait`, `union`, `module`, `crate`), `is_pub`, `is_unsafe`, `is_auto_trait`, `generics_json`, `where_clause_json`, `attributes_json`. |
| 11 | `rust_symbol_facets` | `member_kind` (`fn`, `method`, `associated_fn`, `const`, `static`, `variant`, `field`, `macro`), `is_const`, `is_async`, `is_unsafe`, `self_kind` (`none`, `val`, `ref`, `mut_ref`), `visibility`. |

---

## 2. Strata Architecture

- **Stratum 0 (Ambient Scope)**:
  - 51 Keywords (38 strict keywords + 13 reserved/future keywords).
  - 22 Primitive Types (`bool`, `char`, `str`, integer types `i8`..`u128`, floats `f32`/`f64`, `never`, `slice`, `array`, `tuple`).
  - Standard Prelude Items: Core types (`Option`, `Some`, `None`, `Result`, `Ok`, `Err`, `Box`, `String`, `Vec`), fundamental traits (`Clone`, `Copy`, `Debug`, `Default`, `Eq`, `Iterator`, `Send`, `Sync`, etc.), and standard macros (`println!`, `format!`, `panic!`, `assert!`, `vec!`, `dbg!`).
- **Stratum 1 (Standard Library Distribution)**:
  - Curated Tier-1 Profile: Primary collections (`HashMap`, `HashSet`, `Vec`), IO (`Read`, `Write`), FS (`File`), Path (`PathBuf`), Sync (`Arc`, `Mutex`), Time, Thread.
  - Full Profile: 44 standard library modules (`std::collections`, `std::io`, `std::sync`, etc.) and their types, functions, and trait items.
- **Stratum 3 (Workspace Source AST)**:
  - **Pure static AST parsing** via `syn` and `proc-macro2`.
  - Zero dynamic code execution.
  - Exact source coordinates: `start_line`, `start_col`, `end_line`, `end_col`.
  - Receiver analysis: extracts receiver pass kind (`&self` $\to$ `ref`, `&mut self` $\to$ `mut_ref`, `self` $\to$ `val`, none $\to$ `associated_fn`).
  - Struct fields, enum variants, trait declarations, `impl` blocks, and `use` re-exports.
  - Embedded self-contained demo workspace: `commerce_engine`.

---

## 3. CLI Usage

### Build & Test
```bash
cargo build
cargo test
```

### Harvest Metadata
```bash
# Recommended synthesis profile (Curated Tier-1 std + Ambient + Workspace)
cargo run -- harvest --db catalog_rust_recommended.db --reset --stratum0 --std-recommended --demo-workspace

# Full standard library distribution
cargo run -- harvest --db catalog_rust_full.db --reset --stratum0 --std-full --demo-workspace

# Harvest custom workspace
cargo run -- harvest --db catalog_rust.db --workspace /path/to/rust/crate
```

### Diagnostic Catalog Report
```bash
cargo run -- report --db catalog_rust_recommended.db
```

### Diagnostic Queries
```bash
# Query ambient keywords, primitives, prelude items, and macros
cargo run -- query --db catalog_rust_recommended.db --ambient

# Query standard library item breakdown
cargo run -- query --db catalog_rust_full.db --std-summary

# Query workspace symbols with exact AST line/col coordinates
cargo run -- query --db catalog_rust_recommended.db --workspace-symbols

# Query Rust Container & Symbol Facets (generics, attributes, self_kind)
cargo run -- query --db catalog_rust_recommended.db --facets
```

### Automated Dual-Profile Script
```bash
# Runs both Recommended & Full Base Catalog generation + deep analysis queries:
./script.sh
```
