# UTSS CLI Reference Manual

**Tool Name:** `utss` (Python Harvester CLI)  
**Version:** 0.2.0  
**Runtime:** Python 3.13+ (`uv run utss`)  
**Location:** [`harvesters/utss-python/`](../harvesters/utss-python/)

> [!NOTE]
> This manual documents the `utss` CLI for the Python catalog harvester. For the unified multi-language catalog harvester across all 6 languages, use [`./harvest_all.sh`](../harvest_all.sh). For the individual language harvester CLIs, see `harvesters/utss-*/README.md`.

The Universal Type & Symbol System (UTSS) provides a command-line interface designed for both interactive developer exploration and automated integration into transpiler build pipelines.

---

## 1. Global Invocations & Options

UTSS can be invoked directly through `uv` or standard Python:

```bash
# Via uv CLI alias:
uv run utss [SUBCOMMAND] [OPTIONS]

# Via entrypoint script directly:
uv run python main.py [SUBCOMMAND] [OPTIONS]
```

### Global Options

| Option | Flag | Description |
| :--- | :--- | :--- |
| Database Path | `--db <path>` | Target SQLite database file. Defaults to `catalog.db` in current directory. |
| Help | `-h`, `--help` | Show command usage and argument documentation. |

---

## 2. Command: `harvest`

The `harvest` command performs empirical discovery across Concentric Strata (Stratum 0 Ambient, Stratum 1 Stdlib, Stratum 2 Virtualenv Ecosystem, and Stratum 3 Local Workspace AST), optionally executing Pass 4 Static Typeshed Overlay.

### Synopsis

```bash
uv run utss harvest [--db <path>] [OPTIONS]
```

### Options

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--db` | `PATH` | `catalog.db` | Target SQLite database file. |
| `--workspace` | `PATH` | `.` | Root directory of local project workspace to index via static AST (Stratum 3). |
| `--workspace-name`| `STRING`| `workspace` | Logical distribution name assigned to Stratum 3 symbols. |
| `--stdlib-modules`| `STRING...` | `None` | Explicit list of standard library module names to harvest (e.g. `sys os io json`). |
| `--sample-stdlib` | `FLAG` | `False` | Quickly harvests a curated representative sample of 12 standard modules (`sys`, `os`, `io`, `_io`, `json`, `math`, `time`, `pathlib`, `collections`, `abc`, `functools`, `typing`). |
| `--demo-stubs` | `FLAG` | `False` | Applies embedded zero-dependency Typeshed stubs for core modules (`builtins`, `sys`, `os`, `json`). |
| `--demo-workspace`| `FLAG` | `False` | Creates and indexes an embedded multi-file demo project (`commerce_engine`) in a temporary sandbox. |
| `--typeshed-dir` | `PATH` | `None` | Directory containing full Typeshed repository checkout (`stdlib/` and `stubs/`). |
| `--reset` | `FLAG` | `False` | Drops existing schema tables before harvesting fresh data. |

### Practical Examples

#### 1. Quick Development Harvest with Demo Typeshed Stubs & Demo Workspace
```bash
uv run utss harvest --db catalog.db --sample-stdlib --demo-stubs --demo-workspace --reset
```

#### 2. Comprehensive Harvest of Entire Stdlib + Active Virtualenv + Local Code
```bash
uv run utss harvest --db full_catalog.db --workspace . --typeshed-dir /path/to/typeshed --reset
```

#### 3. Targeted Harvest of Specific Core Modules
```bash
uv run utss harvest --db target.db --stdlib-modules sys os io _io json math --demo-stubs --reset
```

---

## 3. Command: `overlay`

The `overlay` command applies static `.pyi` type stubs (Typeshed) to an *existing* UTSS database without re-harvesting the underlying runtime environment. It performs static guard evaluation (`sys.version_info` and `sys.platform`), enriches untyped C-builtins, captures `@overload` sets, and restores erased generic variables.

### Synopsis

```bash
uv run utss overlay [--db <path>] (--demo-stubs | --typeshed-dir <path>)
```

### Options

| Option | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `--db` | `PATH` | `catalog.db` | Target SQLite database file. |
| `--demo-stubs` | `FLAG` | `False` | Apply embedded zero-dependency demo stubs for `builtins`, `sys`, `os`, `json`. |
| `--typeshed-dir` | `PATH` | `None` | Apply full Typeshed directory (`stdlib/` and `stubs/`). |

### Practical Examples

#### Overlay Embedded Stubs
```bash
uv run utss overlay --db catalog.db --demo-stubs
```

#### Overlay Custom External Typeshed Stubs
```bash
uv run utss overlay --db catalog.db --typeshed-dir /usr/local/share/typeshed
```

---

## 4. Command: `report`

The `report` command prints an empirical diagnostic summary of an existing database, breaking down symbols by stratum, origin kind, visibility, re-exports, and overload sets.

### Synopsis

```bash
uv run utss report [--db <path>]
```

### Example Output

```text
======================================================================
 PYTHON SPECTRUM CATALOG SUMMARY (catalog.db)
