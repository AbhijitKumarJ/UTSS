# UTSS Universal Relational Schemas across 6 Languages

This directory contains the exported SQL schemas for the full standard library distribution catalogs across all **6 supported language implementations** in the **Universal Type & Symbol System (UTSS)**.

---

## 1. Schema Matrix & Export File Mapping

| Language | Working Folder | Local Schema File | Central Schema File | Full Catalog Database |
| :--- | :--- | :--- | :--- | :--- |
| **Python** | `harvesters/utss-python/` | [`harvesters/utss-python/schema.sql`](file:///home/abhijit/Videos/transpilers/UTSS/harvesters/utss-python/schema.sql) | [`schemas/python.sql`](file:///home/abhijit/Videos/transpilers/UTSS/schemas/python.sql) | `harvesters/utss-python/catalog_base_full.db` |
| **C# .NET** | `harvesters/utss-csharp/` | [`harvesters/utss-csharp/schema.sql`](file:///home/abhijit/Videos/transpilers/UTSS/harvesters/utss-csharp/schema.sql) | [`schemas/csharp.sql`](file:///home/abhijit/Videos/transpilers/UTSS/schemas/csharp.sql) | `harvesters/utss-csharp/catalog_cs_full.db` |
| **Rust** | `harvesters/utss-rust/` | [`harvesters/utss-rust/schema.sql`](file:///home/abhijit/Videos/transpilers/UTSS/harvesters/utss-rust/schema.sql) | [`schemas/rust.sql`](file:///home/abhijit/Videos/transpilers/UTSS/schemas/rust.sql) | `harvesters/utss-rust/catalog_rust_full.db` |
| **TypeScript** | `harvesters/utss-typescript/` | [`harvesters/utss-typescript/schema.sql`](file:///home/abhijit/Videos/transpilers/UTSS/harvesters/utss-typescript/schema.sql) | [`schemas/typescript.sql`](file:///home/abhijit/Videos/transpilers/UTSS/schemas/typescript.sql) | `harvesters/utss-typescript/catalog_ts_full.db` |
| **C/C++** | `harvesters/utss-cpp/` | [`harvesters/utss-cpp/schema.sql`](file:///home/abhijit/Videos/transpilers/UTSS/harvesters/utss-cpp/schema.sql) | [`schemas/cpp.sql`](file:///home/abhijit/Videos/transpilers/UTSS/schemas/cpp.sql) | `harvesters/utss-cpp/catalog_cpp_full.db` |
| **Go** | `harvesters/utss-go/` | [`harvesters/utss-go/schema.sql`](file:///home/abhijit/Videos/transpilers/UTSS/harvesters/utss-go/schema.sql) | [`schemas/go.sql`](file:///home/abhijit/Videos/transpilers/UTSS/schemas/go.sql) | `harvesters/utss-go/catalog_go_full.db` |

---

## 2. Universal Schema Architecture (11 Tables)

Every database catalog adheres strictly to the dual-layer relational architecture:

### Layer 1: Universal Language-Agnostic Core Tables (1–9)
Common to all 6 languages with identical primary keys, foreign keys, and cascading relationships:
1. `environments`: Host platform triplet, runtime implementation, language version, compiler/interpreter paths.
2. `distributions`: Strata units (Stratum 0 = `<ambient>`, Stratum 1 = Stdlib / Runtime, Stratum 2 = Third-party packages, Stratum 3 = Workspace).
3. `containers`: Physical and logical namespaces, modules, classes, structs, interfaces, enums, files with 1-based source coordinates (`start_line`, `start_col`, `end_line`, `end_col`).
4. `symbols`: Master symbol directory (functions, methods, properties, fields, variants, constants, keywords).
5. `callables`: Primary invocation signatures, `is_async`, `is_generator`, `is_static`, `is_class_bound`, `return_type_expr`, `raw_signature`.
6. `callable_overloads`: Polymorphic signatures, macro arms, and overload variants.
7. `parameters`: Ordered parameter metadata, pass kinds (`val`, `ref`, `mut_ref`, `pointer`, `variadic`, `keyword_only`, `positional_only`), type expressions, default values.
8. `state_members`: Struct/class fields, static members, variables, constants, access modes (`read_only`, `read_write`).
9. `symbol_aliases`: Re-exports, imports, and type aliases (`export *`, `pub use`, `using`, `import`).

### Layer 2: Language Fidelity Facet Tables (10–11)
Maintains a 1:1 foreign key relationship with `containers` and `symbols` to capture language-specific semantics without corrupting the universal schema:

| Language | Table 10 (Container Facets) | Table 11 (Symbol Facets) | Key Language-Specific Columns |
| :--- | :--- | :--- | :--- |
| **Python** | `py_container_facets` | `py_symbol_facets` | `is_dunder`, `is_coroutine`, `is_property`, `mangled_name`, `stub_status` |
| **C# .NET** | `cs_container_facets` | `cs_symbol_facets` | `assembly_name`, `is_record`, `is_struct`, `is_interface`, `is_extension_method`, `is_virtual` |
| **Rust** | `rust_container_facets` | `rust_symbol_facets` | `item_kind` (`struct`, `enum`, `trait`, `union`), `is_pub`, `is_unsafe`, `is_auto_trait`, `self_kind` (`val`, `ref`, `mut_ref`) |
| **TypeScript** | `ts_container_facets` | `ts_symbol_facets` | `is_ambient`, `heritage_clauses_json`, `access_modifier` (`public`, `protected`, `private`), `is_readonly`, `is_optional`, `is_declare` |
| **C/C++** | `cpp_container_facets` | `cpp_symbol_facets` | `is_template`, `base_classes_json`, `is_virtual`, `is_pure_virtual`, `is_override`, `is_const`, `is_noexcept`, `pass_by` |
| **Go** | `go_container_facets` | `go_symbol_facets` | `package_name`, `item_kind`, `receiver_kind` (`none`, `value`, `pointer`), `receiver_type` (`*Order`), `is_variadic`, `is_exported` |
