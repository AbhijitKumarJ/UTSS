# UTSS Go - Universal Type & Symbol System Cataloger

An implementation of the **Universal Type & Symbol System (UTSS)** for **Go (targeting Go 1.27)**, providing cross-language relational type and symbol introspection across Strata 0–3 using the standardized 11-table SQLite catalog architecture.

---

## 1. Dual-Layer Relational Architecture

The SQLite catalog maintains strict structural parity with universal UTSS standards across Python, C#, Rust, TypeScript, and C++:

### Layer 1: Universal Language-Agnostic Core Tables (1–9)
| # | Table Name | Purpose |
|---|------------|---------|
| 1 | `environments` | Host platform triplet (`linux-amd64`), compiler (`gc`), language version (`go1.27.4`). |
| 2 | `distributions` | Strata packaging units (`<ambient>`, `std`, `commerce_engine`). |
| 3 | `containers` | Hierarchy: `ambient_scope`, `package`, `struct`, `interface`, `type`. |
| 4 | `symbols` | Functions, methods, struct fields, interface methods, constants, variables, keywords. |
| 5 | `callables` | Signature metadata, `is_static`, `is_class_bound`, `return_type_expr`, `raw_signature`, `signature_source`. |
| 6 | `callable_overloads` | Polymorphic overload variants placeholder. |
| 7 | `parameters` | Parameter names, pass kinds (`val`, `pointer`, `slice`, `variadic`), type expressions, default values. |
| 8 | `state_members` | Struct fields, package-level variables, constants, access modes (`read_only`, `read_write`). |
| 9 | `symbol_aliases` | Package import declarations (`import "commerce/models"`). |

### Layer 2: Go Fidelity Facet Tables (10–11, 1:1 with Core)
| # | Table Name | Purpose |
|---|------------|---------|
| 10 | `go_container_facets` | `package_name`, `item_kind` (`package`, `struct`, `interface`, `type_alias`), `type_params_json` (generics e.g. `[T any]`), `embedded_fields_json`, `is_exported`. |
| 11 | `go_symbol_facets` | `member_kind` (`func`, `method`, `field`, `const`, `var`, `type`, `builtin`), `receiver_kind` (`none`, `value`, `pointer`), `receiver_type` (`*Order`, `Order`), `is_exported`, `is_variadic`, `signature_json`. |

---

## 2. Strata Architecture

### Stratum 0: Ambient Scope
Contains all language specification predeclared keywords, fundamental types, constants, and builtins:
- **25 Keywords**: `break`, `case`, `chan`, `const`, `continue`, `default`, `defer`, `else`, `fallthrough`, `for`, `func`, `go`, `goto`, `if`, `import`, `interface`, `map`, `package`, `range`, `return`, `select`, `struct`, `switch`, `type`, `var`.
- **22 Predeclared Types**: `bool`, `byte`, `complex64`, `complex128`, `error`, `float32`, `float64`, `int`, `int8`, `int16`, `int32`, `int64`, `rune`, `string`, `uint`, `uint8`, `uint16`, `uint32`, `uint64`, `uintptr`, `any`, `comparable`.
- **4 Predeclared Constants & Identifiers**: `true`, `false`, `iota`, `nil`.
- **18 Predeclared Built-in Functions**: `append`, `cap`, `clear`, `close`, `complex`, `copy`, `delete`, `imag`, `len`, `make`, `max`, `min`, `new`, `panic`, `print`, `println`, `real`, `recover`.

### Stratum 1: Standard Library Packages
Provides two harvesting profiles:
1. **Recommended Profile (`--std-recommended`)**:
   - Curated Tier-1 standard library packages: `fmt`, `io`, `os`, `strings`, `strconv`, `time`, `sync`, `net/http`, `context`, `errors`, `path/filepath`.
   - Comprehensive function and method signatures, parameters, pass kinds (`val`, `pointer`, `slice`, `variadic`), return types, and interfaces.
2. **Full Profile (`--std-full`)**:
   - Complete 50+ package Go standard distribution (`archive/tar`, `bufio`, `bytes`, `compress/gzip`, `crypto/rand`, `crypto/sha256`, `database/sql`, `encoding/json`, `flag`, `math`, `net`, `os/exec`, `reflect`, `regexp`, `runtime`, `sort`, `testing`, `unsafe`, etc.).

