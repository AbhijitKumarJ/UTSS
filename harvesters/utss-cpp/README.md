# UTSS C/C++ - Universal Type & Symbol System Cataloger

An implementation of the **Universal Type & Symbol System (UTSS)** for **C and C++ (targeting modern ISO C++20)**, providing cross-language relational type and symbol introspection across Strata 0–3 using the standardized 11-table SQLite catalog architecture.

---

## 1. Dual-Layer Relational Architecture

The SQLite catalog maintains strict structural parity with universal UTSS standards across Python, C#, Rust, and TypeScript:

### Layer 1: Universal Language-Agnostic Core Tables (1–9)
| # | Table Name | Purpose |
|---|------------|---------|
| 1 | `environments` | Host platform triplet (`x86_64-linux-gnu`), compiler (`g++`), language version (`C++20`). |
| 2 | `distributions` | Strata packaging units (`<ambient>`, `libstdc++`, `commerce_engine`). |
| 3 | `containers` | Hierarchy: `ambient_scope`, `file`, `namespace`, `class`, `struct`, `union`, `enum`. |
| 4 | `symbols` | Functions, methods, constructors, destructors, operators, fields, enum members, type aliases, keywords. |
| 5 | `callables` | Signature metadata, `is_static`, `is_class_bound`, `return_type_expr`, `raw_signature`, `signature_source`. |
| 6 | `callable_overloads` | Function and method overload signatures. |
| 7 | `parameters` | Parameter names, pass kinds (`val`, `ref`, `const_ref`, `rvalue_ref`, `pointer`), type expressions, default values. |
| 8 | `state_members` | Fields, static members, constants, enum constants, access modes (`read_only`, `read_write`). |
| 9 | `symbol_aliases` | `#include` header directives and `using` type aliases. |

### Layer 2: C++ Fidelity Facet Tables (10–11, 1:1 with Core)
| # | Table Name | Purpose |
|---|------------|---------|
| 10 | `cpp_container_facets` | `item_kind` (`namespace`, `class`, `struct`, `enum`, `enum_class`, `union`, `concept`), `is_template`, `template_params_json`, `base_classes_json` (`public IOrderService`), `is_final`, `is_abstract`, `attributes_json`. |
| 11 | `cpp_symbol_facets` | `member_kind` (`function`, `method`, `constructor`, `destructor`, `operator`, `field`, `enum_constant`, `type_alias`, `macro`), `access_specifier` (`public`, `protected`, `private`), `is_virtual`, `is_pure_virtual`, `is_override`, `is_const`, `is_noexcept`, `is_constexpr`, `is_inline`, `is_static`, `pass_by`, `attributes_json`. |

---

## 2. Strata Architecture

### Stratum 0: Ambient Scope
Contains all language fundamental types, keywords, and ambient constants/macros:
- **97 Keywords (ISO C++20)**: `alignas`, `auto`, `class`, `concept`, `const`, `constexpr`, `co_await`, `co_return`, `decltype`, `explicit`, `friend`, `inline`, `mutable`, `namespace`, `noexcept`, `nullptr`, `override`, `requires`, `static_assert`, `template`, `virtual`, `volatile`, etc.
- **24 Fundamental Primitive Types**: `void`, `bool`, `char`, `signed char`, `unsigned char`, `char8_t`, `char16_t`, `char32_t`, `wchar_t`, `short`, `unsigned short`, `int`, `unsigned int`, `long`, `unsigned long`, `long long`, `unsigned long long`, `float`, `double`, `long double`, `std::nullptr_t`, `size_t`, `ptrdiff_t`, `intptr_t`.
- **Predefined Macros & Built-in Constants**: `nullptr`, `true`, `false`, `NULL`, `__cplusplus`, `__FILE__`, `__LINE__`, `__DATE__`, `__TIME__`, `__func__`.

### Stratum 1: Standard Library Headers
Provides two harvesting profiles:
1. **Recommended Profile (`--std-recommended`)**:
   - Curated Tier-1 standard C/C++ runtime headers: `<iostream>`, `<vector>`, `<string>`, `<memory>` (`std::unique_ptr`, `std::shared_ptr`, `std::make_unique`), `<filesystem>`, `<utility>`, `<algorithm>`, `<cstdio>`, `<cstdlib>`.
   - Comprehensive function and method signatures, parameters, pass kinds (`val`, `const_ref`, `rvalue_ref`, `pointer`), return types, and qualifiers.
