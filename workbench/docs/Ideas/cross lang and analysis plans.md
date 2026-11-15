Transitioning UTSS from isolated single-language catalogs into a **Cross-Language Synthesis & Bridge Research Engine** starts with treating your 6 SQLite databases (`python`, `csharp`, `rust`, `typescript`, `cpp`, `go`) as a single federated dataset. Because all 6 catalogs share an identical 9-table **Layer 1 Universal Core** alongside their **Layer 2 Fidelity Facets**, you can design a multi-language curriculum that systematically exposes the **exact impedance mismatches** a transpiler or unified compiler IR must solve.

---

## 1. Architectural Prerequisite: The Unified Federation View

Before running multi-language tutorials in the Workbench's Monaco SQL Runner, the FastAPI backend can expose a **federated connection** (either via a lightweight SQLite master database that runs `ATTACH DATABASE 'dbs/python_base_full.db' AS py;` for all 6 languages, or via DuckDB) with two pre-built convenience views:

* **`v_all_containers`**: Unions `containers` + `distributions` + `environments` across all 6 languages with a `language` column.
* **`v_all_symbols`**: Unions `symbols` + `callables` + `state_members` across all 6 languages, allowing single-query `GROUP BY language` comparisons without repetitive 6-way `UNION ALL` boilerplate.



---

## 2. Multi-Language Tutorial Curriculum: 4 Progressive Tracks (10 Lessons)

Instead of generic language trivia, design the cross-language curriculum around **the four structural pillars required to build a universal transpiler or bridge tool**:

