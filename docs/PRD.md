# Product Requirements Document (PRD): Universal Type & Symbol System (UTSS)

**Document Version:** 1.0.0  
**Status:** Complete & Delivered (Foundational Reference Implementation)  
**Author:** Antigravity / Engineering Team  
**Date:** November 11, 2026  
**Target:** Implementation of Proof of Concept & Foundation for Multi-Language Expansion

> [!NOTE]
> This PRD defines the foundational design principles of the UTSS Dual-Layer architecture and the 4 strata taxonomy as originally demonstrated in Python. The system has since expanded into a full polyglot monorepo covering 6 languages (Python, C#, Rust, TypeScript, C++, Go) with a unified Workbench and Central Relational Schemas. See the root [README.md](../README.md) and [docs/NEXT_PHASE_DOMAIN_EXPANSION_PLAN.md](NEXT_PHASE_DOMAIN_EXPANSION_PLAN.md).

---

## 1. Executive Summary & Problem Statement

### 1.1 Context
In language transpilation (specifically Python-to-C# via `psc`, and future multi-language transpilation pipelines), static analyzers and code generators frequently suffer from "namespace hallucinations" and impedance mismatches. Compilers cannot reliably distinguish between:
1. Symbols available in Python without any imports (ambient keywords, pure builtins, `site`-injected helpers, and implicit module dunders).
2. Symbols actually declared in a module vs. foreign dependencies pulled in via namespace pollution (`import os` inside `shutil.py`).
3. Public facades vs. underlying compiled C-accelerator implementations (`io.BufferedReader` $\to$ `_io.BufferedReader`, `json.loads` $\to$ `_json`, `os.listdir` $\to$ `posix`/`nt`).
4. Exact runtime signatures and descriptors vs. duck-typed conventions.

### 1.2 Mission
Build **UTSS** (**Universal Type & Symbol System**)—an empirical, zero-hallucination inventory and cataloging engine that indexes 100% of a Python environment's namespace into a high-performance **Dual-Layer SQLite Database**:
- **Layer 1: Language-Agnostic Core Schema** (Containers, Symbols, Callables, Parameters, State Members, Symbol Aliases) modeled after universal compiler IR concepts.
- **Layer 2: Python-Fidelity Facets** (Module origin kinds, descriptor protocols, dunder categories, MRO, PEP 562 lazy `__getattr__`) attached via 1:1 foreign keys without polluting the universal tables.

---

## 2. Taxonomy of Concentric Strata

To ensure zero blind spots across any Python environment, UTSS categorizes all constructs into four concentric strata:

| Stratum | Scope / Origin | Requires `import`? | Sub-Categories Included | Discovery Mechanism |
| :--- | :--- | :---: | :--- | :--- |
| **Stratum 0: Ambient Scope** | Lexical & Interpreter Scope | **No** | **0A.** Hard/Soft Keywords (`def`, `match`, `type`)<br>**0B.** Pure `builtins` (`len`, `int`, `open`)<br>**0C.** `site`-injected builtins (`help`, `exit`, `quit`)<br>**0D.** Implicit module dunders (`__name__`, `__file__`, `__doc__`)<br>**0E.** Object protocols (`__init__`, `__iter__`, `__call__`) | `keyword`, `python -S` differential probe, and module namespace inspection. |
| **Stratum 1: Python Installation (Stdlib)** | Versioned Runtime (`3.13.x`) | **Yes** | **1A.** Built-in C modules (`sys`, `math`, `time`)<br>**1B.** Frozen modules (`_frozen_importlib`, `os`)<br>**1C.** Pure-Python stdlib (`json`, `pathlib`, `collections`)<br>**1D.** Dynamic C extensions (`.so`/`.pyd` in `lib-dynload`)<br>**1E.** Hidden accelerators (`_io`, `_json`, `_sre`, `posix`) | `sys.builtin_module_names`, `sys.stdlib_module_names`, `pkgutil`, `sysconfig.get_paths()`. |
| **Stratum 2: Third-Party Ecosystem** | Active Virtualenv (`site-packages`) | **Yes** | **2A.** Standard packages (`numpy`, `requests`)<br>**2B.** Mismatched distributions (`scikit-learn` $\to$ `sklearn`)<br>**2C.** PEP 420 Namespace packages (`google.*`)<br>**2D.** Compiled extensions & stubs | `importlib.metadata.distributions()`, `packages_distributions()`, and `find_spec()`. |
| **Stratum 3: Workspace Source** | Local Project Code | **Yes** (or entry script) | **3A.** Entrypoint scripts (`__main__`, `main.py`)<br>**3B.** Local modules and packages with relative imports | Safe local filesystem walk and AST parsing (`ast.parse()`) **without code execution**. |

---

## 3. Engineering Analysis & Python 3.13 Runtime Discoveries

Empirical evaluation of the prototype against the Python 3.13 runtime identified the following key architectural requirements:

### 3.1 Hardened Signature Extraction
- **The Issue:** Python 3.13's `inspect.signature()` executes symbolic AST evaluation of default parameter values for C-extension functions. On modules such as `_curses` and `select`, evaluating symbolic constants (e.g. `_curses.ACS_VLINE` or `select.epoll.poll(timeout=-1, maxevents=-1)`) raises `AttributeError` or `NameError` inside `inspect.py`.
- **The Solution:** Broaden exception handling in `extract_callable_signature` to catch `(ValueError, TypeError, AttributeError, NameError, Exception)`, falling back gracefully to `__text_signature__`, first-line docstring signatures, and empty parameter fallback.

### 3.2 Provenance vs. Pollution Differentiation
When module `A` executes `import B`, `A.__dict__['B']` contains a module reference. A naive crawler duplicates `B` as a child of `A`. UTSS strictly bifurcates:
- **`defined_here`**: Objects whose `__module__ == module.__name__`.
- **`c_accelerator_reexport`**: Public facade re-exporting symbols from private C implementations (`io.BufferedReader` from `_io`).
- **`explicit_all_reexport`**: Foreign symbols explicitly published in `__all__`.
- **`imported_module_ref` / `imported_symbol_ref`**: Captured in `symbol_aliases` for compiler dependency resolution, never duplicated in primary symbol tables.

### 3.3 Safe AST Harvester for Stratum 3
Local workspace files must **never be executed via `importlib`** during harvesting to avoid side-effects (e.g. executing scripts, opening connections). Stratum 3 must be powered by a static `ast.NodeVisitor` that records modules, classes, functions, parameters, type annotations, and global assignments directly into the universal schema.

---

## 4. Phase 1 Architecture & Modular Decomposition

The UTSS implementation replaces the monolithic prototype (`Ideation/1.py`) with a clean, extensible package in `src/utss/`:

```
UTSS/
├── pyproject.toml              # Build config, deps, CLI scripts (`utss`)
├── main.py                     # Entrypoint redirector
├── docs/
│   └── PRD.md                  # This document
├── src/
│   └── utss/
│       ├── __init__.py         # Package exports & version
│       ├── schema.py           # Universal SQLite DDL, migrations, index definitions
│       ├── models.py           # Enums & Typed representations
│       ├── introspect.py       # Hardened signatures, visibility rules, safe repr
│       ├── cataloger.py        # Central engine: Stratum 0, 1, 2 orchestration
│       ├── workspace.py        # Stratum 3 static AST harvester
│       ├── queries.py          # Pre-built diagnostics & SQL verification queries
│       └── cli.py              # CLI commands: `harvest`, `report`, `query`
└── tests/
    ├── conftest.py             # SQLite fixtures
    ├── test_schema.py          # Table schemas, foreign keys, cascades
    ├── test_introspect.py      # Signature extraction & edge-case resiliency
    ├── test_stratum_0.py       # Ambient scope & differential builtins
    ├── test_stratum_1.py       # Stdlib & C-accelerator re-export mapping
    ├── test_stratum_2.py       # Third-party metadata harvesting
    ├── test_stratum_3.py       # Safe workspace AST harvesting
    └── test_cli.py             # End-to-end CLI integration
```

---

## 5. Implementation Roadmap (Phases 1 through 4+)

### Phase 1: Foundation & Spectrum Harvester (`1.md`) — [COMPLETED]
- [x] Create PRD in `docs/PRD.md`.
- [x] Implement modular `utss` package with Dual-Layer Schema.
- [x] Hardened signature introspection resilient to Python 3.13 C-extension quirks.
- [x] Full coverage of Stratum 0 (Ambient), Stratum 1 (Stdlib), Stratum 2 (Third-Party), and Stratum 3 (Workspace AST).
- [x] CLI with reporting and diagnostic SQL queries.
- [x] Pytest verification suite covering all Strata (18/18 tests passing).

### Phase 2: Static Stub & Typeshed Overlay (`2.md`) — [COMPLETED]
- [x] Schema extensions:
  - Add `sys_platform` to `environments`.
  - Add `stub_path` to `containers`.
  - Add `has_overloads`, `overload_count`, `type_params_json` to `callables`.
  - Add `callable_overloads` universal table for 1..N polymorphic signatures.
  - Add `overload_id` and `type_source` ('runtime_annotation' vs 'pyi_stub') to `parameters`.
- [x] Static `.pyi` AST overlay engine (`src/utss/overlay.py`):
  - Static evaluation of `sys.version_info` and `sys.platform` AST guard branches (`if sys.version_info >= (3, 12):`).
  - Enrichment of untyped C-builtins (`len`, `print`, `max`, `iter`) with static parameter/return types.
  - Polymorphic `@overload` extraction (e.g. `builtins.open`, `max`, `os.getenv`).
  - Restoration of erased generic types on module/class state variables (`sys.argv` $\to$ `list[str]`, `os.environ` $\to$ `MutableMapping[str, str]`).
  - Support auto-discovery of installed typeshed, custom `--typeshed-dir`, and zero-dependency `--demo-stubs`.
- [x] CLI extensions:
  - `utss harvest --demo-stubs` or `utss harvest --typeshed-dir <path>`
  - `utss overlay --demo-stubs` or `utss overlay --typeshed-dir <path>`
  - `utss query --overloads` (Query D) and `utss query --pyi-enriched` (Query E)
- [x] Comprehensive pytest suite for overlay & overloads (27/27 tests passing).

### Phase 3: Deep Pure-AST Workspace Harvester (`3.md`) — [COMPLETED]
- [x] Schema extensions:
  - Add AST source coordinates (`start_line`, `start_col`, `end_line`, `end_col`) to `containers` and `symbols`.
  - Add callable modifiers (`is_static`, `is_class_bound`, `signature_source`) to `callables`.
  - Add `'ast_annotation'` to allowed `type_source` in `parameters`.
  - Add specialized provenance values: `'ast_defined'`, `'ast_init_attribute'`, `'ast_type_checking_only'`, `'ast_main_guard'`.
  - Add specialized alias kinds: `'workspace_import'`, `'workspace_relative_import'`, `'wildcard_import'`.
- [x] Embedded multi-file demo workspace fixtures (`EMBEDDED_DEMO_WORKSPACE_FILES`):
  - `commerce_engine` package (`__init__.py`, `models.py`, `service.py`, `_internal_metrics.py`, `cli_runner.py`).
  - `--demo-workspace` CLI flag for zero-dependency local workspace verification.
- [x] Deep AST Harvester engine (`src/utss/workspace.py`):
  - Auto-discovery of workspace files handling `src/` layout, flat layout, and ignored directories.
  - Instance attribute synthesis from `__init__`, `__new__`, `__post_init__` (`self.<attr> = ...`) with parameter type annotation propagation.
  - Private name mangling detection (`self.__secret_token` $\to$ `private_mangled`).
  - Scope-bounded generator detection (`yield` / `yield from`) that explicitly halts at nested closure boundaries.
  - Relative import resolution (`from .models import Order`, `from ..core import Config`) against package hierarchy.
  - Static `__all__` evaluation (`__all__ = [...]`, `__all__ += [...]`).
  - Traversal of conditional blocks (`if TYPE_CHECKING:`, `try / except:`, `if __name__ == '__main__':`).
  - PEP 695 `type CustomerId = int` alias extraction.
- [x] Diagnostic query suite in `src/utss/queries.py` and CLI options:
  - Query F: `--workspace-symbols` (synthesized `self.<attr>` fields and types).
  - Query G: `--workspace-generators` (static generators and coroutines).
  - Query H: `--workspace-imports` (workspace import and re-export dependency graph).
- [x] Pytest verification suite for Stratum 3 deep AST features (36/36 tests passing).

### Phase 4: Semantic Typing & Universal Symbol Representation (`4.md`) — [UPCOMING]
- Normalization of duck-typed protocols into universal nominal and structural interfaces.
- Mapping Python nominal types (`int`, `str`, `dict`, `list`) to Universal Compiler Types (`i64`/`BigInt`, `string`, `Map<K, V>`, `List<T>`).

### Phase 5: Transpiler Backend Integration (`5.md` / `psc`)
- Emit C# symbol tables, P/Invoke or native runtime bindings for Python C-extensions.
- Transpile Python ambient and stdlib calls directly to equivalent .NET BCL or runtime helper libraries.

---

## 6. Success Metrics & Verification Criteria (Phase 1 PoC)

1. **Zero Runtime Exceptions**: Full harvest of all 289+ Python 3.13 stdlib modules without unhandled exceptions.
2. **Accurate Stratum 0 Separation**: Verifiably isolates 6 `site`-injected builtins (`help`, `quit`, `exit`, `copyright`, `credits`, `license`) from pure builtins via `python -S`.
3. **Traceable Re-exports**: Verifiable resolution from `io` to `_io`, `json` to `_json`, and `os` to `posix`/`nt`.
4. **Static Safety**: Stratum 3 extracts local code symbols via pure AST parsing without running module code.
5. **Test Coverage**: 100% passing test suite across all schema tables and strata harvesters.