======================================================================
 Runtime   : CPython 3.13.12 on Linux-x86_64 (/home/user/UTSS/.venv/bin/python, platform=linux)

--- 1. Containers by Stratum & Origin Kind ---
  [Stratum 0: <ambient>      ] ambient_scope  (ambient     ) -> Public:    1, Hidden (_):    0
  [Stratum 1: python-stdlib  ] module         (builtin_c   ) -> Public:    2, Hidden (_):    1
  [Stratum 1: python-stdlib  ] module         (frozen      ) -> Public:    2, Hidden (_):    0
  [Stratum 1: python-stdlib  ] package        (pure_python ) -> Public:    1, Hidden (_):    0

--- 2. Symbols by Stratum, Kind & Visibility ---
  [Stratum 0] method         | vis=system_dunder     | prov=defined_here    :    439
  [Stratum 0] method         | vis=public_implicit   | prov=defined_here    :    223
  [Stratum 0] constructor    | vis=system_dunder     | prov=defined_here    :    149
  [Stratum 0] function       | vis=public_implicit   | prov=pyi_enriched    :      5
  [Stratum 1] method         | vis=public_implicit   | prov=defined_here    :    275
  [Stratum 1] function       | vis=exported_all      | prov=re_exported     :    172

--- 3. Cross-Module Re-Exports & C-Accelerator Aliases (Sample) ---
  io.BufferedReader           -> _io.BufferedReader           (c_accelerator_reexport)
  io.open                     -> _io.open                     (c_accelerator_reexport)
  json.JSONDecoder            -> json.decoder.JSONDecoder     (explicit_all_reexport)

--- 4. Polymorphic @overload Sets (7 variants registered) ---
  <ambient>.max               -> 3 @overload signatures
  <ambient>.open              -> 2 @overload signatures
  os.getenv                   -> 2 @overload signatures
======================================================================
```

---

## 5. Command: `query`

The `query` command runs built-in diagnostic queries to inspect specific namespace mechanics, or accepts custom arbitrary SQL queries.

### Synopsis

```bash
uv run utss query [--db <path>] [QUERY_OPTION]
```

### Pre-Built Diagnostic Query Flags

#### Flag: `--ambient` (Query A)
Verifies Stratum 0 ambient namespace available without import statements (pure builtins, `site`-injected helpers, hard/soft keywords, and implicit module dunders).

```bash
uv run utss query --db catalog.db --ambient
```

#### Flag: `--module <name>` (Query B)
Inspects a specific module's symbol breakdown (classes, functions, variables), categorizing visibility into `public_implicit`, `exported_all`, `hidden_internal`, and `system_dunder`.

```bash
uv run utss query --db catalog.db --module sys
```

#### Flag: `--c-accelerators` (Query C)
Traces public standard library facades (such as `io`, `json`, `os`) to their underlying compiled C implementations (`_io`, `_json`, `posix`).

```bash
uv run utss query --db catalog.db --c-accelerators
```

#### Flag: `--overloads` (Query D)
Displays all registered polymorphic `@overload` families, listing their positional declaration order, signature strings, and typed return expressions.

```bash
uv run utss query --db catalog.db --overloads
```

#### Flag: `--pyi-enriched` (Query E)
Lists C-builtin functions that were successfully enriched with typed parameters and return values via the Typeshed overlay pass.

```bash
uv run utss query --db catalog.db --pyi-enriched
```

#### Flag: `--workspace-symbols` (Query F)
Lists Stratum 3 workspace symbols, including synthesized `self.<attr>` instance attributes with propagated parameter types, private mangled fields, and exact AST coordinates.

```bash
uv run utss query --db catalog.db --workspace-symbols
```

#### Flag: `--workspace-generators` (Query G)
Lists Stratum 3 generator functions (`yield` / `yield from`) and coroutines (`async def`), verified via scope-bounded AST analysis.

```bash
uv run utss query --db catalog.db --workspace-generators
```

#### Flag: `--workspace-imports` (Query H)
Traces the local workspace import graph and relative import resolution (`from .models import Order`), tracking re-exports and `__all__` exposure.

```bash
uv run utss query --db catalog.db --workspace-imports
```

#### Flag: `--sql <query_string>`
Executes an arbitrary read-only SQL query against the database and prints tabulated output.

```bash
uv run utss query --db catalog.db --sql "
SELECT s.name, c.return_type_expr, c.raw_signature 
FROM callables c 
JOIN symbols s ON c.symbol_id = s.symbol_id 
WHERE s.name = 'len';
"
```

---

## 6. Automation & CI Recipes

### Complete Verification Shell Script (`verify.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail

DB_FILE="build/utss_catalog.db"
mkdir -p build

echo "==> 1. Harvesting stdlib and local codebase..."
uv run utss harvest \
    --db "${DB_FILE}" \
    --sample-stdlib \
    --workspace . \
    --demo-stubs \
    --reset

echo "==> 2. Verifying @overload extraction..."
uv run utss query --db "${DB_FILE}" --overloads

echo "==> 3. Verifying C-builtin type enrichment..."
uv run utss query --db "${DB_FILE}" --pyi-enriched

echo "==> 4. Catalog successfully verified."
```