| Track | Lesson Title | Core Bridge / Transpiler Question | UTSS Tables & Columns Joined |
| --- | --- | --- | --- |
| **I. Scope & Packaging** | **1. The Ambient Baseline (Stratum 0)** | What does a language give you with *zero* imports (`len`, `int`, `Result`, `Promise`, `println!`)? | `distributions` (`stratum = 0`), `symbols` (`symbol_kind`, `provenance`) across all 6 DBs |
| **I. Scope & Packaging** | **2. Namespace Topology & Re-Export Graphs** | How deeply nested are stdlib containers (`std::collections` vs `System.Collections.Generic` vs flat Go packages), and how do facades re-export internals? | `containers` (`parent_container_id`), `symbol_aliases` (`alias_kind`: `c_accelerator_reexport`, `pub_use_reexport`, `global_using`) |
| **II. Memory & Passing** | **3. Parameter Passing & Ownership Matrix** | How do Python's `positional_or_keyword` arguments map to Rust's `ref`/`mut_ref`, C++'s `const_ref`/`rvalue_ref`, Go's `pointer`, and C#'s `ref`/`out`/`in`? | `parameters` (`pass_kind`), `rust_symbol_facets` (`self_kind`), `go_symbol_facets` (`receiver_kind`), `cpp_symbol_facets` (`pass_by`) |
| **II. Memory & Passing** | **4. Mutability & Value vs. Reference Semantics** | Where is immutability the default (Rust `is_mutable=0`, C# `readonly struct`, TS `is_readonly`) vs opt-in (`Final`, `const`)? | `state_members` (`is_constant`, `is_mutable`, `access_mode`), `cs_container_facets` (`is_readonly_struct`, `is_ref_struct`) |
| **III. Polymorphism** | **5. Static Overloading vs. Dynamic Dispatch** | How do C# and C++ native method overloads compare to Python `@overload` stubs, TypeScript declaration overloads, and Go/Rust zero-overload designs? | `callables` (`has_overloads`, `overload_count`), `callable_overloads` (`overload_ordinal`, `raw_signature`) |
| **III. Polymorphism** | **6. Structural vs. Nominal Contracts** | How do Python dunder protocols (`__iter__`, `__enter__`) map to C# `IEnumerable`/`IDisposable`, Rust `Trait`s, Go implicit `interface`s, and C++ `concept`s? | `py_symbol_facets` (`dunder_category`), `cs_container_facets` (`implemented_interfaces_json`), `rust_container_facets` (`item_kind='trait'`), `go_container_facets` (`item_kind='interface'`) |
| **III. Polymorphism** | **7. Generics & Type Parameter Constraints** | How are generic bounds expressed across `type_params_json` (`[T any]` in Go, `typename T` in C++, `where_clause_json` in Rust, `generic_type_parameters_json` in C#)? | `callables` (`type_params_json`), `rust_container_facets`, `cs_container_facets`, `cpp_container_facets`, `go_container_facets` |
| **IV. Execution & Safety** | **8. Async, Coroutines & Generators** | How prevalent are `is_async` and `is_generator` callables across Python, C#, Rust, and TypeScript stdlibs compared to Go's synchronous-API + goroutine model? | `callables` (`is_async`, `is_generator`), `py_symbol_facets` (`co_flags`), `cs_symbol_facets` (`is_async`), `rust_symbol_facets` (`is_async`) |
| **IV. Execution & Safety** | **9. Error Handling & Safety Boundaries** | Where do stdlibs rely on exceptions (`exception_class`), return values (`Result<T, E>`, `(T, error)`), `noexcept` guarantees, or `unsafe` blocks? | `containers` (`container_kind='exception_class'`), `callables` (`return_type_expr`), `cpp_symbol_facets` (`is_noexcept`), `rust_symbol_facets` (`is_unsafe`) |
| **IV. Execution & Safety** | **10. The Rosetta Crosswalk (Lexical & Semantic Twins)** | Given a universal concept (e.g., UTF-8 String, Hash Map, File Stream, JSON Parser), what are the exact `qualified_name` counterparts across all 6 stdlibs? | Cross-DB join matching canonical operations (`open`, `read`, `parse`, `len`/`Count`/`len()`) across all 6 catalogs

 |

---

## 3. Data Science Research Agenda (`pandas` / `matplotlib` / `seaborn`)

Once you explore these relationships via SQL in the Workbench, exporting them into a Python Data Science pipeline (`server/analysis/` or Jupyter/Marimo notebooks) lets you quantify the **structural laws** of each language before writing transpiler rules:

### Experiment 1: Standard Library Surface Area & "Batteries-Included" Topology

* **Pandas Analysis**: Group `v_all_containers` and `v_all_symbols` by `language`, `stratum`, and `container_kind`. Compute the **Symbol-to-Container Ratio** (average symbols per module/namespace/struct) and **Tree Depth** (recursive parent hops via `parent_container_id`).
* **Visualization (`matplotlib` / `seaborn`)**:
* **Grouped Log-Scale Bar Chart**: Total Stratum 0 vs. Stratum 1 containers and symbols per language.
* **Violin / Box Plot**: Distribution of member counts per container (e.g., showing Go's small, focused packages vs. C#'s deep `System.*` namespaces vs. Python's monolithic C-extension modules).


* **Tooling Insight**: Tells your code generator whether a target language idioms favor splitting generated code into many small files/packages or consolidating into namespace hierarchies.

### Experiment 2: The Polymorphism & Arity Spectrum (Signature Complexity)

* **Pandas Analysis**: Load `callables`, `callable_overloads`, and `parameters` across all 6 DBs. Compute per-language distributions of:
1. Parameter count (arity) per callable.
2. Optional/default parameter ratio (`is_optional == 1`).
3. Overload multiplicity (`overload_count` where `has_overloads == 1`).


* **Visualization**:
* **Heatmap / Stacked Bar Chart**: Breakdown of `parameters.pass_kind` by language (`positional_or_keyword`, `keyword_only`, `val`, `ref`, `mut_ref`, `const_ref`, `pointer`, `out`, `variadic`).
* **ECDF (Empirical Cumulative Distribution Function) Plot**: Overload counts per callable comparing C#, C++, TypeScript, and Python `.pyi` stubs against Rust and Go (`overload_count == 0`).


* **Tooling Insight**: When transpiling a Python function with 5 optional keyword arguments (`def open(...)`) or 6 `@overload` variants into Rust or Go (which lack function overloading and default parameters), this data quantifies exactly how often your transpiler must synthesize **Builder structs**, **Options structs**, or **suffixed function names** (`open_with_mode`, `open_binary`).

### Experiment 3: Dunder-to-Trait/Interface Alignment Matrix

* **Pandas Analysis**: Extract all Python classes in `py_symbol_facets` grouped by `dunder_category` (`container`, `context_manager`, `numeric`, `comparison`, `lifecycle`) and cross-tabulate them against C# `implemented_interfaces_json`, Rust `trait` names, and C++ `operator` symbols.
* **Visualization**:
* **Sankey / Alluvial Diagram or Co-occurrence Heatmap**: Mapping Python dunder clusters (`__enter__`/`__exit__`, `__len__`/`__getitem__`, `__add__`/`__eq__`) to their target equivalents (`IDisposable` / `Drop`, `IReadOnlyList<T>` / `Index<T>`, operator overloads).


* **Tooling Insight**: Directly generates the lookup table for **Phase 4 Semantic Protocol Normalization**.

### Experiment 4: Type Erasure & Annotation Completeness Audit

* **Pandas Analysis**: Calculate the percentage of `callables.return_type_expr` and `parameters.type_expr` that are non-null and non-`Any`/`object`/`void*` across strata and signature sources (`inspect_signature` vs `pyi_stub_overlay` vs static AST).
* **Visualization**:
* **Stacked Horizontal Bar Chart**: "Type Completeness Score" before and after Pass 4 `.pyi` overlay in Python, compared against 100% statically typed catalogs (Rust, C#, Go, C++) and TypeScript (`any` vs concrete types).


* **Tooling Insight**: Measures the exact "type inference gap" your transpiler still needs to resolve when compiling real-world Python or TypeScript workspaces.

---

## 4. How This Pipeline Feeds Your Ultimate Bridge Tooling

```
[Stage 1: SQL Workbench]       [Stage 2: Data Science]        [Stage 3: Unified Bridge Engine]
Interactive Cross-DB Queries ──► Pandas/Matplotlib Empirical ──► Canonical Type & Protocol
(Discover edge cases &          Clustering & Impedance          Crosswalk Tables in SQLite
 structural patterns)           Quantification                  (Powers psc & multi-lang IR)

```

1. **Explore (SQL Curriculum)**: You write cross-language SQL queries in the Workbench to inspect how specific constructs (e.g., iterators, slices, file handles, dictionaries) are represented in Layer 1 & Layer 2 tables across all 6 languages.
2. **Quantify (Pandas/Matplotlib)**: You run statistical scripts over the full catalogs to see the macro-distribution of patterns (e.g., 82% of Rust methods take `&self` or `&mut self`; 34% of Python stdlib callables use keyword-only or default args).
3. **Codify (Bridge Tables)**: The output of your Pandas notebooks isn't just charts—it exports two new tables directly into a master `utss_bridge.db`:
* `universal_type_mappings` (mapping `builtins.list[T]` $\leftrightarrow$ `System.Collections.Generic.List<T>` $\leftrightarrow$ `alloc::vec::Vec<T>` $\leftrightarrow$ `std::vector<T>` $\leftrightarrow$ `[]T` $\leftrightarrow$ `Array<T>`).
* `universal_protocol_mappings` (mapping dunder/trait/interface contracts across the 6 ecosystems).



Would you like to start by **designing the SQL queries and YAML curriculum files for the Cross-Language Tutorial Track**, or by **building a Python Data Science notebook/script (`pandas` + `matplotlib`) that loads all 6 `.db` files to generate the first comparative plots**?




















This **12-Lesson Multi-Language & Bridge Synthesis Curriculum** is designed for the `Comparative Analytics` track (`queries/comparative/`) in the UTSS Workbench.

Because all 6 UTSS databases (`python`, `csharp`, `rust`, `typescript`, `cpp`, `go`) share an identical 9-table **Layer 1 Universal Core**, **Lessons 1–9** can be run either on any single database (by toggling the TopNav Database Switcher to compare outputs immediately) or across a federated connection, while **Lessons 10–12** join **Layer 2 Language-Fidelity Facets** across attached databases to construct cross-language transpiler crosswalks.

---

## 0. Curriculum Overview Matrix

| Module | Lesson | Topic | Core Transpiler / Bridge Problem Solved | Primary UTSS Tables |
| --- | --- | --- | --- | --- |
| **I. Scope & Topology** | **01** | **The Ambient Baseline (Stratum 0)** | Identifying symbols available with zero imports (`len`, `Result`, `Promise`, `int`). | `environments`, `distributions`, `symbols` |
| **I. Scope & Topology** | **02** | **Stdlib Namespace Depth & Granularity** | Mapping flat package topologies (Go, Python) to deep namespace trees (C#, Rust, C++). | `distributions`, `containers` (recursive CTE) |
| **I. Scope & Topology** | **03** | **Facades, Re-Exports & Alias Graphs** | Resolving public API facades (`io.open`, `pub use`, `global using`) to canonical definitions. | `symbol_aliases`, `containers`, `symbols` |
| **II. Memory & Calling** | **04** | **Parameter Passing & Ownership Spectrum** | Translating Python positional/keyword args into `val`, `ref`, `mut_ref`, `out`, or `pointer`. | `parameters`, `callables`, `symbols` |
| **II. Memory & Calling** | **05** | **Arity, Optionality & Default Arguments** | Synthesizing Builder/Options structs when transpiling default-heavy APIs to Rust or Go. | `callables`, `parameters` |
| **II. Memory & Calling** | **06** | **State Mutability & Field Access Control** | Enforcing immutability defaults (`readonly`, `const`, `is_mutable=0`) across state members. | `state_members`, `symbols`, `containers` |
| **III. Polymorphism** | **07** | **Static Overloading vs. Single Dispatch** | Disambiguating C#/C++/TS/Python `@overload` families into distinct target identifiers. | `callables`, `callable_overloads`, `symbols` |
| **III. Polymorphism** | **08** | **Parametric Polymorphism & Generics** | Aligning generic type parameters (`type_params_json`) across erased, reified, and monomorphized runtimes. | `callables`, `containers`, `symbols` |
| **III. Polymorphism** | **09** | **Async State Machines & Generators** | Mapping `async`/`await` coroutines and `yield` generators across runtime execution models. | `callables`, `symbols`, `containers` |
| **IV. Facet Crosswalks** | **10** | **Value Semantics & Stack Constraints** | Bridging C# `readonly ref struct`, Rust stack structs, Go value types, and C++ PODs. | `cs_container_facets`, `rust_container_facets`, `cpp_container_facets` |
| **IV. Facet Crosswalks** | **11** | **Dunders to Interfaces, Traits & Concepts** | Normalizing Python duck-typed dunders (`__iter__`, `__enter__`) into nominal contracts. | `py_symbol_facets`, `cs_container_facets`, `rust_container_facets`, `go_container_facets` |
| **IV. Facet Crosswalks** | **12** | **The Rosetta Crosswalk (Semantic Twins)** | Discovering equivalent stdlib types & methods (String, List/Vec, Map/Dict, File I/O) across all 6 DBs. | Federated join across all 6 catalogs

 |

---

## Module I: Scope, Packaging & Namespace Topology

### Lesson 1: The Ambient Baseline (Stratum 0) — Zero-Import Vocabulary

* **Why It Matters**: Every transpiler must know what symbols exist in lexical scope before a single `import`, `using`, `use`, or `#include` is emitted. Python exposes 60+ built-in functions/types (`len`, `open`, `ValueError`) and `site`-injected helpers in Stratum 0; Rust exposes the Standard Prelude (`Option`, `Result`, `Vec`, `Box`, `drop`); Go exposes predeclared identifiers (`make`, `len`, `append`, `panic`, `error`); TypeScript exposes ECMAScript globals (`Promise`, `Array`, `Record`); whereas C++ and C# restrict Stratum 0 primarily to language keywords and primitive types.


* **Bridge Research Goal**: Quantify how many Stratum 0 ambient symbols in a source language require synthesizing an explicit Stratum 1 import (`using System;`, `#include <vector>`, `import "fmt"`) in the target language.

```sql
/*---
id: comp_01_ambient_baseline
suite: comparative
sequence: 1
title: "The Ambient Baseline (Stratum 0): Zero-Import Vocabulary"
difficulty: Basic
category: Scope & Topology
description: "Compares symbols available globally without any import statement across language runtimes, broken down by symbol kind and provenance."
---*/
SELECT
    e.language,
    e.runtime_name,
    e.language_version,
    s.symbol_kind,
    s.provenance,
    COUNT(s.symbol_id) AS ambient_symbol_count,
    GROUP_CONCAT(
        CASE WHEN s.symbol_id % 7 = 0 THEN s.name END, ', '
    ) AS sample_symbols
FROM environments e
JOIN distributions d ON d.env_id = e.env_id
JOIN containers c ON c.dist_id = d.dist_id
JOIN symbols s ON s.container_id = c.container_id
WHERE d.stratum = 0
  AND c.requires_import = 0
GROUP BY e.language, e.runtime_name, e.language_version, s.symbol_kind, s.provenance
ORDER BY e.language ASC, ambient_symbol_count DESC;

```

---

### Lesson 2: Standard Library Architecture (Stratum 1) — Deep Trees vs. Flat Packages

* **Why It Matters**: Standard libraries organize their containers into radically different hierarchy depths via `parent_container_id`. Go (`fmt`, `net/http`) and Python (`json`, `os.path`) favor shallow module/package trees; C# (`System.Collections.Generic.List`) and Rust (`std::collections::hash_map::Entry`) nest namespaces, modules, and types 3 to 6 levels deep; C++ places nearly the entire standard library inside a single flat `std` namespace container (`std::vector`, `std::filesystem::path`).


* **Bridge Research Goal**: Measure container hierarchy depth (`tree_depth`) and symbol density per container so code generators know how to map source module paths into idiomatic target namespace hierarchies.

```sql
/*---
id: comp_02_stdlib_topology
suite: comparative
sequence: 2
title: "Stdlib Namespace Depth & Container Granularity (Stratum 1)"
difficulty: Intermediate
category: Scope & Topology
description: "Uses a recursive CTE to compute the nesting depth of Stratum 1 containers (modules, namespaces, classes, structs, traits) and symbol density per container."
---*/
WITH RECURSIVE container_hierarchy AS (
    -- Root containers in Stratum 1 (no parent container)
    SELECT
        c.container_id,
        c.dist_id,
        c.parent_container_id,
        c.container_kind,
        c.qualified_name,
        1 AS depth
    FROM containers c
    JOIN distributions d ON c.dist_id = d.dist_id
    WHERE d.stratum = 1
      AND c.parent_container_id IS NULL

    UNION ALL

    -- Child containers (submodules, nested namespaces, classes/structs inside modules)
    SELECT
        child.container_id,
        child.dist_id,
        child.parent_container_id,
        child.container_kind,
        child.qualified_name,
        parent.depth + 1 AS depth
    FROM containers child
    JOIN container_hierarchy parent ON child.parent_container_id = parent.container_id
    WHERE parent.depth < 10
)
SELECT
    e.language,
    ch.container_kind,
    ch.depth AS hierarchy_depth,
    COUNT(DISTINCT ch.container_id) AS container_count,
    COUNT(s.symbol_id) AS total_symbols,
    ROUND(CAST(COUNT(s.symbol_id) AS FLOAT) / NULLIF(COUNT(DISTINCT ch.container_id), 0), 2) AS avg_symbols_per_container
FROM container_hierarchy ch
JOIN distributions d ON ch.dist_id = d.dist_id
JOIN environments e ON d.env_id = e.env_id
LEFT JOIN symbols s ON s.container_id = ch.container_id AND s.is_hidden = 0
GROUP BY e.language, ch.container_kind, ch.depth
ORDER BY e.language ASC, ch.depth ASC, container_count DESC;

```

---

### Lesson 3: Facades, Re-Exports & Namespace Delegation (`symbol_aliases`)

* **Why It Matters**: Compilers cannot rely on naive symbol locations because languages frequently expose symbols through public facades while defining them in private implementation containers. Python's `io.BufferedReader` delegates to C-accelerator `_io.BufferedReader` (`c_accelerator_reexport`); Rust's `std` re-exports primitives from `core` and `alloc` via `pub use` (`pub_use_reexport`); C# uses `global using` and type forwarding; C++ headers re-export symbols via `using` declarations (`using_decl`).


* **Bridge Research Goal**: Trace `symbol_aliases` from the public container a user imports to the underlying `target_module_name` and `target_symbol_name` where the true type signature lives.

```sql
/*---
id: comp_03_facade_reexports
suite: comparative
sequence: 3
title: "Public Facades, Re-Exports & C-Accelerator Delegation"
difficulty: Intermediate
category: Scope & Topology
description: "Inspects symbol_aliases to trace how public standard library containers re-export symbols from private backing modules or core crates."
---*/
SELECT
    e.language,
    sa.alias_kind,
    c.qualified_name AS public_facade_container,
    sa.exposed_name AS public_symbol,
    sa.target_module_name AS backing_container,
    sa.target_symbol_name AS backing_symbol,
    sa.is_in_dunder_all
FROM symbol_aliases sa
JOIN containers c ON sa.source_container_id = c.container_id
JOIN distributions d ON c.dist_id = d.dist_id
JOIN environments e ON d.env_id = e.env_id
ORDER BY e.language ASC, sa.alias_kind ASC, c.qualified_name ASC
LIMIT 200;

```

---

## Module II: Memory, Mutability & Calling Conventions

### Lesson 4: Parameter Passing Semantics & Ownership Spectrum (`parameters.pass_kind`)

* **Why It Matters**: In Python, every argument is passed as an object reference with flexible calling syntax (`positional_only`, `positional_or_keyword`, `keyword_only`, `var_positional`, `var_keyword`). Static targets partition parameter passing by **memory ownership and mutability**: Rust distinguishes `val`, `ref`, `mut_ref`, `self_val`, `self_ref`, `self_mut_ref`; C++ distinguishes `val`, `ref`, `const_ref`, `rvalue_ref`, `pointer`, `const_pointer`; C# distinguishes `value`, `ref`, `out`, `in`, `params`; Go distinguishes `val`, `pointer`, `slice`, `variadic`.


* **Bridge Research Goal**: Quantify the exact distribution of `parameters.pass_kind` across each language's standard library to design automated borrow/reference inference rules when transpiling from Python or TypeScript to Rust, C++, C#, or Go.

```sql
/*---
id: comp_04_parameter_passing
suite: comparative
sequence: 4
title: "The Parameter Passing & Ownership Spectrum (pass_kind)"
difficulty: Intermediate
category: Memory & Calling Conventions
description: "Profiles how parameters are passed across languages—contrasting Python's calling-syntax kinds against Rust ownership borrows, C++ const/rvalue refs, C# ref/out/in, and Go pointers."
---*/
SELECT
    e.language,
    p.pass_kind,
    COUNT(p.param_id) AS parameter_count,
    ROUND(
        100.0 * COUNT(p.param_id) / SUM(COUNT(p.param_id)) OVER (PARTITION BY e.language),
        2
    ) AS pct_of_language_params,
    SUM(CASE WHEN p.is_optional = 1 THEN 1 ELSE 0 END) AS optional_params,
    COUNT(DISTINCT p.type_expr) AS distinct_type_expressions
FROM parameters p
JOIN callables cal ON p.callable_symbol_id = cal.symbol_id
JOIN symbols s ON cal.symbol_id = s.symbol_id
JOIN containers c ON s.container_id = c.container_id
JOIN distributions d ON c.dist_id = d.dist_id
JOIN environments e ON d.env_id = e.env_id
WHERE s.is_hidden = 0
GROUP BY e.language, p.pass_kind
ORDER BY e.language ASC, parameter_count DESC;

```

---

### Lesson 5: Default Arguments, Optionality & Arity Impedance

* **Why It Matters**: Python (`open`, `json.dumps`), TypeScript, C#, and C++ allow functions with 5 to 15 parameters where most have default values (`is_optional = 1`, `default_expr IS NOT NULL`). Neither **Rust** nor **Go** supports default parameter values or optional positional arguments in function signatures.


* **Bridge Research Goal**: Identify high-arity callables with optional defaults so the transpiler knows when it must synthesize an **Options/Config struct** (in Go) or a **Builder pattern** (in Rust) instead of a direct 1:1 function call.

```sql
/*---
id: comp_05_arity_and_defaults
suite: comparative
sequence: 5
title: "Callable Arity & Default Parameter Impedance"
difficulty: Intermediate
category: Memory & Calling Conventions
description: "Analyzes callable parameter counts (arity) and optional default parameter ratios to measure the signature impedance between default-supporting languages (Python/C#/TS/C++) and strict-arity languages (Rust/Go)."
---*/
WITH callable_arity AS (
    SELECT
        e.language,
        s.qualified_name,
        s.symbol_kind,
        cal.raw_signature,
        COUNT(p.param_id) AS total_params,
        SUM(CASE WHEN p.is_optional = 1 OR p.default_expr IS NOT NULL THEN 1 ELSE 0 END) AS optional_params
    FROM callables cal
    JOIN symbols s ON cal.symbol_id = s.symbol_id
    JOIN containers c ON s.container_id = c.container_id
    JOIN distributions d ON c.dist_id = d.dist_id
    JOIN environments e ON d.env_id = e.env_id
    LEFT JOIN parameters p ON p.callable_symbol_id = cal.symbol_id AND p.overload_id IS NULL
    WHERE d.stratum IN (0, 1)
      AND s.is_hidden = 0
    GROUP BY e.language, cal.symbol_id, s.qualified_name, s.symbol_kind, cal.raw_signature
)
SELECT
    language,
    symbol_kind,
    COUNT(*) AS total_callables,
    ROUND(AVG(total_params), 2) AS avg_arity,
    MAX(total_params) AS max_arity,
    SUM(CASE WHEN optional_params > 0 THEN 1 ELSE 0 END) AS callables_with_defaults,
    ROUND(100.0 * SUM(CASE WHEN optional_params > 0 THEN 1 ELSE 0 END) / COUNT(*), 2) AS pct_with_defaults
FROM callable_arity
GROUP BY language, symbol_kind
ORDER BY language ASC, total_callables DESC;

```

---

### Lesson 6: State Mutability & Field Access Control (`state_members`)

* **Why It Matters**: In Python, module globals and instance attributes (`self.x`) default to `is_mutable = 1` and `access_mode = 'read_write'` unless typed as `Final` or wrapped in a read-only `@property`. Rust defaults bindings and fields to immutable (`is_mutable = 0`), C# provides `init_only` (`{ get; init; }`) and `read_only` properties, and TypeScript provides `readonly` modifiers.


* **Bridge Research Goal**: Compare mutability ratios across `state_members` to determine when transpiled class fields can be emitted as `readonly` / immutable fields versus mutable state.

```sql
/*---
id: comp_06_state_mutability
suite: comparative
sequence: 6
title: "State Mutability, Constants & Access Modes (state_members)"
difficulty: Basic
category: Memory & Calling Conventions
description: "Compares fields, properties, constants, and module variables across languages by mutability flags (is_constant, is_mutable) and access_mode (read_only, read_write, init_only)."
---*/
SELECT
    e.language,
    s.symbol_kind,
    sm.access_mode,
    sm.is_constant,
    sm.is_mutable,
    COUNT(sm.symbol_id) AS member_count,
    SUM(CASE WHEN sm.declared_type_expr IS NOT NULL AND sm.declared_type_expr != '' THEN 1 ELSE 0 END) AS explicitly_typed_count
FROM state_members sm
JOIN symbols s ON sm.symbol_id = s.symbol_id
JOIN containers c ON s.container_id = c.container_id
JOIN distributions d ON c.dist_id = d.dist_id
JOIN environments e ON d.env_id = e.env_id
WHERE s.is_hidden = 0
GROUP BY e.language, s.symbol_kind, sm.access_mode, sm.is_constant, sm.is_mutable
ORDER BY e.language ASC, member_count DESC;

```

---

## Module III: Polymorphism, Overloading & Type Generics

### Lesson 7: Static Overloading vs. Single-Dispatch Signatures (`callable_overloads`)

* **Why It Matters**: C#, C++, and TypeScript rely heavily on ad-hoc function/method overloading (`has_overloads = 1`), and Python models type-dependent return types via `.pyi` `@overload` stubs (e.g., `builtins.open` returning `TextIOWrapper` vs `FileIO` depending on the `mode` string literal). Rust and Go prohibit function overloading by name—every variant requires either a distinct method name (`from_str`, `from_utf8`, `with_capacity`) or a trait conversion (`From<T>`).


* **Bridge Research Goal**: Inspect `callable_overloads` families and their return-type divergence across `overload_ordinal` to automate name disambiguation when targeting non-overloaded languages (or collapsing overloaded C#/C++ functions into Python `@overload` stubs).

```sql
/*---
id: comp_07_polymorphic_overloads
suite: comparative
sequence: 7
title: "Polymorphic @overload Families & Return-Type Variance"
difficulty: Intermediate
category: Polymorphism & Type Systems
description: "Examines callables with multiple registered overload signatures (callable_overloads) and measures how frequently overloaded variants change their return type."
---*/
SELECT
    e.language,
    s.qualified_name,
    s.symbol_kind,
    cal.overload_count,
    COUNT(DISTINCT co.return_type_expr) AS distinct_return_types,
    MIN(co.raw_signature) AS first_overload_signature,
    MAX(co.raw_signature) AS last_overload_signature
FROM callables cal
JOIN symbols s ON cal.symbol_id = s.symbol_id
JOIN containers c ON s.container_id = c.container_id
JOIN distributions d ON c.dist_id = d.dist_id
JOIN environments e ON d.env_id = e.env_id
JOIN callable_overloads co ON co.callable_symbol_id = cal.symbol_id
WHERE cal.has_overloads = 1
GROUP BY e.language, cal.symbol_id, s.qualified_name, s.symbol_kind, cal.overload_count
ORDER BY cal.overload_count DESC, distinct_return_types DESC
LIMIT 100;

```

---

### Lesson 8: Generic Type Parameters & Parametric Polymorphism (`type_params_json`)

* **Why It Matters**: Parametric polymorphism is stored universally in `callables.type_params_json` (and container facet generic columns), but its syntax and runtime semantics differ sharply: Python (`["_T"]`) and TypeScript erase generics at runtime; C# (`["T"]`) reifies generics in the CLR VM; Rust (`["T", "const N: usize"]`) and C++ (`["typename T", "size_t N"]`) monomorphize templates at compile time (including non-type `const` integer parameters); Go (`[T any]`, `[T comparable]`) uses GC-shape stenciling with interface constraints.


* **Bridge Research Goal**: Extract all generic callables and inspect their type parameter constraints across languages.

```sql
/*---
id: comp_08_generic_type_params
suite: comparative
sequence: 8
title: "Parametric Polymorphism & Generic Type Parameters"
difficulty: Intermediate
category: Polymorphism & Type Systems
description: "Inspects callables that declare generic/template type parameters in type_params_json alongside their return type expressions."
---*/
SELECT
    e.language,
    s.qualified_name,
    s.symbol_kind,
    cal.type_params_json,
    cal.return_type_expr,
    cal.raw_signature,
    cal.signature_source
FROM callables cal
JOIN symbols s ON cal.symbol_id = s.symbol_id
JOIN containers c ON s.container_id = c.container_id
JOIN distributions d ON c.dist_id = d.dist_id
JOIN environments e ON d.env_id = e.env_id
WHERE cal.type_params_json IS NOT NULL
  AND cal.type_params_json != ''
  AND cal.type_params_json != '[]'
  AND s.is_hidden = 0
ORDER BY e.language ASC, s.qualified_name ASC
LIMIT 150;

```

---

### Lesson 9: Concurrency & Iteration Primitives (`is_async` & `is_generator`)

* **Why It Matters**: Python (`async def`, `yield`), C# (`async Task<T>`, `yield return` returning `IEnumerable<T>` / `IAsyncEnumerable<T>`), Rust (`async fn` returning `Future`), and TypeScript (`async` returning `Promise<T>`, `function*`) encode asynchronous and lazy-iteration semantics directly on the callable signature (`is_async = 1`, `is_generator = 1`). Go deliberately omits `async`/`await` coloring in favor of synchronous functions invoked as goroutines (`go fn()`) with channels, and C++20 models coroutines via return types (`co_await`, `co_yield`).


* **Bridge Research Goal**: Audit `is_async` and `is_generator` prevalence across standard libraries to map coroutine state machines and lazy iterators across runtimes.

```sql
/*---
id: comp_09_async_and_generators
suite: comparative
sequence: 9
title: "Async Coroutines & Lazy Generators Across Runtimes"
difficulty: Intermediate
category: Execution & Safety
description: "Compares the density of async functions (is_async=1) and generator/iterator functions (is_generator=1) across standard libraries."
---*/
SELECT
    e.language,
    s.symbol_kind,
    cal.is_async,
    cal.is_generator,
    COUNT(cal.symbol_id) AS callable_count,
    GROUP_CONCAT(
        CASE WHEN cal.symbol_id % 5 = 0 THEN s.qualified_name END, ', '
    ) AS sample_callables
FROM callables cal
JOIN symbols s ON cal.symbol_id = s.symbol_id
JOIN containers c ON s.container_id = c.container_id
JOIN distributions d ON c.dist_id = d.dist_id
JOIN environments e ON d.env_id = e.env_id
WHERE (cal.is_async = 1 OR cal.is_generator = 1)
  AND s.is_hidden = 0
GROUP BY e.language, s.symbol_kind, cal.is_async, cal.is_generator
ORDER BY e.language ASC, callable_count DESC;

```

---

## Module IV: Cross-Language Facet Alignment & Bridge Synthesis

> **Federated Execution Note for Lessons 10–12**: These three advanced lessons query **Layer 2 Language-Fidelity Facets** across multiple languages simultaneously. When running in the Comparative Analytics backend (`server/analysis/`), attach the 6 SQLite databases onto a read-only analytical connection using aliases `py`, `cs`, `rs`, `ts`, `cpp`, and `go`:
> 
> 
> ```sql
> ATTACH DATABASE 'dbs/python_base_full.db' AS py;
> ATTACH DATABASE 'dbs/catalog_cs_full.db'  AS cs;
> ATTACH DATABASE 'dbs/catalog_rust_full.db' AS rs;
> ATTACH DATABASE 'dbs/catalog_ts_full.db'  AS ts;
> ATTACH DATABASE 'dbs/catalog_cpp_full.db' AS cpp;
> ATTACH DATABASE 'dbs/catalog_go_full.db'  AS go;
> 
> ```
> 
> 

### Lesson 10: Value Types, Stack Allocation & Receiver Mechanics (Layer 2 Facet Join)

* **Why It Matters**: In Python, every `int`, `str`, or `Order` instance is a heap-allocated PyObject with reference counting. When transpiling Python or TypeScript to C#, Rust, Go, or C++, performance depends on lowering classes to value types and choosing the right method receiver: C# distinguishes `class`, `struct`, `readonly struct`, `record struct`, and stack-bound `ref struct` (`Span<T>`) in `cs_container_facets`; Rust tracks ownership on every method via `self_kind` (`val`, `ref`, `mut_ref`) in `rust_symbol_facets`; Go distinguishes `receiver_kind` (`value` vs `pointer` `*T`) in `go_symbol_facets`; and C++ tracks `is_const`, `is_constexpr`, and `is_noexcept` in `cpp_symbol_facets`.


* **Bridge Research Goal**: Compare how each compiled target constrains memory allocation and method receiver mutability in its Layer 2 facets.

```sql
/*---
id: comp_10_value_types_and_receivers
suite: comparative
sequence: 10
title: "Memory Layout & Method Receivers Across Layer 2 Facets"
difficulty: Advanced
category: Facet Crosswalks
description: "Unions Layer 2 facet tables across C#, Rust, Go, and C++ to compare value-type containers and method receiver mutability (ref/mut_ref, value/pointer, const/noexcept)."
---*/
SELECT
    'csharp' AS language,
    cf.type_kind AS container_category,
    CASE
        WHEN cf.is_ref_struct = 1 THEN 'stack_only_ref_struct'
        WHEN cf.is_readonly_struct = 1 THEN 'immutable_value_type'
        WHEN cf.is_sealed = 1 THEN 'sealed_nominal'
        ELSE 'standard_nominal'
    END AS memory_semantics,
    COUNT(*) AS entity_count
FROM cs.cs_container_facets cf
GROUP BY cf.type_kind, memory_semantics

UNION ALL

SELECT
    'rust' AS language,
    sf.member_kind AS container_category,
    'self_' || sf.self_kind || CASE WHEN sf.is_const = 1 THEN '_const' ELSE '' END AS memory_semantics,
    COUNT(*) AS entity_count
FROM rs.rust_symbol_facets sf
WHERE sf.member_kind IN ('method', 'associated_fn', 'fn')
GROUP BY sf.member_kind, memory_semantics

UNION ALL

SELECT
    'go' AS language,
    sf.member_kind AS container_category,
    'receiver_' || sf.receiver_kind AS memory_semantics,
    COUNT(*) AS entity_count
FROM go.go_symbol_facets sf
WHERE sf.member_kind IN ('method', 'func')
GROUP BY sf.member_kind, memory_semantics

UNION ALL

SELECT
    'cpp' AS language,
    sf.member_kind AS container_category,
    CASE
        WHEN sf.is_constexpr = 1 THEN 'constexpr_compile_time'
        WHEN sf.is_const = 1 AND sf.is_noexcept = 1 THEN 'const_noexcept_method'
        WHEN sf.is_const = 1 THEN 'const_method'
        ELSE 'mutable_or_free'
    END AS memory_semantics,
    COUNT(*) AS entity_count
FROM cpp.cpp_symbol_facets sf
WHERE sf.member_kind IN ('method', 'function', 'operator')
GROUP BY sf.member_kind, memory_semantics
ORDER BY language ASC, entity_count DESC;

```

---

### Lesson 11: Protocol & Interface Alignment — Python Dunders to C# Interfaces & Rust Traits

* **Why It Matters**: Phase 4 of UTSS ("Cross-Language Type Normalization") requires translating Python's structural/duck-typed dunder protocols (`py_symbol_facets.dunder_category`: `container`, `context_manager`, `comparison`, `numeric`, `lifecycle`, `async`) into nominal C# interfaces (`IEnumerable<T>`, `IDisposable`, `IComparable<T>`), Rust traits (`Iterator`, `Drop`, `PartialEq`, `Add`, `Index`), Go implicit interfaces (`io.Reader`, `io.Closer`), and C++ overloaded operators.


* **Bridge Research Goal**: Build an empirical crosswalk table mapping Python dunder categories directly to their structural counterparts in C#, Rust, and C++.

```sql
/*---
id: comp_11_dunder_to_trait_alignment
suite: comparative
sequence: 11
title: "Protocol Alignment: Python Dunders vs. C# Interfaces, Rust Traits & C++ Operators"
difficulty: Advanced
category: Facet Crosswalks
description: "Maps Python's dunder_category protocols (context_manager, container, comparison, numeric) to their behavioral counterparts in C#, Rust, and C++."
---*/
WITH protocol_catalog AS (
    -- Python Dunder Protocols
    SELECT
        'python' AS language,
        psf.dunder_category AS protocol_family,
        s.name AS construct_name,
        COUNT(DISTINCT s.container_id) AS implementing_containers
    FROM py.py_symbol_facets psf
    JOIN py.symbols s ON psf.symbol_id = s.symbol_id
    WHERE psf.dunder_category IS NOT NULL
    GROUP BY psf.dunder_category, s.name

    UNION ALL

    -- C# Operators & Interface Implementations
    SELECT
        'csharp' AS language,
        CASE
            WHEN csf.operator_kind LIKE '%Addition%' OR csf.operator_kind LIKE '%Subtraction%' OR csf.operator_kind LIKE '%Multiply%' THEN 'numeric'
            WHEN csf.operator_kind LIKE '%Equality%' OR csf.operator_kind LIKE '%LessThan%' OR csf.operator_kind LIKE '%GreaterThan%' THEN 'comparison'
            WHEN csf.member_kind = 'indexer' THEN 'container'
            WHEN s.name = 'Dispose' OR csf.explicit_interface_specifier LIKE '%IDisposable%' THEN 'context_manager'
            ELSE 'other_contract'
        END AS protocol_family,
        COALESCE(csf.operator_kind, s.name) AS construct_name,
        COUNT(DISTINCT s.container_id) AS implementing_containers
    FROM cs.cs_symbol_facets csf
    JOIN cs.symbols s ON csf.symbol_id = s.symbol_id
    WHERE csf.operator_kind IS NOT NULL
       OR csf.member_kind = 'indexer'
       OR s.name IN ('Dispose', 'GetEnumerator', 'Equals', 'CompareTo')
    GROUP BY protocol_family, construct_name

    UNION ALL

    -- Rust Core Traits
    SELECT
        'rust' AS language,
        CASE
            WHEN c.short_name IN ('Drop', 'Deref', 'DerefMut') THEN 'context_manager'
            WHEN c.short_name IN ('Iterator', 'IntoIterator', 'Index', 'IndexMut', 'ExactSizeIterator') THEN 'container'
            WHEN c.short_name IN ('PartialEq', 'Eq', 'PartialOrd', 'Ord', 'Hash') THEN 'comparison'
            WHEN c.short_name IN ('Add', 'Sub', 'Mul', 'Div', 'Rem', 'Neg') THEN 'numeric'
            WHEN c.short_name IN ('Clone', 'Copy', 'Default') THEN 'lifecycle'
            ELSE 'other_trait'
        END AS protocol_family,
        c.qualified_name AS construct_name,
        COUNT(s.symbol_id) AS implementing_containers
    FROM rs.rust_container_facets rcf
    JOIN rs.containers c ON rcf.container_id = c.container_id
    LEFT JOIN rs.symbols s ON s.container_id = c.container_id
    WHERE rcf.item_kind = 'trait'
    GROUP BY protocol_family, c.qualified_name
)
SELECT
    protocol_family,
    language,
    construct_name,
    implementing_containers
FROM protocol_catalog
WHERE protocol_family IN ('context_manager', 'container', 'comparison', 'numeric', 'lifecycle')
ORDER BY protocol_family ASC, language ASC, implementing_containers DESC;

```

---

### Lesson 12: The Rosetta Crosswalk — Mapping Canonical Types & Operations Across All 6 Stdlibs

* **Why It Matters**: The culmination of the curriculum is constructing the **Rosetta Crosswalk** for Phase 4 & Phase 5 (`psc` and multi-target transpilation): given a universal data structure or operation (Dynamic Array/List, Key-Value Hash Map, UTF-8 String, File Handle, JSON Serializer), what are the exact `qualified_name` containers and method signatures across all 6 databases?


* **Bridge Research Goal**: Query the canonical container and its public methods across all 6 catalogs simultaneously to verify how operations like `append`/`Add`/`push`/`push_back` or `len`/`Count`/`size` map to one another.

```sql
/*---
id: comp_12_rosetta_crosswalk
suite: comparative
sequence: 12
title: "The Rosetta Crosswalk: Dynamic Sequence & Hash Map Twins Across 6 Stdlibs"
difficulty: Advanced
category: Facet Crosswalks
description: "Queries the canonical Dynamic Array (list / List<T> / Vec<T> / vector<T> / Array<T> / slice) and Hash Map containers across all 6 attached UTSS databases to align their method vocabularies."
---*/
WITH canonical_containers AS (
    SELECT 'python' AS lang, 'Sequence<T>' AS concept, c.container_id, c.qualified_name
    FROM py.containers c WHERE c.qualified_name IN ('builtins.list', 'list')
    UNION ALL
    SELECT 'csharp', 'Sequence<T>', c.container_id, c.qualified_name
    FROM cs.containers c WHERE c.qualified_name = 'System.Collections.Generic.List'
    UNION ALL
    SELECT 'rust', 'Sequence<T>', c.container_id, c.qualified_name
    FROM rs.containers c WHERE c.qualified_name LIKE '%::vec::Vec'
    UNION ALL
    SELECT 'cpp', 'Sequence<T>', c.container_id, c.qualified_name
    FROM cpp.containers c WHERE c.qualified_name = 'std::vector'
    UNION ALL
    SELECT 'typescript', 'Sequence<T>', c.container_id, c.qualified_name
    FROM ts.containers c WHERE c.qualified_name = 'Array'
    UNION ALL
    SELECT 'go', 'Sequence<T>', c.container_id, c.qualified_name
    FROM go.containers c WHERE c.qualified_name = 'slices'
)
SELECT
    cc.concept,
    cc.lang AS language,
    cc.qualified_name AS canonical_container,
    s.name AS operation_name,
    cal.raw_signature,
    cal.return_type_expr
FROM canonical_containers cc
JOIN (
    SELECT 'python' AS lang, container_id, symbol_id, name, is_hidden FROM py.symbols
    UNION ALL
    SELECT 'csharp', container_id, symbol_id, name, is_hidden FROM cs.symbols
    UNION ALL
    SELECT 'rust', container_id, symbol_id, name, is_hidden FROM rs.symbols
    UNION ALL
    SELECT 'cpp', container_id, symbol_id, name, is_hidden FROM cpp.symbols
    UNION ALL
    SELECT 'typescript', container_id, symbol_id, name, is_hidden FROM ts.symbols
    UNION ALL
    SELECT 'go', container_id, symbol_id, name, is_hidden FROM go.symbols
) s ON s.lang = cc.lang AND s.container_id = cc.container_id
LEFT JOIN (
    SELECT 'python' AS lang, symbol_id, raw_signature, return_type_expr FROM py.callables
    UNION ALL
    SELECT 'csharp', symbol_id, raw_signature, return_type_expr FROM cs.callables
    UNION ALL
    SELECT 'rust', symbol_id, raw_signature, return_type_expr FROM rs.callables
    UNION ALL
    SELECT 'cpp', symbol_id, raw_signature, return_type_expr FROM cpp.callables
    UNION ALL
    SELECT 'typescript', symbol_id, raw_signature, return_type_expr FROM ts.callables
    UNION ALL
    SELECT 'go', symbol_id, raw_signature, return_type_expr FROM go.callables
) cal ON cal.lang = s.lang AND cal.symbol_id = s.symbol_id
WHERE s.is_hidden = 0
  AND s.name IN (
      -- Append / Insert operations
      'append', 'Add', 'push', 'push_back', 'Insert', 'insert',
      -- Length / Capacity operations
      '__len__', 'Count', 'len', 'size', 'length', 'capacity', 'Cap',
      -- Removal / Clear operations
      'pop', 'RemoveAt', 'pop_back', 'clear', 'Clear', 'Delete'
  )
ORDER BY cc.concept, s.name, cc.lang;

```

---

## How This Curriculum Transitions Into Your Data Science Phase

Each of the 4 curriculum modules feeds directly into a corresponding `pandas` + `matplotlib` research notebook:

1. **Module I Queries (`comp_01` – `comp_03`)** $\rightarrow$ **Namespace & Dependency Graph DataFrame**: Plot container depth distributions and alias re-export networks.
2. **Module II Queries (`comp_04` – `comp_06`)** $\rightarrow$ **Signature & Ownership Matrix DataFrame**: Generate stacked bar charts of `pass_kind` and violin plots of callable arity + optional default ratios.
3. **Module III Queries (`comp_07` – `comp_09`)** $\rightarrow$ **Polymorphism & Concurrency Spectrum DataFrame**: Plot overload multiplicity curves and async/generator ratios.
4. **Module IV Queries (`comp_10` – `comp_12`)** $\rightarrow$ **Automated Crosswalk Extraction**: Export the joined query results directly as `universal_type_mappings` and `universal_protocol_mappings` tables for your Phase 4 normalizer.

Would you like me to generate the **Python Data Science analysis script (`utss_comparative_analysis.py` or Jupyter notebook)** next so you can run these exact aggregations across your 6 `.db` files and plot the comparative charts with `pandas` and `matplotlib`?









