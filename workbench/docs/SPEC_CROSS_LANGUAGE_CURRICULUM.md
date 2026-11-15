# Specification: 10-Lesson Cross-Language Curriculum

This document specifies the **Cross-Language Synthesis & Transpiler Impedance Curriculum** (10 lessons across 4 structural tracks) executed against the **Federated Multi-Language Engine** (`federated_recommended` / `federated_full`).

---

## Curriculum Structure Overview

| Track | Sequence | Lesson ID | Title | Key Transpiler Question |
| :--- | :---: | :--- | :--- | :--- |
| **I. Scope & Packaging** | 1 | `cross_01_ambient_baseline` | The Ambient Baseline (Stratum 0 Globals) | What symbols exist with zero imports (`len`, `int`, `Result`, `Promise`, `println!`)? |
| **I. Scope & Packaging** | 2 | `cross_02_namespace_topology` | Namespace Topology & Re-Export Facades | How deeply nested are containers, and how do facades re-export internals? |
| **II. Memory & Passing** | 3 | `cross_03_parameter_passing` | Parameter Passing & Ownership Matrix | How do Python kw-args map to Rust `&mut`, C++ `const&`, Go pointers, C# `in`/`out`? |
| **II. Memory & Passing** | 4 | `cross_04_mutability_guarantees` | Mutability & Value vs Reference Semantics | Where is immutability default (Rust, C# readonly struct) vs opt-in (`const`, `Final`)? |
| **III. Polymorphism** | 5 | `cross_05_overload_multiplicity` | Static Overloading vs Dynamic Dispatch | How do C#/C++ overloads contrast with Python `@overload` and Go/Rust zero-overload? |
| **III. Polymorphism** | 6 | `cross_06_structural_vs_nominal` | Structural vs Nominal Contracts | How do Python dunders map to C# interfaces, Rust traits, and Go implicit interfaces? |
| **III. Polymorphism** | 7 | `cross_07_generic_bounds` | Generics & Type Parameter Constraints | How are generic bounds expressed across `[T any]`, `where T: Trait`, `where T : class`? |
| **IV. Execution & Safety** | 8 | `cross_08_async_state_machines` | Async Coroutines & State Machines | How prevalent are `is_async` callables across languages vs Go's goroutine model? |
| **IV. Execution & Safety** | 9 | `cross_09_error_paradigms` | Error Handling & Safety Boundaries | Where do stdlibs rely on exceptions vs algebraic `Result<T, E>` / `(T, error)`? |
| **IV. Execution & Safety** | 10 | `cross_10_rosetta_crosswalk` | The Rosetta Crosswalk (Canonical Collections)| What are the exact method counterparts for Sequence and Map across all 6 stdlibs? |

---

## Detailed Lesson Specifications

### Track I: Scope & Packaging

#### Lesson 1: The Ambient Baseline (Stratum 0 Globals)
- **ID**: `cross_01_ambient_baseline`
- **Suite**: `comparative` | **Level**: `Basic` | **Sequence**: 1
- **Focus**: Evaluates the symbol budget granted automatically by each language with zero imports.
- **SQL Template**:
  ```sql
  SELECT 
      e.language,
      s.symbol_kind,
      COUNT(s.symbol_id) AS symbol_count,
      GROUP_CONCAT(s.name, ', ') AS sample_symbols
  FROM v_all_symbols s
  JOIN v_all_distributions d ON s.dist_id = d.dist_id AND s.language = d.language
  JOIN v_all_environments e ON s.language = e.language
  WHERE d.stratum = 0
  GROUP BY e.language, s.symbol_kind
  ORDER BY e.language ASC, symbol_count DESC;
  ```
- **Transpiler Insight**: Informs the code generator which primitives and helper functions can be emitted bare vs which require importing standard modules (e.g. `println!` in Rust vs `fmt.Println` in Go).

---

#### Lesson 2: Namespace Topology & Re-Export Facades
- **ID**: `cross_02_namespace_topology`
- **Suite**: `comparative` | **Level**: `Basic` | **Sequence**: 2
- **Focus**: Compares how standard libraries organize containers (flat Go packages vs deep C# namespaces vs C++ nested namespaces) and how `symbol_aliases` re-export internal definitions.
- **SQL Template**:
  ```sql
  SELECT 
      c.language,
      c.container_kind,
      COUNT(c.container_id) AS container_count,
      AVG(LENGTH(c.qualified_name) - LENGTH(REPLACE(c.qualified_name, '.', '')) + 1) AS avg_dot_depth
  FROM v_all_containers c
  WHERE c.stratum = 1
  GROUP BY c.language, c.container_kind
  ORDER BY c.language ASC, container_count DESC;
  ```
- **Transpiler Insight**: Determines whether the transpiler should preserve deep module hierarchies or flatten code into single packages/modules when targeting Go or C.

---

### Track II: Memory & Parameter Passing

#### Lesson 3: Parameter Passing & Ownership Matrix
- **ID**: `cross_03_parameter_passing`
- **Suite**: `comparative` | **Level**: `Intermediate` | **Sequence**: 3
- **Focus**: Profiles the parameter passing conventions across all 6 ecosystems.
- **SQL Template**:
  ```sql
  SELECT 
      p.language,
      p.pass_kind,
      COUNT(*) AS total_params,
      ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY p.language), 2) AS pct_of_language
  FROM v_all_parameters p
  WHERE p.pass_kind IS NOT NULL
  GROUP BY p.language, p.pass_kind
  ORDER BY p.language ASC, total_params DESC;
  ```
- **Transpiler Insight**: Direct mapping matrix for parameter lowering: flags when a Python reference pass must become a Rust `&mut T` or a C# `ref T` to preserve mutability semantics.

---

#### Lesson 4: Mutability Guarantees: Default Immutability vs Explicit Modifiers
- **ID**: `cross_04_mutability_guarantees`
- **Suite**: `comparative` | **Level**: `Intermediate` | **Sequence**: 4
- **Focus**: Measures where immutability is the compiler default (Rust bindings, C# `readonly struct`, TypeScript `readonly`) vs opt-in.
- **SQL Template**:
  ```sql
  SELECT 
      m.language,
      COUNT(*) AS total_state_members,
      SUM(CASE WHEN m.is_constant = 1 THEN 1 ELSE 0 END) AS constant_members,
      SUM(CASE WHEN m.is_mutable = 0 THEN 1 ELSE 0 END) AS immutable_members,
      ROUND(100.0 * SUM(CASE WHEN m.is_mutable = 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS immutability_pct
  FROM v_all_state_members m
  GROUP BY m.language
  ORDER BY immutability_pct DESC;
  ```
- **Transpiler Insight**: Critical for memory safety: when transpiling mutable Python dictionaries or classes into Rust, identifies state that must be wrapped in `Cell<T>`, `RefCell<T>`, or `Arc<Mutex<T>>`.

---

### Track III: Polymorphism & Contracts

#### Lesson 5: Static Overloading vs Dynamic Dispatch
- **ID**: `cross_05_overload_multiplicity`
- **Suite**: `comparative` | **Level**: `Intermediate` | **Sequence**: 5
- **Focus**: Analyzes the presence and density of function overloading across language standard libraries.
- **SQL Template**:
  ```sql
  SELECT 
      c.language,
      COUNT(c.symbol_id) AS total_callables,
      SUM(CASE WHEN c.has_overloads = 1 THEN 1 ELSE 0 END) AS overloaded_callables,
      MAX(c.overload_count) AS max_overloads_for_single_name,
      ROUND(AVG(CASE WHEN c.has_overloads = 1 THEN c.overload_count ELSE 1 END), 2) AS avg_overload_multiplicity
  FROM v_all_callables c
  GROUP BY c.language
  ORDER BY overloaded_callables DESC;
  ```
- **Transpiler Insight**: Quantifies how often a C# or C++ overload cluster (e.g. 14 overloads of `Console.WriteLine` or `std::basic_string::append`) must be lower to named variants (`write_line_str`, `write_line_int`) when targeting Go or Rust.

---

#### Lesson 6: Structural vs Nominal Contracts (Dunders to Traits & Interfaces)
- **ID**: `cross_06_structural_vs_nominal`
- **Suite**: `comparative` | **Level**: `Advanced` | **Sequence**: 6
- **Focus**: Maps behavioral contracts across dynamic protocols (`__iter__`, `__len__`), static interfaces (`IEnumerable`, `IReadOnlyList`), traits (`Iterator`, `Display`), and Go structural interfaces (`io.Reader`).
- **SQL Template**:
  ```sql
  SELECT 
      c.language,
      c.container_kind,
      COUNT(*) AS contract_count,
      GROUP_CONCAT(c.short_name, ', ') AS sample_contracts
  FROM v_all_containers c
  WHERE c.container_kind IN ('interface', 'trait', 'concept')
  GROUP BY c.language, c.container_kind
  ORDER BY contract_count DESC;
  ```
- **Transpiler Insight**: Provides the structural backbone for the Universal Bridge Protocol Normalization layer.

---

#### Lesson 7: Generic Type Parameters & Bound Constraints
- **ID**: `cross_07_generic_bounds`
- **Suite**: `comparative` | **Level**: `Advanced` | **Sequence**: 7
- **Focus**: Profiles generic type parameter usage and constraint annotations across callables and containers.
- **SQL Template**:
  ```sql
  SELECT 
      c.language,
      COUNT(c.symbol_id) AS total_callables,
      SUM(CASE WHEN c.type_params_json IS NOT NULL AND c.type_params_json != '[]' THEN 1 ELSE 0 END) AS generic_callables
  FROM v_all_callables c
  GROUP BY c.language
  ORDER BY generic_callables DESC;
  ```
- **Transpiler Insight**: Guides code generation of type parameter lists and where-clause boundaries in target code.

---

### Track IV: Execution & Safety

#### Lesson 8: Async Coroutines, State Machines & Event Loop Mechanics
- **ID**: `cross_08_async_state_machines`
- **Suite**: `comparative` | **Level**: `Advanced` | **Sequence**: 8
- **Focus**: Evaluates the prevalence of `async` and `generator` functions across standard libraries.
- **SQL Template**:
  ```sql
  SELECT 
      c.language,
      COUNT(c.symbol_id) AS total_callables,
      SUM(CASE WHEN c.is_async = 1 THEN 1 ELSE 0 END) AS async_callables,
      SUM(CASE WHEN c.is_generator = 1 THEN 1 ELSE 0 END) AS generator_callables
  FROM v_all_callables c
  GROUP BY c.language
  ORDER BY async_callables DESC;
  ```
- **Transpiler Insight**: Explains why Go requires no `is_async` callables (all I/O is synchronously written and multiplexed on goroutines), contrasting with C# Task state machines, Python asyncio, and Rust Future poll-based models.

---

#### Lesson 9: Error Handling Paradigms: Exceptions vs Algebraic Result Types
- **ID**: `cross_09_error_paradigms`
- **Suite**: `comparative` | **Level**: `Advanced` | **Sequence**: 9
- **Focus**: Contrasts exception hierarchies (`exception_class` in Python/C#) against algebraic error return types (`Result<T, E>` in Rust, `(T, error)` in Go).
- **SQL Template**:
  ```sql
  SELECT 
      c.language,
      COUNT(CASE WHEN c.container_kind = 'exception_class' THEN 1 END) AS declared_exception_classes,
      COUNT(CASE WHEN cal.return_type_expr LIKE '%Result%' OR cal.return_type_expr LIKE '%error%' THEN 1 END) AS error_returning_callables
  FROM v_all_containers c
  LEFT JOIN v_all_callables cal ON c.container_id = cal.container_id AND c.language = cal.language
  GROUP BY c.language
  ORDER BY declared_exception_classes DESC;
  ```
- **Transpiler Insight**: Highlights the lowering strategy: converting thrown exceptions into `Result<T, E>` matching blocks or Go `if err != nil` guards.

---

#### Lesson 10: The Rosetta Crosswalk (Canonical Collections & Streams)
- **ID**: `cross_10_rosetta_crosswalk`
- **Suite**: `comparative` | **Level**: `Advanced` | **Sequence**: 10
- **Focus**: Directly joins the 6 catalogs on canonical core operations (`append`, `push`, `add`, `len`, `count`, `clear`).
- **SQL Template**:
  ```sql
  SELECT 
      s.language,
      s.name AS method_name,
      c.short_name AS container_name,
      cal.return_type_expr,
      cal.raw_signature
  FROM v_all_symbols s
  JOIN v_all_containers c ON s.container_id = c.container_id AND s.language = c.language
  JOIN v_all_callables cal ON s.symbol_id = cal.symbol_id AND s.language = cal.language
  WHERE s.name IN ('append', 'push', 'push_back', 'Add', 'len', 'Count', 'size', 'length', 'clear', 'Clear')
  ORDER BY s.name ASC, s.language ASC
  LIMIT 50;
  ```
- **Transpiler Insight**: Verifies that the compiler's universal method substitution dictionary matches live symbols in all target standard libraries.