### Stratum 3: Workspace Pure AST Harvester
- Pure static AST extraction using Go's official standard library packages (`go/parser`, `go/token`, `go/ast`) with **zero dynamic code execution**.
- Extracts:
  - **Containers**: Packages, Structs, Interfaces, Type definitions.
  - **Symbols**: Functions, Methods, Struct Fields, Interface Methods, Package Variables, Constants.
  - **Source Coordinates**: Exact 1-based source coordinate spans (`start_line`, `start_col`, `end_line`, `end_col`) from `token.Position`.
  - **Go Receiver Semantics**: Identifies value receivers (`(o Order)`) vs pointer receivers (`(o *Order)`), exported status (`ast.IsExported`), and variadic arguments (`...T`).
  - **Import Declarations**: Captured into `symbol_aliases`.
  - **Embedded Demo**: Rich fixture `commerce_engine` containing `OrderStatus` enum/type, `CustomerID` type alias, `OrderLine` struct, `Order` struct with pointer receiver methods (`AddItem`, `CalculateSubtotal`, `MarkPaid`), `IOrderService` interface, and `OrderService` implementation.

---

## 3. Directory Layout

```
harvesters/utss-go/
├── go.mod                     # Go module definition
├── go.sum                     # Checksums for dependencies (modernc.org/sqlite)
├── script.sh                  # Automated dual-profile generator & analytical queries
├── verify.sh                  # Comprehensive build & test verification runner
├── README.md                  # This documentation
├── cmd/
│   └── utss-go/
│       └── main.go            # CLI executable entry point (utss-go)
├── pkg/
│   ├── schema/
│   │   └── schema.go          # SQLite 11-table schema DDL & initialization
│   ├── models/
│   │   └── models.go          # Go structs matching universal relational schema
│   ├── stratum0/
│   │   └── ambient.go         # Stratum 0 ambient keywords, primitives, builtins
│   ├── stratum1/
│   │   └── std.go             # Standard library multi-profile harvester
│   ├── stratum3/
│   │   └── workspace.go       # Pure AST workspace walker & demo fixture
│   └── queries/
│       └── queries.go         # Analytical query and reporting utilities
├── tests/
│   └── integration_test.go    # Unit & integration test suite
└── bin/                       # Output binary (utss-go)
```

---

## 4. Quick Start & CLI Usage

### Build and Run Tests
```bash
cd harvesters/utss-go
go build -o bin/utss-go ./cmd/utss-go
go test -v ./tests
```

### Harvest Profiles
```bash
# Harvest Recommended Tier-1 Catalog
./bin/utss-go harvest \
    --db catalog_go_recommended.db \
    --reset \
    --stratum0 \
    --std-recommended \
    --demo-workspace

# Harvest Full Standard Library Distribution Catalog
./bin/utss-go harvest \
    --db catalog_go_full.db \
    --reset \
    --stratum0 \
    --std-full \
    --demo-workspace

# Harvest an Arbitrary Physical Codebase Directory
./bin/utss-go harvest \
    --db catalog_custom.db \
    --reset \
    --stratum0 \
    --std-recommended \
    --workspace-dir ../my-go-project
```

### Audit Reports & Queries
```bash
# Print catalog spectrum report
./bin/utss-go report --db catalog_go_recommended.db

# Inspect Stratum 0 ambient breakdown
./bin/utss-go query --db catalog_go_recommended.db --ambient

# Inspect Stratum 3 workspace symbols with line/col coordinates
./bin/utss-go query --db catalog_go_recommended.db --workspace-symbols

# Inspect Go language fidelity facets
./bin/utss-go query --db catalog_go_recommended.db --go-facets
```

---

## 5. Automated Execution Scripts

- `./verify.sh`: Compiles Go, executes the integration test suite, and runs a verification catalog harvest.
- `./script.sh`: Generates both Profile 1 (`catalog_go_recommended.db`) and Profile 2 (`catalog_go_full.db`) and prints diagnostic spectrum, AST coordinates, and facet tables.
