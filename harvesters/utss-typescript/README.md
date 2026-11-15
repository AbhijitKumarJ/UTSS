# UTSS TypeScript - Universal Type & Symbol System Cataloger

An implementation of the **Universal Type & Symbol System (UTSS)** for **TypeScript and ECMAScript**, providing cross-language relational type and symbol introspection across Strata 0–3 using the standardized 11-table SQLite catalog architecture.

---

## 1. Dual-Layer Relational Architecture

The SQLite catalog maintains strict structural parity with universal UTSS standards across Python, C#, and Rust:

### Layer 1: Universal Language-Agnostic Core Tables (1–9)
| # | Table Name | Purpose |
|---|------------|---------|
| 1 | `environments` | Host platform triplet (`x64-linux`), runtime (`node`), language version (`5.7.3`). |
| 2 | `distributions` | Strata packaging units (`<ambient>`, `node_stdlib`, `commerce_engine`). |
| 3 | `containers` | Hierarchy: `ambient_scope`, `module`, `namespace`, `class`, `interface`, `enum`. |
| 4 | `symbols` | Functions, methods, properties, getters, setters, enum members, type aliases, keywords. |
| 5 | `callables` | Signature metadata, `is_async`, `is_generator`, `is_static`, `is_class_bound`, `return_type_expr`, `raw_signature`. |
| 6 | `callable_overloads` | Polymorphic function and method overload signatures. |
| 7 | `parameters` | Parameter names, pass kinds (`val`, `optional`, `rest`), type expressions, default values. |
| 8 | `state_members` | Class/interface fields, constants, variables, enum members, access modes (`read_only`, `read_write`). |
| 9 | `symbol_aliases` | Re-exports (`export * from ...`, `export { X }`), imports, and type aliases. |

### Layer 2: TypeScript Fidelity Facet Tables (10–11, 1:1 with Core)
| # | Table Name | Purpose |
|---|------------|---------|
| 10 | `ts_container_facets` | `item_kind` (`module`, `namespace`, `class`, `interface`, `enum`), `is_export`, `is_default_export`, `is_ambient`, `is_abstract`, `type_params_json`, `heritage_clauses_json` (`extends`, `implements`), `modifiers_json`. |
| 11 | `ts_symbol_facets` | `member_kind` (`function`, `method`, `property`, `getter`, `setter`, `constructor`, `enum_member`, `type_alias`, `variable`, `keyword`, `primitive`), `access_modifier` (`public`, `protected`, `private`), `is_readonly`, `is_optional`, `is_abstract`, `is_override`, `is_declare`, `type_annotation_json`, `modifiers_json`. |

---

## 2. Strata Architecture

### Stratum 0: Ambient Scope
Contains all language primitives, keywords, global utility types, and ambient builtins requiring zero imports:
- **74 Keywords**: Strict reserved keywords (`break`, `class`, `const`, `function`, `import`, `return`, `typeof`, etc.) and contextual/TS keywords (`type`, `interface`, `namespace`, `declare`, `abstract`, `as`, `any`, `unknown`, `never`, `readonly`, `satisfies`, `using`, etc.).
- **12 Primitive Types**: `string`, `number`, `boolean`, `bigint`, `symbol`, `undefined`, `null`, `any`, `unknown`, `never`, `void`, `object`.
- **21 Global Utility Types**: `Partial<T>`, `Required<T>`, `Readonly<T>`, `Record<K,T>`, `Pick<T,K>`, `Omit<T,K>`, `Exclude<T,U>`, `Extract<T,U>`, `NonNullable<T>`, `Parameters<T>`, `ConstructorParameters<T>`, `ReturnType<T>`, `InstanceType<T>`, `Awaited<T>`, etc.
- **61 Global Builtins**:
  - Global singletons: `globalThis`, `console`, `Math`, `JSON`, `Reflect`, `Atomics`, `Intl`.
  - Standard constructors: `Object`, `Array`, `Promise`, `Map`, `Set`, `Error`, `Date`, `RegExp`, `ArrayBuffer`, `DataView`, etc.
  - Global functions: `fetch`, `structuredClone`, `eval`, `isFinite`, `isNaN`, `parseFloat`, `parseInt`, `setTimeout`, `clearTimeout`, `queueMicrotask`, etc.

### Stratum 1: Standard Library / Runtime Modules
Provides two harvesting profiles:
1. **Recommended Profile (`--std-recommended`)**:
   - Curated Tier-1 standard runtime surface: `node:fs` (and `node:fs/promises`), `node:path`, `node:events` (`EventEmitter`), `node:crypto`, `node:stream` (`Readable`, `Writable`), `node:buffer` (`Buffer`), `node:util`, `node:os`, `node:http`, `node:process`.
   - Comprehensive function and method signatures, parameters, pass kinds (`val`, `optional`, `rest`), return types, and modifiers.
