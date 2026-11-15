# UTSS Architecture & Technical Deep-Dive

**Document:** Architecture Design & Engineering Decisions  
**System:** Universal Type & Symbol System (UTSS)  
**Authors:** Antigravity Engineering Team  
**Status:** Active Reference (Foundational Reference Implementation)

> [!NOTE]
> This document details the foundational CPython reference implementation of the UTSS Dual-Layer architecture (located in [`harvesters/utss-python/`](../harvesters/utss-python/)). For the polyglot monorepo across all 6 languages (Python, C#, Rust, TypeScript, C++, Go), see the root [README.md](../README.md), the central schemas in [schemas/](../schemas/README.md), and the [workbench/](../workbench/README.md).  

---

## 1. Motivation: The Transpiler Symbol Ground-Truth Problem

Transpilation from a dynamic, optionally-typed language like Python to a statically-typed target like C# (`psc`), Go, or Rust presents fundamental challenges that cannot be resolved through static AST parsing or naive runtime reflection alone.

### Why Static AST Parsing Alone Fails
Static AST visitors cannot inspect compiled C extensions (`sys`, `math`, `time`, `_io`, `posix`). When user code executes `import math; math.sqrt(16)`, the AST reveals only the names `"math"` and `"sqrt"`. The AST contains **zero information** about whether `sqrt` is a function, what its parameter constraints are, whether it raises exceptions, or what type it returns.

Furthermore, static AST tools stumble over Python's dynamic runtime exports. For instance, in Python's standard library:
- User code imports `from io import BufferedReader`.
- But `BufferedReader` is not defined in `io.py`; it is imported from a compiled C accelerator `_io`.
- In AST, `BufferedReader` looks like a foreign import alias. Without runtime ground truth, a transpiler cannot know if `io.BufferedReader` is a public API or an internal implementation artifact.

### Why Pure Runtime Reflection (`dir()`) Alone Fails
Conversely, relying exclusively on runtime reflection (`dir(module)`) introduces severe namespace pollution:
1. **Namespace Leaks**: When `shutil.py` does `import os`, `dir(shutil)` contains `'os'`. A naive runtime crawler indexes `shutil.os.path.join`, polluting the symbol space.
2. **Missing Types on C-Builtins**: Functions implemented in C (e.g. `len`, `math.sin`, `builtins.open`) have `__annotations__ == {}` at runtime. Calling `inspect.signature(len)` yields `(obj, /)`, with no return type information (`int`).
3. **Erased Generics on Global Variables**: Modules often declare global state variables (`sys.argv`, `os.environ`). At runtime, `type(sys.argv)` is simply `list`, erasing the element type `str`.
4. **Side-Effects on Workspace Code**: Running `importlib.import_module()` on user code can trigger side-effects (opening network connections, starting background threads, running top-level scripts).

### The UTSS Solution: An Empirical 4-Pass Hybrid Pipeline
UTSS combines **hardened runtime reflection**, **safe static AST parsing**, and **conditional static `.pyi` stub overlays** into an integrated relational database.

```
                           ┌──────────────────────────────┐
                           │      Python Interpreter      │
                           │   (CPython 3.13 Runtime)     │
                           └──────────────┬───────────────┘
                                          │
                 ┌────────────────────────┼────────────────────────┐
                 │                        │                        │
                 ▼                        ▼                        ▼
        [Pass 0: Ambient]        [Pass 1: Stdlib]        [Pass 2: Ecosystem]
        - Keywords (keyword)     - Built-in C modules    - importlib.metadata
        - Pure builtins (-S)     - Frozen modules        - packages_distributions
        - site helpers           - Dynamic C extensions  - find_spec roots
        - Module dunders         - C-accelerators (_io)
                 │                        │                        │
                 └────────────────────────┼────────────────────────┘
                                          │
                                          ▼
                               ┌──────────────────────┐
                               │   Dual-Layer Schema  │
                               │     (catalog.db)     │
                               └──────────▲───────────┘
                                          │
                 ┌────────────────────────┴────────────────────────┐
                 │                                                 │
                 ▼                                                 ▼
        [Pass 3: Workspace AST]                          [Pass 4: Typeshed Overlay]
        - ast.parse (no execution)                       - Static .pyi parsing
        - Packages, modules, classes                     - Guard pruning (sys.version_info)
        - Defs, methods, annotations                     - C-builtin type enrichment
        - Global state members                           - Polymorphic @overload sets
```

---

## 2. Taxonomy of Concentric Strata

UTSS structures all language constructs into 4 concentric strata to guarantee exhaustive coverage:

| Stratum | Name | Boundary | Discovery Strategy |
| :---: | :--- | :--- | :--- |
| **0** | **Ambient Scope** | Available globally without any `import` statement. | Hard/soft keywords via `keyword`; pure builtins via `python -S` sub-process differential probe; `site`-injected builtins; implicit module dunders (`__name__`, `__file__`, `__doc__`). |
| **1** | **Python Installation (Stdlib)** | Shipped with the active Python distribution. | Standard library modules via `sys.stdlib_module_names` and `sys.builtin_module_names`; C-accelerators mapped to public facades. |
| **2** | **Third-Party Ecosystem** | Installed packages in active environment (`site-packages`). | Package distributions via `importlib.metadata.distributions()`; distribution-to-top-level-package mapping via `packages_distributions()`. |
| **3** | **Workspace Source** | Local user/application codebase. | Pure static AST traversal (`ast.parse()`) with zero runtime code execution. |

---

## 3. The Dual-Layer Schema Rationale

### Universal Core vs. Language-Specific Facets

A major design flaw in traditional compiler symbol tables is coupling the data model to a specific source language. For example, adding an `is_c_extension` or `mro_list` column to a universal `containers` or `symbols` table makes the schema useless for C# or TypeScript codebases.

UTSS adopts a **strict dual-layer relational architecture**:

```
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │                         LAYER 1: UNIVERSAL CORE                             │
 │                                                                             │
 │   [environments] ──< [distributions] ──< [containers] ──< [symbols]        │
 │                                                              │              │
 │                                            ┌─────────────────┴──────────┐   │
 │                                            ▼                            ▼   │
 │                                       [callables]               [state_members]
 │                                            │                                │
 │                                     ┌──────┴──────────────┐                 │
 │                                     ▼                     ▼                 │
 │                           [callable_overloads]     [parameters]             │
 └─────────────────────────────────────┬─────────────────────┬─────────────────┘
                                       │ 1:1                 │ 1:1
 ┌─────────────────────────────────────▼─────────────────────▼─────────────────┐
 │                      LAYER 2: PYTHON-FIDELITY FACETS                        │
 │                                                                             │
 │           [py_container_facets]                      [py_symbol_facets]     │
 │           - origin_kind                              - dunder_category      │
 │           - has_dunder_all                           - descriptor_kind      │
 │           - dunder_all_json                          - is_coroutine_fn      │
 │           - has_lazy_getattr                         - mro_json             │
 │                                                      - base_classes_json    │
 └─────────────────────────────────────────────────────────────────────────────┘
```

1. **Universal Core (Tables 1–9)**:
   - Models concepts present in any structured language: environments, distributions/assemblies, packages/modules, classes, methods, functions, variables, parameters, and aliases.
   - Any compiler backend (e.g. Roslyn, LLVM, `psc`) can consume these tables without knowledge of Python internals.
2. **Python Facets (Tables 10–11)**:
   - Contains Python-specific mechanics: descriptor protocols (`@property`, `@classmethod`), dunder categories (`__getitem__` $\to$ container indexing), C-extension loading types, and class MRO tuples.
   - Joined via `1:1` foreign keys with `ON DELETE CASCADE`.

---

## 4. Pass 4: Static Typeshed Overlay & Static Guard Evaluation

The static `.pyi` overlay pass bridges the gap between CPython's compiled C implementations and static type annotations.

### 4.1 Static AST Guard Pruning (`eval_static_guard`)
Typeshed stubs frequently contain conditional statements guarding platform- or version-specific definitions:

```python
if sys.version_info >= (3, 10):
    def aiter(iterable: AsyncIterable[T], /) -> AsyncIterator[T]: ...

if sys.platform == "win32":
    def startfile(filepath: StrOrBytesPath, operation: str = ...) -> None: ...
else:
    def fork() -> int: ...
```

If parsed naively, a cataloger would either register both conflicting branches or fail on duplicate symbols.

UTSS implements a dedicated AST evaluator: `eval_static_guard(test_node, env_context)`:
1. Evaluates binary comparisons (`>=`, `>`, `<`, `<=`, `==`, `!=`, `in`, `not in`) over `sys.version_info` tuples (e.g. `(3, 13)`).
2. Evaluates equality and containment over `sys.platform` strings (e.g. `'linux'`, `'win32'`, `'darwin'`).
3. Evaluates boolean combinations (`and`, `or`, `not`).
4. **Flattens active AST bodies**: If a test evaluates to `True`, the `body` statements are emitted; if `False`, `orelse` statements are emitted. If indeterminable, it defaults safely to the primary branch.

### 4.2 Polymorphic `@overload` Modeling
In Python type stubs, polymorphic functions are expressed using the `@overload` decorator:

```python
@overload
def open(file: StrOrBytesPath, mode: OpenTextMode = "r", ...) -> TextIOWrapper: ...
@overload
def open(file: StrOrBytesPath, mode: OpenBinaryMode, ...) -> FileIO: ...
```

UTSS models this relationally:
1. The base callable is stored in `callables` with `has_overloads = 1` and `overload_count = 2`.
2. Each variant is inserted into `callable_overloads` with its 0-based `overload_order` (`0`, `1`), its variant return type, and its signature.
3. Overload-specific parameters are inserted into `parameters` linked via `overload_id`.

---

## 5. Hardened Introspection: Surviving Python 3.13 Quirks

During the development of UTSS on Python 3.13.12, empirical testing uncovered unexpected failures in the standard library's `inspect` module:

### The Bug in Python 3.13 `inspect.signature`
When inspecting certain C-extension functions (notably in `_curses` and `select.epoll`), `inspect.signature()` attempts to evaluate symbolic AST constants for default arguments. In Python 3.13, this can trigger internal `AttributeError` or `NameError` inside `inspect.py`:
- `AttributeError: module '_curses' has no attribute 'ACS_VLINE'`
- `AttributeError: 'builtin_function_or_method' object has no attribute 'EPOLLIN'`

### Hardened Signature Fallback Strategy
UTSS implements a multi-stage fallback in `src/utss/introspect.py`:
1. **Stage 1 (Primary)**: Attempt `inspect.signature(obj)`.
2. **Stage 2 (Catch & Recover)**: Catch `(ValueError, TypeError, AttributeError, NameError, Exception)`.
3. **Stage 3 (Text Signature)**: Check `getattr(obj, "__text_signature__", None)`. If present (e.g. `"(iterable, /)"`), parse parameter names using regular expressions.
4. **Stage 4 (Docstring Parse)**: Check `getattr(obj, "__doc__", "")`. Many C builtins format their first line as `name(arg1, arg2=default) -> return_type`.
5. **Stage 5 (Graceful Degradation)**: Return an empty parameter list rather than aborting the catalog harvest.

---

## 6. Stratum 3: Deep Pure-AST Workspace Harvesting Engine

Scanning arbitrary local application code requires a fundamentally different architecture than runtime reflection or `.pyi` stubs. Importing user modules is dangerous because top-level statements often invoke argument parsers, initiate database connections, require external environment variables, or launch subprocesses.

UTSS implements a pure static AST harvester (`WorkspaceAstCataloger`) that parses files using `ast.parse()` without code execution, solving five core challenges:

### 6.1 Constructor Instance Attribute Synthesis & Parameter Type Propagation
In idiomatic Python, class attributes are rarely declared in the class body; they are assigned dynamically inside `__init__`, `__new__`, or `__post_init__`:

```python
class Order:
    def __init__(self, order_id: str, subtotal: float = 0.0) -> None:
        self.order_id = order_id
        self.subtotal = subtotal
        self.__secret_token = "tok_live_99"
```

The AST harvester:
1. Traverses the AST of constructor methods.
2. Identifies all `self.<attr> = ...` and `self.<attr>: T = ...` assignments.
3. Automatically **propagates parameter type annotations**: since `subtotal` is typed as `float` in `__init__`'s signature, `self.subtotal` is recorded in `state_members` with `declared_type_expr = 'float'`.
4. Detects double-underscore prefixes (e.g. `self.__secret_token`), assigning `visibility = 'private_mangled'`.
5. Categorizes the symbol with `provenance = 'ast_init_attribute'`.

### 6.2 Scope-Bounded Generator Detection
At runtime, the interpreter flags generators via `CO_GENERATOR` bytecode flags. In pure AST mode, looking for `ast.Yield` or `ast.YieldFrom` across an entire function tree causes false positives if a generator is defined inside a nested closure or lambda:

```python
def make_counter():
    # Outer function is NOT a generator!
    def generator():
        yield 1  # Inner closure IS a generator
    return generator
```

UTSS implements a **scope-bounded AST walker**: it inspects a function's statement stack, explicitly halting traversal at nested `def`, `async def`, `class`, and `lambda` boundaries. If `Yield` or `YieldFrom` is found within the function's own lexical scope, `is_generator` is set to `1`.

### 6.3 Package Layout & Relative Import Resolution
Workspaces may use a flat layout, a `src/` layout (`src/pkg/__init__.py`), or PEP 420 namespace packages. When parsing relative imports:

```python
from ..models import Order
```

The AST harvester:
1. Computes the logical dotted module path relative to the package root (stripping `src/` when present).
2. Calculates the target module using `node.level` and the current package hierarchy.
3. Records the dependency edge in `symbol_aliases` with `alias_type = 'workspace_relative_import'`.

### 6.4 Static `__all__` Evaluation & Conditional Blocks
1. **Static `__all__`**: Evaluates list, tuple, and set literals assigned to `__all__` or augmented via `__all__ += [...]`, classifying symbols as `exported_all` vs. `public_implicit`.
2. **Conditional Block Traversal**: Traverses inside `if TYPE_CHECKING:`, `try / except:`, and `if __name__ == "__main__":` blocks, tagging symbols with `'ast_type_checking_only'` or `'ast_main_guard'` so conditional type aliases and entrypoints are preserved.

### 6.5 Exact AST Coordinates
Every container and symbol records `start_line`, `start_col`, `end_line`, and `end_col` directly from the AST node, providing compilers and LSPs with precise source ranges.

---

## 7. Transpiler Backends Integration Roadmap

UTSS serves as the foundational database for upcoming compiler and transpiler pipelines:

```
                            UTSS (catalog.db)
                                   │
               ┌───────────────────┴───────────────────┐
               ▼                                       ▼
    Phase 4: Type Normalizer                Phase 5: psc Transpiler
    - Python int -> System.Numerics.BigInteger   - Synthesize C# namespaces
    - Python list[T] -> System.Collections.Generic.List<T> - Map builtins to BCL methods
    - Duck protocols -> C# Interfaces       - Emit P/Invoke native stubs
```

1. **Phase 4 (Cross-Language Type Normalization)**:
   - Normalize Python's nominal and structural types into universal primitive, product, and sum types.
   - Map duck-typed dunder protocols (`__getitem__`, `__iter__`, `__enter__`) to standard compiler interfaces (`IIndexable<K, V>`, `IEnumerable<T>`, `IDisposable`).
2. **Phase 5 (`psc` Transpiler Integration)**:
   - Query `catalog.db` during compilation to resolve symbols, check overloads, and generate idiomatic target code.
