# UTSS C# (.NET 10.0) - Universal Type & Symbol System Cataloger

An implementation of the **Universal Type & Symbol System (UTSS)** for **C# and the .NET ecosystem**, mirroring the dual-layer relational catalog architecture of the Python engine.

---

## 1. Dual-Layer Relational Architecture

The SQLite catalog maintains strict structural parity with universal UTSS standards across its 11 tables:

### Layer 1: Universal Language-Agnostic Core Tables (1–9)
| # | Table Name | Purpose |
|---|------------|---------|
| 1 | `environments` | Host platform triplet, OS, runtime (`.NET`), language version (`10.0`). |
| 2 | `distributions` | Strata-based packaging units (`<ambient>`, `System.Runtime`, `<workspace>`). |
| 3 | `containers` | Hierarchy: `ambient_scope`, `namespace`, `class`, `struct`, `record`, `interface`, `enum`. |
| 4 | `symbols` | Directory of symbols: `keyword`, `type_alias`, `method`, `constructor`, `property`, `field`, etc. |
| 5 | `callables` | Signature metadata, `is_async`, `is_generator`, `is_static`, `has_overloads`, `return_type_expr`. |
| 6 | `callable_overloads` | Ordered 1..N polymorphic method overloads. |
| 7 | `parameters` | Positional/named parameters, pass kind (`value`, `ref`, `out`, `in`, `params`), defaults. |
| 8 | `state_members` | Properties, fields, constants, access modes (`read_only`, `read_write`, `init_only`). |
| 9 | `symbol_aliases` | Using aliases (`using ProjectOrder = ...;`) and global usings. |

### Layer 2: C# Fidelity Facet Tables (10–11, 1:1 with Core)
| # | Table Name | Purpose |
|---|------------|---------|
| 10 | `cs_container_facets` | `type_kind` (`record`, `interface`, `struct`, `class`), `is_sealed`, `is_abstract`, `is_static`, `is_readonly_struct`, `is_ref_struct`, `base_type_qname`, `implemented_interfaces_json`, `generic_type_parameters_json`. |
| 11 | `cs_symbol_facets` | `member_kind` (`method`, `property`, `field`, `constructor`, `operator`), `is_virtual`, `is_override`, `is_abstract`, `is_sealed`, `is_async`, `is_extension_method`, `is_init_only`, `has_getter`, `has_setter`. |

---

## 2. Strata Architecture

- **Stratum 0 (Ambient Scope)**:
  - 121 C# reserved and contextual keywords (`record`, `async`, `await`, `init`, `yield`, `var`, etc.).
  - 18 primitive type aliases (`int` $\to$ `System.Int32`, `string` $\to$ `System.String`, `bool` $\to$ `System.Boolean`, etc.).
  - Default implicit global usings (`System`, `System.Collections.Generic`, `System.IO`, `System.Linq`, `System.Threading.Tasks`).
- **Stratum 1 (Runtime BCL)**:
  - Reflection-based metadata extraction over loaded CoreCLR assemblies (`System.Private.CoreLib`, `System.Runtime`).
  - Method overloads, return types, parameter pass kinds, interfaces, and type hierarchy.
- **Stratum 3 (Workspace Source AST)**:
  - **Pure static Roslyn parsing** (`Microsoft.CodeAnalysis.CSharp.CSharpSyntaxTree` + `CSharpSyntaxWalker`).
  - Zero code execution and zero dynamic assembly loading.
  - Exact source coordinates: `start_line`, `start_col`, `end_line`, `end_col`.
  - Record primary constructor parameter synthesis (generates both constructor parameters and `init_only` properties).
  - Scope-bounded generator detection (`yield return` / `yield break`).
  - Extension method detection (`this` parameter modifier on static methods).
  - Using alias capture (`using Alias = Target;`).
  - Embedded self-contained demo workspace: `CommerceEngine`.

---

## 3. CLI Usage

### Build Solution
```bash
dotnet build UTSS.CSharp.slnx
```

### Run Tests
```bash
dotnet test UTSS.CSharp.slnx
```

### Harvest Metadata
```bash
# Recommended synthesis profile (Curated Tier-1 BCL: System, Linq, Collections, IO, Json, etc.)
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- \
    harvest --db catalog_cs_recommended.db --reset --stratum0 --bcl-recommended --demo-workspace

# Full base catalog profile (Full CoreCLR reflection across 1,400+ public types in assemblies)
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- \
    harvest --db catalog_cs_full.db --reset --stratum0 --bcl-full --demo-workspace

# Harvest specific custom workspace
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- \
    harvest --db catalog_cs.db --workspace /path/to/csharp/project
```

### Diagnostic Catalog Report
```bash
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- report --db catalog_cs_recommended.db
```

### Diagnostic Queries
```bash
# Query ambient keywords, primitive aliases, and ambient literals
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- query --db catalog_cs_recommended.db --ambient

# Query BCL breakdown by container type kind (class, struct, interface, enum, delegate)
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- query --db catalog_cs_full.db --bcl-summary

# Query top polymorphic method overloads in .NET CoreCLR
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- query --db catalog_cs_full.db --bcl-overloads

# Query generic type parameters and implemented interfaces
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- query --db catalog_cs_full.db --bcl-generics

# Query workspace symbols with exact AST line/col coordinates
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- query --db catalog_cs_recommended.db --workspace-symbols

# Query C# Container & Symbol Facets (records, interfaces, async methods, extension methods)
dotnet run --project src/UTSS.CSharp/UTSS.CSharp.csproj -- query --db catalog_cs_recommended.db --facets
```

### Automated End-to-End Profile Script
```bash
# Executes both Recommended & Full Base Catalog generation + deep analysis queries:
./script.sh
```