2. **Full Profile (`--std-full`)**:
   - Complete 46-module native Node.js / ECMAScript standard library distribution (`node:assert`, `node:child_process`, `node:cluster`, `node:crypto`, `node:dns`, `node:http2`, `node:net`, `node:sqlite`, `node:test`, `node:worker_threads`, `node:zlib`, etc.).

### Stratum 3: Workspace Pure AST Harvester
- Uses the official TypeScript Compiler API (`ts.createSourceFile`) with **zero dynamic code execution**.
- Extracts:
  - **Containers**: Modules (`SourceFile`), Classes, Interfaces, Enums.
  - **Symbols**: Methods, Constructors, Properties, Getters, Setters, Functions, Enum variants, Type aliases, Top-level constants/variables.
  - **Source Coordinates**: Exact 1-based source coordinate spans (`start_line`, `start_col`, `end_line`, `end_col`) matching Python, C#, and Rust conventions.
  - **Callable Modifiers**: `is_async` (e.g. `async processOrder`), `is_generator` (e.g. `*streamAuditEvents`), `is_static`, `is_class_bound`.
  - **Re-exports & Imports**: Recorded in `symbol_aliases` (`export * from ...`, `export { X }`).
  - **Embedded Demo**: Rich fixture `commerce_engine` containing `OrderStatus` enum, `CustomerId` type alias, `IOrderLine` interface, `Order` class with private fields and getters, `IOrderService` interface, and `OrderService` class.

---

## 3. Directory Layout

```
harvesters/utss-typescript/
├── package.json               # NPM package configuration and scripts
├── tsconfig.json              # TypeScript compiler configuration (NodeNext)
├── script.sh                  # Automated dual-profile generator & analytical queries
├── verify.sh                  # Comprehensive build & test verification runner
├── README.md                  # This documentation
├── src/
│   ├── index.ts               # Library entry point
│   ├── cli.ts                 # CLI executable entry point (utss-ts)
│   ├── schema.ts              # SQLite 11-table schema DDL & reset utilities
│   ├── models.ts              # TypeScript models and interfaces
│   ├── stratum0_ambient.ts    # Stratum 0 ambient keywords, primitives, builtins
│   ├── stratum1_std.ts        # Stratum 1 standard library multi-profile harvester
│   ├── stratum3_workspace.ts  # Stratum 3 pure AST workspace walker & demo fixture
│   ├── queries.ts             # Diagnostic queries and reporting utilities
│   └── tests/
│       └── integration.test.ts # Native node:test integration test suite
└── dist/                      # Compiled JavaScript and TypeScript declarations
```

---

## 4. Quick Start & CLI Usage

### Build and Run Tests
```bash
cd harvesters/utss-typescript
npm run build
npm test
```

### Harvest Profiles
```bash
# Harvest Recommended Tier-1 Catalog
node dist/cli.js harvest \
    --db catalog_ts_recommended.db \
    --reset \
    --stratum0 \
    --std-recommended \
    --demo-workspace

# Harvest Full Standard Library Distribution Catalog
node dist/cli.js harvest \
    --db catalog_ts_full.db \
    --reset \
    --stratum0 \
    --std-full \
    --demo-workspace

# Harvest an Arbitrary Physical Codebase Directory
node dist/cli.js harvest \
    --db catalog_custom.db \
    --reset \
    --stratum0 \
    --std-recommended \
    --workspace-dir ../my-typescript-project
```

### Audit Reports & Queries
```bash
# Print catalog spectrum report
node dist/cli.js report --db catalog_ts_recommended.db

# Inspect Stratum 0 ambient breakdown
node dist/cli.js query --db catalog_ts_recommended.db --ambient

# Inspect Stratum 3 workspace symbols with line/col coordinates
node dist/cli.js query --db catalog_ts_recommended.db --workspace-symbols

# Inspect TypeScript language fidelity facets
node dist/cli.js query --db catalog_ts_recommended.db --ts-facets
```

---

## 5. Automated Execution Scripts

- `./verify.sh`: Compiles TypeScript, executes the `node:test` integration test suite, and runs a verification catalog harvest.
- `./script.sh`: Generates both Profile 1 (`catalog_ts_recommended.db`) and Profile 2 (`catalog_ts_full.db`) and prints diagnostic spectrum, AST coordinates, and facet tables.