2. **Full Profile (`--std-full`)**:
   - Complete 64-header ISO C++20 standard library distribution (`<array>`, `<deque>`, `<map>`, `<set>`, `<unordered_map>`, `<span>`, `<format>`, `<ranges>`, `<thread>`, `<atomic>`, `<coroutine>`, `<chrono>`, `<cmath>`, `<cstring>`, etc.).

### Stratum 3: Workspace Pure AST Harvester
- Pure static lexical AST extraction for C and C++ header and source files (`.hpp`, `.h`, `.cpp`, `.cc`) with **zero dynamic code execution**.
- Extracts:
  - **Containers**: Files, Namespaces, Classes, Structs, Enums, Scoped Enums (`enum class`).
  - **Symbols**: Constructors, Destructors, Methods, Member Fields, Functions, Enum variants, Type aliases (`using X = Y;`).
  - **Source Coordinates**: Exact 1-based source coordinate spans (`start_line`, `start_col`, `end_line`, `end_col`) matching Python, C#, Rust, and TypeScript conventions.
  - **C++ Modifiers**: `is_virtual`, `is_pure_virtual` (`= 0`), `is_override`, `is_const` (`const`), `is_noexcept`, `access_specifier` (`public`, `protected`, `private`).
  - **Include Directives**: Captured into `symbol_aliases` (`#include <string>`, `#include "models/order.hpp"`).
  - **Embedded Demo**: Rich fixture `commerce_engine` containing `OrderStatus` enum class, `CustomerId` type alias, `OrderLine` struct, `Order` class with private fields and getters, `IOrderService` abstract interface, and `OrderService` implementation.

---

## 3. Directory Layout

```
harvesters/utss-cpp/
├── Makefile                   # High-performance C++20 Makefile
├── script.sh                  # Automated dual-profile generator & analytical queries
├── verify.sh                  # Comprehensive build & test verification runner
├── README.md                  # This documentation
├── third_party/
│   └── sqlite3/               # Bundled official SQLite3 amalgamation (zero external deps)
│       ├── sqlite3.h
│       ├── sqlite3.c
│       └── sqlite3.o
├── include/
│   └── utss/
│       ├── schema.hpp         # SQLite 11-table schema DDL & RAII wrappers
│       ├── models.hpp         # C++ models and records
│       ├── stratum0_ambient.hpp
│       ├── stratum1_std.hpp   # Standard library multi-profile harvester
│       ├── stratum3_workspace.hpp # Pure AST workspace walker & demo fixture
│       └── queries.hpp        # Analytical query and reporting utilities
├── src/
│   ├── main.cpp               # CLI executable entry point (utss-cpp)
│   ├── schema.cpp
│   ├── stratum0_ambient.cpp
│   ├── stratum1_std.cpp
│   ├── stratum3_workspace.cpp
│   └── queries.cpp
├── tests/
│   └── test_main.cpp          # Unit & integration test suite
└── bin/                       # Output binaries (utss-cpp, test_utss)
```

---

## 4. Quick Start & CLI Usage

### Build and Run Tests
```bash
cd harvesters/utss-cpp
make all
make test
```

### Harvest Profiles
```bash
# Harvest Recommended Tier-1 Catalog
./bin/utss-cpp harvest \
    --db catalog_cpp_recommended.db \
    --reset \
    --stratum0 \
    --std-recommended \
    --demo-workspace

# Harvest Full Standard Library Distribution Catalog
./bin/utss-cpp harvest \
    --db catalog_cpp_full.db \
    --reset \
    --stratum0 \
    --std-full \
    --demo-workspace

# Harvest an Arbitrary Physical Codebase Directory
./bin/utss-cpp harvest \
    --db catalog_custom.db \
    --reset \
    --stratum0 \
    --std-recommended \
    --workspace-dir ../my-cpp-project
```

### Audit Reports & Queries
```bash
# Print catalog spectrum report
./bin/utss-cpp report --db catalog_cpp_recommended.db

# Inspect Stratum 0 ambient breakdown
./bin/utss-cpp query --db catalog_cpp_recommended.db --ambient

# Inspect Stratum 3 workspace symbols with line/col coordinates
./bin/utss-cpp query --db catalog_cpp_recommended.db --workspace-symbols

# Inspect C++ language fidelity facets
./bin/utss-cpp query --db catalog_cpp_recommended.db --cpp-facets
```

---

## 5. Automated Execution Scripts

- `./verify.sh`: Compiles C++, executes the unit and integration test suite, and runs a verification catalog harvest.
- `./script.sh`: Generates both Profile 1 (`catalog_cpp_recommended.db`) and Profile 2 (`catalog_cpp_full.db`) and prints diagnostic spectrum, AST coordinates, and facet tables.
