#!/usr/bin/env python3
"""
python_spectrum_harvester.py

Standalone, zero-dependency clean-room experiment to catalog the complete spectrum
of a Python installation into a Language-Agnostic + Python-Facet SQLite database:
  - Pass 1 (Stratum 0): Ambient Scope (No-import keywords, builtins, site-builtins, module dunders)
  - Pass 2 (Stratum 1): Versioned Python Stdlib (Built-in C, Frozen, Pure-Python, C-Extensions,
                        both public and hidden `_` modules/functions/variables)
  - Pass 3 (Stratum 2): Environment Third-Party Distributions (via importlib.metadata)
  - Pass 4 (Static .pyi Overlay): AST-based Typeshed `.pyi` overlay that enriches opaque C-builtins,
                        attaches static parameter/return types, populates `@overload` sets,
                        and resolves `sys.version_info` / `sys.platform` guards statically.
"""

from __future__ import annotations

import argparse
import ast
import builtins
import hashlib
import importlib
import importlib.machinery
import importlib.metadata
import importlib.util
import inspect
import json
import keyword
import platform
import pkgutil
import sqlite3
import subprocess
import sys
import sysconfig
import types
from pathlib import Path
from typing import Any, Sequence


SIDE_EFFECT_STDLIB_MODULES: frozenset[str] = frozenset({
    "antigravity",
    "this",
    "idlelib",
    "tkinter",
    "turtle",
    "turtledemo",
    "test",
    "lib2to3",
    "ensurepip",
    "venv",
    "pydoc_data",
    "__hello__",
    "__phello__",
    "_xxsubinterpreters",
    "_xxinterpchannels",
    "_xxtestfuzz",
})

IMPLICIT_MODULE_DUNDERS: tuple[tuple[str, str, str], ...] = (
    ("__name__", "str", "Module's runtime name ('__main__' when executed directly, or dotted module name)."),
    ("__doc__", "str | None", "Module's top-level docstring literal, or None if absent."),
    ("__package__", "str | None", "Parent package name used to resolve relative imports."),
    ("__loader__", "Loader | None", "The importlib Loader object that loaded this module."),
    ("__spec__", "ModuleSpec | None", "The importlib ModuleSpec describing module import state and origin."),
    ("__file__", "str | None", "Filesystem path from which the module was loaded (absent on some built-in C modules)."),
    ("__cached__", "str | None", "Filesystem path to the compiled bytecode (.pyc) file."),
    ("__builtins__", "dict[str, Any] | module", "Reference to the ambient builtins module or its namespace dictionary."),
    ("__annotations__", "dict[str, Any]", "Module-level variable type annotations dictionary."),
)

# Embedded mini-typeshed stubs so `--demo-stubs` works in a 100% bare Python environment
EMBEDDED_DEMO_STUBS: dict[str, str] = {
    "builtins": """
from typing import Any, Callable, Iterable, Iterator, Sequence, Sized, TypeVar, overload
import io

_T = TypeVar("_T")
_T_co = TypeVar("_T_co", covariant=True)

def len(obj: Sized, /) -> int: ...
def print(
    *values: object,
    sep: str | None = " ",
    end: str | None = "\\n",
    file: Any | None = None,
    flush: bool = False,
) -> None: ...

@overload
def open(
    file: str | bytes | int,
    mode: str = "r",
    buffering: int = -1,
    encoding: str | None = None,
    errors: str | None = None,
    newline: str | None = None,
    closefd: bool = True,
    opener: Callable[[str, int], int] | None = None,
) -> io.TextIOWrapper: ...
@overload
def open(
    file: str | bytes | int,
    mode: bytes,
    buffering: int = -1,
    encoding: None = None,
    errors: None = None,
    newline: None = None,
    closefd: bool = True,
    opener: Callable[[str, int], int] | None = None,
) -> io.BufferedRandom | io.BufferedReader | io.BufferedWriter: ...

@overload
def max(arg1: _T, arg2: _T, *_args: _T, key: Callable[[_T], Any] | None = None) -> _T: ...
@overload
def max(iterable: Iterable[_T], *, key: Callable[[_T], Any] | None = None) -> _T: ...
@overload
def max(iterable: Iterable[_T], *, key: Callable[[_T], Any] | None = None, default: _T) -> _T: ...

class str(Sequence[str]):
    def split(self, sep: str | None = None, maxsplit: int = -1) -> list[str]: ...
    def join(self, iterable: Iterable[str], /) -> str: ...
    def replace(self, old: str, new: str, count: int = -1, /) -> str: ...
""",
    "sys": """
import sys
from typing import Any, NoReturn, TextIO

argv: list[str]
executable: str
platform: str
version: str
version_info: tuple[int, int, int, str, int]
modules: dict[str, Any]
path: list[str]
stdin: TextIO
stdout: TextIO
stderr: TextIO

def exit(status: str | int | None = None, /) -> NoReturn: ...
def getrecursionlimit() -> int: ...
def setrecursionlimit(limit: int, /) -> None: ...
def _getframe(depth: int = 0, /) -> Any: ...

if sys.version_info >= (3, 12):
    def getunicodeinternedsize(*, _only_immortal: bool = False) -> int: ...
""",
    "os": """
from typing import Any, Callable, Iterator, Mapping, MutableMapping, overload

environ: MutableMapping[str, str]
sep: str
linesep: str
name: str

def getcwd() -> str: ...
def listdir(path: str | bytes | None = None) -> list[str]: ...
def makedirs(name: str | bytes, mode: int = 0o777, exist_ok: bool = False) -> None: ...
def walk(
    top: str,
    topdown: bool = True,
    onerror: Callable[[OSError], object] | None = None,
    followlinks: bool = False,
) -> Iterator[tuple[str, list[str], list[str]]]: ...

@overload
def getenv(key: str) -> str | None: ...
@overload
def getenv(key: str, default: str) -> str: ...
""",
    "json": """
from typing import Any, Callable, IO

def dumps(
    obj: Any,
    *,
    skipkeys: bool = False,
    ensure_ascii: bool = True,
    check_circular: bool = True,
    allow_nan: bool = True,
    indent: int | str | None = None,
    separators: tuple[str, str] | None = None,
    default: Callable[[Any], Any] | None = None,
    sort_keys: bool = False,
) -> str: ...

def loads(
    s: str | bytes | bytearray,
    *,
    object_hook: Callable[[dict[str, Any]], Any] | None = None,
    parse_float: Callable[[str], Any] | None = None,
    parse_int: Callable[[str], Any] | None = None,
    parse_constant: Callable[[str], Any] | None = None,
    strict: bool = True,
) -> Any: ...
""",
}


# ============================================================================
# 1. LANGUAGE-AGNOSTIC CORE + PYTHON FACET SQLITE SCHEMA
# ============================================================================

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

-- 1. Environments: Tracks exact language runtime versions & platforms
CREATE TABLE IF NOT EXISTS environments (
    env_id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,                 -- 'python', 'rust', 'csharp', 'typescript'
    runtime_name TEXT NOT NULL,             -- 'CPython', 'PyPy', 'rustc', '.NET'
    language_version TEXT NOT NULL,         -- e.g. '3.12.7'
    version_major INTEGER NOT NULL,
    version_minor INTEGER NOT NULL,
    version_micro INTEGER NOT NULL,
    platform_triplet TEXT NOT NULL,         -- e.g. 'Linux-x86_64'
    sys_platform TEXT NOT NULL,             -- e.g. 'linux', 'darwin', 'win32'
    executable_path TEXT NOT NULL,
    captured_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(language, runtime_name, language_version, platform_triplet, executable_path)
);

-- 2. Distributions: Logical deliverable units (Ambient, Stdlib, or 3rd-party packages)
CREATE TABLE IF NOT EXISTS distributions (
    dist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    env_id INTEGER NOT NULL REFERENCES environments(env_id) ON DELETE CASCADE,
    stratum INTEGER NOT NULL,               -- 0 = Ambient, 1 = Stdlib, 2 = Third-Party, 3 = Workspace
    dist_name TEXT NOT NULL,                -- '<ambient>', 'python-stdlib', 'numpy', 'scikit-learn'
    dist_version TEXT NOT NULL,
    summary TEXT,
    UNIQUE(env_id, stratum, dist_name, dist_version)
);

-- 3. Containers: Universal hierarchy (ambient_scope, package, module, class, exception_class)
CREATE TABLE IF NOT EXISTS containers (
    container_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dist_id INTEGER NOT NULL REFERENCES distributions(dist_id) ON DELETE CASCADE,
    parent_container_id INTEGER REFERENCES containers(container_id) ON DELETE CASCADE,
    container_kind TEXT NOT NULL,           -- 'ambient_scope', 'package', 'module', 'class', 'exception_class'
    qualified_name TEXT NOT NULL,           -- '<ambient>', 'os', 'os.path', '<ambient>.str', 'json.JSONDecoder'
    short_name TEXT NOT NULL,
    requires_import INTEGER NOT NULL DEFAULT 1,
    visibility TEXT NOT NULL,               -- 'public', 'hidden_internal', 'system_dunder'
    is_hidden INTEGER NOT NULL DEFAULT 0,
    physical_path TEXT,
    stub_path TEXT,                         -- Path to overlaid .pyi file if enriched
    sha256_hash TEXT,
    docstring TEXT,
    UNIQUE(dist_id, qualified_name)
);

-- 4. Symbols: Master language-agnostic directory of every callable, variable, constant, property, or keyword
CREATE TABLE IF NOT EXISTS symbols (
    symbol_id INTEGER PRIMARY KEY AUTOINCREMENT,
    container_id INTEGER NOT NULL REFERENCES containers(container_id) ON DELETE CASCADE,
    origin_container_id INTEGER REFERENCES containers(container_id),
    name TEXT NOT NULL,
    qualified_name TEXT NOT NULL,
    symbol_kind TEXT NOT NULL,              -- 'keyword', 'soft_keyword', 'function', 'method', 'constructor',
                                            -- 'class', 'exception', 'constant', 'variable', 'property', 'type_alias'
    visibility TEXT NOT NULL,               -- 'exported_all', 'public_implicit', 'hidden_internal',
                                            -- 'private_mangled', 'system_dunder'
    provenance TEXT NOT NULL,               -- 'defined_here', 're_exported', 'site_injected',
                                            -- 'implicit_dunder', 'pyi_stub_only', 'pyi_enriched'
    is_hidden INTEGER NOT NULL DEFAULT 0,
    docstring TEXT,
    UNIQUE(container_id, name)
);

-- 5. Callables: Universal primary signature & execution modifiers for functions, methods, and constructors
CREATE TABLE IF NOT EXISTS callables (
    symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
    is_async INTEGER NOT NULL DEFAULT 0,
    is_generator INTEGER NOT NULL DEFAULT 0,
    is_static INTEGER NOT NULL DEFAULT 0,
    is_class_bound INTEGER NOT NULL DEFAULT 0,
    has_overloads INTEGER NOT NULL DEFAULT 0,
    overload_count INTEGER NOT NULL DEFAULT 0,
    type_params_json TEXT,                  -- Generic type parameters e.g. '["_T"]'
    return_type_expr TEXT,
    raw_signature TEXT,
    signature_source TEXT NOT NULL          -- 'inspect_signature', 'text_signature', 'docstring_first_line',
                                            -- 'pyi_stub_overlay', 'pyi_overload_overlay', 'unknown'
);

-- 6. Callable Overloads: Stores 1..N static @overload signatures per callable
CREATE TABLE IF NOT EXISTS callable_overloads (
    overload_id INTEGER PRIMARY KEY AUTOINCREMENT,
    callable_symbol_id INTEGER NOT NULL REFERENCES callables(symbol_id) ON DELETE CASCADE,
    overload_ordinal INTEGER NOT NULL,
    type_params_json TEXT,
    return_type_expr TEXT,
    raw_signature TEXT NOT NULL,
    UNIQUE(callable_symbol_id, overload_ordinal)
);

-- 7. Parameters: Ordered parameter list for primary callables (overload_id IS NULL) and @overload variants
CREATE TABLE IF NOT EXISTS parameters (
    param_id INTEGER PRIMARY KEY AUTOINCREMENT,
    callable_symbol_id INTEGER NOT NULL REFERENCES callables(symbol_id) ON DELETE CASCADE,
    overload_id INTEGER REFERENCES callable_overloads(overload_id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    name TEXT NOT NULL,
    pass_kind TEXT NOT NULL,                -- 'positional_only', 'positional_or_keyword', 'var_positional',
                                            -- 'keyword_only', 'var_keyword'
    type_expr TEXT,
    type_source TEXT,                       -- 'runtime_annotation', 'pyi_stub', NULL
    default_expr TEXT,
    is_optional INTEGER NOT NULL DEFAULT 0
);

-- 8. State Members: Ambient constants, module globals, class variables, and properties
CREATE TABLE IF NOT EXISTS state_members (
    symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
    declared_type_expr TEXT,                -- Populated from __annotations__ or .pyi AnnAssign (e.g. 'list[str]')
    runtime_type_name TEXT NOT NULL,        -- Runtime type(obj).__name__ (e.g. 'list')
    is_constant INTEGER NOT NULL DEFAULT 0,
    is_mutable INTEGER NOT NULL DEFAULT 1,
    literal_value_repr TEXT,
    access_mode TEXT NOT NULL DEFAULT 'read_write'
);

-- 9. Symbol Aliases & Re-exports: Tracks cross-module re-exports and imported references
CREATE TABLE IF NOT EXISTS symbol_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_container_id INTEGER NOT NULL REFERENCES containers(container_id) ON DELETE CASCADE,
    exposed_name TEXT NOT NULL,
    target_module_name TEXT NOT NULL,
    target_symbol_name TEXT NOT NULL,
    alias_kind TEXT NOT NULL,               -- 'c_accelerator_reexport', 'explicit_all_reexport',
                                            -- 'imported_module_ref', 'imported_symbol_ref', 'pyi_reexport'
    is_in_dunder_all INTEGER NOT NULL DEFAULT 0,
    UNIQUE(source_container_id, exposed_name)
);

-- ============================================================================
-- PYTHON-SPECIFIC FIDELITY FACET TABLES (1:1 WITH CORE TABLES)
-- ============================================================================

-- 10. Python Container Facets
CREATE TABLE IF NOT EXISTS py_container_facets (
    container_id INTEGER PRIMARY KEY REFERENCES containers(container_id) ON DELETE CASCADE,
    module_origin_kind TEXT,                -- 'ambient', 'builtin_c', 'frozen', 'pure_python', 'c_extension', 'namespace_pkg', 'class_body'
    has_dunder_all INTEGER NOT NULL DEFAULT 0,
    dunder_all_json TEXT,
    has_lazy_getattr INTEGER NOT NULL DEFAULT 0,
    base_classes_json TEXT,
    mro_json TEXT,
    metaclass_name TEXT
);

-- 11. Python Symbol Facets
CREATE TABLE IF NOT EXISTS py_symbol_facets (
    symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
    py_runtime_type TEXT NOT NULL,
    descriptor_kind TEXT,
    is_c_implemented INTEGER NOT NULL DEFAULT 0,
    co_flags INTEGER,
    dunder_category TEXT
);

CREATE INDEX IF NOT EXISTS idx_containers_qname ON containers(qualified_name);
CREATE INDEX IF NOT EXISTS idx_symbols_qname ON symbols(qualified_name);
CREATE INDEX IF NOT EXISTS idx_symbols_container_name ON symbols(container_id, name);
CREATE INDEX IF NOT EXISTS idx_params_callable ON parameters(callable_symbol_id, overload_id, ordinal);
CREATE INDEX IF NOT EXISTS idx_overloads_callable ON callable_overloads(callable_symbol_id, overload_ordinal);
"""


# ============================================================================
# 2. CLASSIFICATION & RUNTIME INTROSPECTION HELPERS
# ============================================================================

DUNDER_CATEGORIES: dict[str, str] = {
    "__new__": "lifecycle", "__init__": "lifecycle", "__del__": "lifecycle",
    "__init_subclass__": "meta", "__class_getitem__": "meta", "__mro_entries__": "meta", "__prepare__": "meta",
    "__repr__": "representation", "__str__": "representation", "__bytes__": "representation", "__format__": "representation",
    "__lt__": "comparison", "__le__": "comparison", "__eq__": "comparison",
    "__ne__": "comparison", "__gt__": "comparison", "__ge__": "comparison", "__hash__": "comparison", "__bool__": "comparison",
    "__getattr__": "attribute_access", "__getattribute__": "attribute_access",
    "__setattr__": "attribute_access", "__delattr__": "attribute_access", "__dir__": "attribute_access",
    "__get__": "descriptor", "__set__": "descriptor", "__delete__": "descriptor", "__set_name__": "descriptor",
    "__call__": "callable",
    "__len__": "container", "__length_hint__": "container", "__getitem__": "container",
    "__setitem__": "container", "__delitem__": "container", "__missing__": "container",
    "__iter__": "container", "__reversed__": "container", "__contains__": "container",
    "__enter__": "context_manager", "__exit__": "context_manager",
    "__await__": "async", "__aiter__": "async", "__anext__": "async", "__aenter__": "async", "__aexit__": "async",
    "__add__": "numeric", "__sub__": "numeric", "__mul__": "numeric", "__matmul__": "numeric",
    "__truediv__": "numeric", "__floordiv__": "numeric", "__mod__": "numeric", "__divmod__": "numeric",
    "__pow__": "numeric", "__lshift__": "numeric", "__rshift__": "numeric",
    "__and__": "numeric", "__xor__": "numeric", "__or__": "numeric",
    "__neg__": "numeric", "__pos__": "numeric", "__abs__": "numeric", "__invert__": "numeric",
    "__int__": "numeric", "__float__": "numeric", "__complex__": "numeric", "__index__": "numeric",
    "__round__": "numeric", "__trunc__": "numeric", "__floor__": "numeric", "__ceil__": "numeric",
}


def classify_identifier_visibility(name: str, dunder_all: set[str] | None = None) -> tuple[str, int]:
    if name.startswith("__") and name.endswith("__") and len(name) > 4:
        return ("system_dunder", 0)
    if name.startswith("__") and not name.endswith("__"):
        return ("private_mangled", 1)
    if name.startswith("_"):
        return ("hidden_internal", 1)
    if dunder_all is not None and name in dunder_all:
        return ("exported_all", 0)
    return ("public_implicit", 0)


def safe_repr(val: Any, max_len: int = 160) -> str | None:
    try:
        if isinstance(val, (int, float, bool, str, bytes, complex)) or val is None or val is Ellipsis or val is NotImplemented:
            r = repr(val)
            return r if len(r) <= max_len else r[: max_len - 3] + "..."
        return f"<{type(val).__name__}>"
    except Exception:
        return "<unrepresentable>"


def compute_file_sha256(path_str: str | None) -> str | None:
    if not path_str:
        return None
    p = Path(path_str)
    if not p.is_file():
        return None
    try:
        return hashlib.sha256(p.read_bytes()).hexdigest()
    except OSError:
        return None


def get_pure_builtins_without_site() -> set[str]:
    try:
        out = subprocess.check_output(
            [sys.executable, "-S", "-c", "import builtins, json; print(json.dumps(list(builtins.__dict__.keys())))"],
            text=True,
            timeout=5,
        )
        return set(json.loads(out.strip()))
    except Exception:
        return set(builtins.__dict__.keys())


def extract_callable_signature(obj: Any) -> tuple[str | None, str, str | None, list[dict[str, Any]]]:
    params_list: list[dict[str, Any]] = []
    try:
        sig = inspect.signature(obj)
        ret_expr = None
        if sig.return_annotation is not inspect.Signature.empty:
            ret_expr = (
                sig.return_annotation
                if isinstance(sig.return_annotation, str)
                else getattr(sig.return_annotation, "__name__", str(sig.return_annotation))
            )

        for idx, (_, param) in enumerate(sig.parameters.items()):
            kind_map = {
                inspect.Parameter.POSITIONAL_ONLY: "positional_only",
                inspect.Parameter.POSITIONAL_OR_KEYWORD: "positional_or_keyword",
                inspect.Parameter.VAR_POSITIONAL: "var_positional",
                inspect.Parameter.KEYWORD_ONLY: "keyword_only",
                inspect.Parameter.VAR_KEYWORD: "var_keyword",
            }
            ann_str = None
            if param.annotation is not inspect.Parameter.empty:
                ann_str = (
                    param.annotation
                    if isinstance(param.annotation, str)
                    else getattr(param.annotation, "__name__", str(param.annotation))
                )
            def_str = None
            is_opt = 0
            if param.default is not inspect.Parameter.empty:
                def_str = safe_repr(param.default, 80)
                is_opt = 1
            elif param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
                is_opt = 1

            params_list.append({
                "ordinal": idx,
                "name": param.name,
                "pass_kind": kind_map.get(param.kind, "positional_or_keyword"),
                "type_expr": ann_str,
                "type_source": "runtime_annotation" if ann_str is not None else None,
                "default_expr": def_str,
                "is_optional": is_opt,
            })

        source = "text_signature" if getattr(obj, "__text_signature__", None) else "inspect_signature"
        return (str(sig), source, ret_expr, params_list)
    except (ValueError, TypeError):
        doc = getattr(obj, "__doc__", None)
        if isinstance(doc, str) and doc.strip():
            first_line = doc.strip().splitlines()[0].strip()
            if "(" in first_line and ")" in first_line:
                return (first_line, "docstring_first_line", None, [])
        return (None, "unknown", None, [])


# ============================================================================
# 3. RUNTIME SPECTRUM HARVESTER (STRATA 0, 1, 2)
# ============================================================================

class PythonSpectrumCataloger:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.env_id: int = -1
        self.pure_builtin_names: set[str] = get_pure_builtins_without_site()

    def init_db(self, reset: bool = False) -> None:
        if reset:
            for tbl in (
                "py_symbol_facets", "py_container_facets", "symbol_aliases",
                "state_members", "parameters", "callable_overloads", "callables",
                "symbols", "containers", "distributions", "environments",
            ):
                self.conn.execute(f"DROP TABLE IF EXISTS {tbl};")
        self.conn.executescript(SCHEMA_SQL)
        self.conn.commit()

    def register_environment(self) -> int:
        vi = sys.version_info
        plat = f"{platform.system()}-{platform.machine()}"
        cur = self.conn.execute(
            """
            INSERT INTO environments (
                language, runtime_name, language_version,
                version_major, version_minor, version_micro,
                platform_triplet, sys_platform, executable_path
            )
            VALUES ('python', ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(language, runtime_name, language_version, platform_triplet, executable_path)
            DO UPDATE SET captured_at = CURRENT_TIMESTAMP
            RETURNING env_id
            """,
            (
                platform.python_implementation(),
                platform.python_version(),
                vi.major,
                vi.minor,
                vi.micro,
                plat,
                sys.platform,
                sys.executable,
            ),
        )
        self.env_id = int(cur.fetchone()[0])
        self.conn.commit()
        return self.env_id

    def register_distribution(self, stratum: int, dist_name: str, dist_version: str, summary: str | None = None) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO distributions (env_id, stratum, dist_name, dist_version, summary)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(env_id, stratum, dist_name, dist_version)
            DO UPDATE SET summary = COALESCE(excluded.summary, distributions.summary)
            RETURNING dist_id
            """,
            (self.env_id, stratum, dist_name, dist_version, summary),
        )
        return int(cur.fetchone()[0])

    def register_container(
        self,
        *,
        dist_id: int,
        parent_id: int | None,
        container_kind: str,
        qualified_name: str,
        short_name: str,
        requires_import: int,
        visibility: str,
        is_hidden: int,
        physical_path: str | None = None,
        docstring: str | None = None,
        module_origin_kind: str | None = None,
        dunder_all: list[str] | None = None,
        has_lazy_getattr: bool = False,
        base_classes: list[str] | None = None,
        mro_list: list[str] | None = None,
        metaclass_name: str | None = None,
    ) -> int:
        sha = compute_file_sha256(physical_path)
        cur = self.conn.execute(
            """
            INSERT INTO containers (
                dist_id, parent_container_id, container_kind, qualified_name,
                short_name, requires_import, visibility, is_hidden,
                physical_path, sha256_hash, docstring
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(dist_id, qualified_name) DO UPDATE SET
                physical_path = COALESCE(excluded.physical_path, containers.physical_path),
                docstring = COALESCE(excluded.docstring, containers.docstring)
            RETURNING container_id
            """,
            (
                dist_id, parent_id, container_kind, qualified_name,
                short_name, requires_import, visibility, is_hidden,
                physical_path, sha, docstring,
            ),
        )
        cid = int(cur.fetchone()[0])

        self.conn.execute(
            """
            INSERT INTO py_container_facets (
                container_id, module_origin_kind, has_dunder_all, dunder_all_json,
                has_lazy_getattr, base_classes_json, mro_json, metaclass_name
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(container_id) DO UPDATE SET
                module_origin_kind = COALESCE(excluded.module_origin_kind, py_container_facets.module_origin_kind)
            """,
            (
                cid,
                module_origin_kind,
                1 if dunder_all is not None else 0,
                json.dumps(dunder_all) if dunder_all is not None else None,
                1 if has_lazy_getattr else 0,
                json.dumps(base_classes) if base_classes is not None else None,
                json.dumps(mro_list) if mro_list is not None else None,
                metaclass_name,
            ),
        )
        return cid

    def harvest_stratum_0_ambient(self) -> None:
        py_ver = platform.python_version()
        dist_id = self.register_distribution(
            stratum=0,
            dist_name="<ambient>",
            dist_version=py_ver,
            summary="Unqualified Python ambient scope: keywords, builtins, site-builtins, and implicit module dunders.",
        )

        ambient_cid = self.register_container(
            dist_id=dist_id,
            parent_id=None,
            container_kind="ambient_scope",
            qualified_name="<ambient>",
            short_name="<ambient>",
            requires_import=0,
            visibility="public",
            is_hidden=0,
            docstring="Symbols and syntax constructs available in Python without any import statement.",
            module_origin_kind="ambient",
        )

        for kw in keyword.kwlist:
            self._insert_keyword_symbol(ambient_cid, kw, is_soft=False)
        for skw in getattr(keyword, "softkwlist", []):
            self._insert_keyword_symbol(ambient_cid, skw, is_soft=True)

        for d_name, d_type, d_doc in IMPLICIT_MODULE_DUNDERS:
            cur = self.conn.execute(
                """
                INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name,
                    symbol_kind, visibility, provenance, is_hidden, docstring
                )
                VALUES (?, ?, ?, ?, 'variable', 'system_dunder', 'implicit_dunder', 0, ?)
                ON CONFLICT(container_id, name) DO NOTHING
                RETURNING symbol_id
                """,
                (ambient_cid, ambient_cid, d_name, f"<ambient>.{d_name}", d_doc),
            )
            row = cur.fetchone()
            if row:
                sid = int(row[0])
                self.conn.execute(
                    """
                    INSERT INTO state_members (
                        symbol_id, declared_type_expr, runtime_type_name,
                        is_constant, is_mutable, literal_value_repr, access_mode
                    )
                    VALUES (?, ?, ?, 0, 1, NULL, 'read_write')
                    """,
                    (sid, d_type, d_type),
                )
                self.conn.execute(
                    """
                    INSERT INTO py_symbol_facets (symbol_id, py_runtime_type, is_c_implemented, dunder_category)
                    VALUES (?, 'implicit_module_dunder', 1, 'meta')
                    """,
                    (sid,),
                )

        for name, obj in sorted(builtins.__dict__.items()):
            provenance = "defined_here" if name in self.pure_builtin_names else "site_injected"
            self._harvest_runtime_member(
                dist_id=dist_id,
                parent_cid=ambient_cid,
                parent_qname="<ambient>",
                module_name="builtins",
                name=name,
                obj=obj,
                dunder_all=None,
                requires_import=0,
                override_provenance=provenance,
            )

        self.conn.commit()

    def _insert_keyword_symbol(self, ambient_cid: int, kw: str, *, is_soft: bool) -> None:
        kind = "soft_keyword" if is_soft else "keyword"
        cur = self.conn.execute(
            """
            INSERT INTO symbols (
                container_id, origin_container_id, name, qualified_name,
                symbol_kind, visibility, provenance, is_hidden, docstring
            )
            VALUES (?, ?, ?, ?, ?, 'public_implicit', 'defined_here', 0, ?)
            ON CONFLICT(container_id, name) DO NOTHING
            RETURNING symbol_id
            """,
            (
                ambient_cid,
                ambient_cid,
                kw,
                f"<ambient>.{kw}",
                kind,
                f"Python {'soft ' if is_soft else ''}keyword `{kw}`.",
            ),
        )
        row = cur.fetchone()
        if row:
            self.conn.execute(
                """
                INSERT INTO py_symbol_facets (symbol_id, py_runtime_type, is_c_implemented)
                VALUES (?, ?, 1)
                """,
                (int(row[0]), kind),
            )

    def discover_stdlib_modules(self, include_submodules: bool = False) -> list[str]:
        names: set[str] = set(sys.builtin_module_names)
        if hasattr(sys, "stdlib_module_names"):
            names.update(sys.stdlib_module_names)

        for path_key in ("stdlib", "platstdlib"):
            p_str = sysconfig.get_path(path_key)
            if p_str and Path(p_str).is_dir():
                for mod_info in pkgutil.iter_modules([p_str]):
                    names.add(mod_info.name)

        filtered = sorted(
            n for n in names
            if n not in SIDE_EFFECT_STDLIB_MODULES and not n.startswith("test.")
        )

        if not include_submodules:
            return filtered

        expanded: list[str] = []
        for mod_name in filtered:
            expanded.append(mod_name)
            try:
                spec = importlib.util.find_spec(mod_name)
                if spec and spec.submodule_search_locations:
                    for sub in pkgutil.walk_packages(spec.submodule_search_locations, prefix=f"{mod_name}."):
                        if not any(part in SIDE_EFFECT_STDLIB_MODULES for part in sub.name.split(".")):
                            expanded.append(sub.name)
            except Exception:
                continue
        return sorted(set(expanded))

    def harvest_stratum_1_stdlib(self, module_filter: set[str] | None = None, include_submodules: bool = False) -> None:
        py_ver = platform.python_version()
        dist_id = self.register_distribution(
            stratum=1,
            dist_name="python-stdlib",
            dist_version=py_ver,
            summary=f"Standard library and compiled-in modules shipped with {platform.python_implementation()} {py_ver}.",
        )

        candidates = self.discover_stdlib_modules(include_submodules=include_submodules)
        if module_filter:
            candidates = [
                m for m in candidates
                if m in module_filter or m.split(".")[0] in module_filter
            ]

        for mod_name in candidates:
            self.harvest_module_by_name(dist_id=dist_id, mod_name=mod_name)
        self.conn.commit()

    def harvest_stratum_2_third_party(self, target_packages: set[str] | None = None) -> None:
        pkg_to_dists = importlib.metadata.packages_distributions()
        visited_dists: set[tuple[str, str]] = set()

        for dist in importlib.metadata.distributions():
            dist_name = dist.metadata["Name"] or "unknown"
            dist_ver = dist.version or "0.0.0"
            if (dist_name, dist_ver) in visited_dists:
                continue
            visited_dists.add((dist_name, dist_ver))

            summary = dist.metadata.get("Summary")
            dist_id = self.register_distribution(
                stratum=2,
                dist_name=dist_name,
                dist_version=dist_ver,
                summary=summary,
            )

            if target_packages is not None:
                top_pkgs = [
                    pkg for pkg, d_names in pkg_to_dists.items()
                    if dist_name in d_names
                ]
                if dist_name not in target_packages and not any(p in target_packages for p in top_pkgs):
                    continue
                for pkg in sorted(set(top_pkgs)):
                    if pkg in target_packages or dist_name in target_packages:
                        self.harvest_module_by_name(dist_id=dist_id, mod_name=pkg)
        self.conn.commit()

    def _classify_module_origin(self, mod_name: str, mod: types.ModuleType) -> tuple[str, str | None]:
        if mod_name in sys.builtin_module_names:
            return ("builtin_c", None)
        spec = getattr(mod, "__spec__", None)
        origin = getattr(spec, "origin", None) if spec else getattr(mod, "__file__", None)
        if origin == "frozen" or (spec and getattr(spec, "loader", None) and "Frozen" in type(spec.loader).__name__):
            return ("frozen", None)
        if origin == "built-in":
            return ("builtin_c", None)
        if spec and spec.submodule_search_locations and origin is None:
            return ("namespace_pkg", None)
        if isinstance(origin, str):
            for ext in importlib.machinery.EXTENSION_SUFFIXES:
                if origin.endswith(ext):
                    return ("c_extension", origin)
            return ("pure_python", origin)
        return ("unknown", None)

    def harvest_module_by_name(self, dist_id: int, mod_name: str) -> int | None:
        if mod_name in SIDE_EFFECT_STDLIB_MODULES:
            return None
        try:
            mod = importlib.import_module(mod_name)
        except Exception:
            return None

        origin_kind, phys_path = self._classify_module_origin(mod_name, mod)
        is_pkg = hasattr(mod, "__path__")
        container_kind = "package" if is_pkg else "module"
        short_name = mod_name.rsplit(".", 1)[-1]
        vis, is_hid = classify_identifier_visibility(short_name)

        raw_all = getattr(mod, "__all__", None)
        dunder_all_list = [str(x) for x in raw_all] if isinstance(raw_all, (list, tuple, set, frozenset)) else None
        dunder_all_set = set(dunder_all_list) if dunder_all_list is not None else None
        has_lazy_getattr = "__getattr__" in mod.__dict__

        parent_cid: int | None = None
        if "." in mod_name:
            parent_name = mod_name.rsplit(".", 1)[0]
            row = self.conn.execute(
                "SELECT container_id FROM containers WHERE dist_id = ? AND qualified_name = ? LIMIT 1",
                (dist_id, parent_name),
            ).fetchone()
            if row:
                parent_cid = int(row[0])

        mod_cid = self.register_container(
            dist_id=dist_id,
            parent_id=parent_cid,
            container_kind=container_kind,
            qualified_name=mod_name,
            short_name=short_name,
            requires_import=1,
            visibility=vis,
            is_hidden=is_hid,
            physical_path=phys_path,
            docstring=inspect.getdoc(mod),
            module_origin_kind=origin_kind,
            dunder_all=dunder_all_list,
            has_lazy_getattr=has_lazy_getattr,
        )

        mod_annotations = getattr(mod, "__annotations__", {}) or {}

        for attr_name, obj in sorted(mod.__dict__.items()):
            if attr_name in IMPLICIT_MODULE_DUNDERS or attr_name in ("__all__", "__path__"):
                continue

            if isinstance(obj, types.ModuleType):
                target_mod_name = getattr(obj, "__name__", attr_name)
                in_all = 1 if (dunder_all_set and attr_name in dunder_all_set) else 0
                self.conn.execute(
                    """
                    INSERT INTO symbol_aliases (
                        source_container_id, exposed_name, target_module_name,
                        target_symbol_name, alias_kind, is_in_dunder_all
                    )
                    VALUES (?, ?, ?, '<module>', 'imported_module_ref', ?)
                    ON CONFLICT(source_container_id, exposed_name) DO NOTHING
                    """,
                    (mod_cid, attr_name, target_mod_name, in_all),
                )
                continue

            obj_mod = getattr(obj, "__module__", None)
            if isinstance(obj_mod, str) and obj_mod != mod_name:
                in_all = dunder_all_set is not None and attr_name in dunder_all_set
                is_backing_c_mod = (
                    obj_mod.startswith(f"_{mod_name.split('.')[0]}")
                    or obj_mod.startswith(f"{mod_name}._")
                    or (mod_name == "os" and obj_mod in ("posix", "nt", "genericpath", "posixpath", "ntpath"))
                )
                alias_kind = (
                    "c_accelerator_reexport"
                    if is_backing_c_mod
                    else ("explicit_all_reexport" if in_all else "imported_symbol_ref")
                )
                self.conn.execute(
                    """
                    INSERT INTO symbol_aliases (
                        source_container_id, exposed_name, target_module_name,
                        target_symbol_name, alias_kind, is_in_dunder_all
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    ON CONFLICT(source_container_id, exposed_name) DO NOTHING
                    """,
                    (
                        mod_cid,
                        attr_name,
                        obj_mod,
                        getattr(obj, "__name__", attr_name),
                        alias_kind,
                        1 if in_all else 0,
                    ),
                )
                if not in_all and not is_backing_c_mod:
                    continue
                provenance = "re_exported"
            else:
                provenance = "defined_here"

            decl_ann = mod_annotations.get(attr_name)
            decl_type_str = str(decl_ann) if decl_ann is not None else None

            self._harvest_runtime_member(
                dist_id=dist_id,
                parent_cid=mod_cid,
                parent_qname=mod_name,
                module_name=mod_name,
                name=attr_name,
                obj=obj,
                dunder_all=dunder_all_set,
                requires_import=1,
                override_provenance=provenance,
                declared_type_expr=decl_type_str,
            )

        return mod_cid

    def _harvest_runtime_member(
        self,
        *,
        dist_id: int,
        parent_cid: int,
        parent_qname: str,
        module_name: str,
        name: str,
        obj: Any,
        dunder_all: set[str] | None,
        requires_import: int,
        override_provenance: str,
        is_inside_class: bool = False,
        declared_type_expr: str | None = None,
    ) -> None:
        vis, is_hid = classify_identifier_visibility(name, dunder_all)
        qname = f"{parent_qname}.{name}"
        py_type_name = type(obj).__name__
        dunder_cat = DUNDER_CATEGORIES.get(name)

        if inspect.isclass(obj):
            is_exc = issubclass(obj, BaseException)
            sym_kind = "exception" if is_exc else "class"
            container_kind = "exception_class" if is_exc else "class"

            bases = [f"{b.__module__}.{b.__qualname__}" for b in getattr(obj, "__bases__", ())]
            mro = [f"{c.__module__}.{c.__qualname__}" for c in getattr(obj, "__mro__", ())]

            cur = self.conn.execute(
                """
                INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name,
                    symbol_kind, visibility, provenance, is_hidden, docstring
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(container_id, name) DO NOTHING
                RETURNING symbol_id
                """,
                (parent_cid, parent_cid, name, qname, sym_kind, vis, override_provenance, is_hid, inspect.getdoc(obj)),
            )
            row = cur.fetchone()
            if row:
                sid = int(row[0])
                self.conn.execute(
                    """
                    INSERT INTO py_symbol_facets (symbol_id, py_runtime_type, is_c_implemented, dunder_category)
                    VALUES (?, ?, ?, ?)
                    """,
                    (sid, py_type_name, 0 if hasattr(obj, "__dict__") and "__module__" in obj.__dict__ else 1, dunder_cat),
                )
                raw_sig, sig_src, ret_expr, params = extract_callable_signature(obj)
                self._insert_callable_and_params(
                    sid,
                    is_async=0,
                    is_generator=0,
                    is_static=0,
                    is_class_bound=1,
                    return_type_expr=name,
                    raw_signature=raw_sig,
                    signature_source=sig_src,
                    params=params,
                )

            if is_inside_class:
                return

            cls_cid = self.register_container(
                dist_id=dist_id,
                parent_id=parent_cid,
                container_kind=container_kind,
                qualified_name=qname,
                short_name=name,
                requires_import=requires_import,
                visibility=vis,
                is_hidden=is_hid,
                docstring=inspect.getdoc(obj),
                module_origin_kind="class_body",
                base_classes=bases,
                mro_list=mro,
                metaclass_name=type(obj).__name__,
            )

            cls_annotations = getattr(obj, "__annotations__", {}) or {}
            for m_name, m_obj in sorted(obj.__dict__.items()):
                if m_name in ("__dict__", "__weakref__", "__doc__", "__module__"):
                    continue
                m_ann = cls_annotations.get(m_name)
                self._harvest_runtime_member(
                    dist_id=dist_id,
                    parent_cid=cls_cid,
                    parent_qname=qname,
                    module_name=module_name,
                    name=m_name,
                    obj=m_obj,
                    dunder_all=None,
                    requires_import=requires_import,
                    override_provenance="defined_here",
                    is_inside_class=True,
                    declared_type_expr=str(m_ann) if m_ann is not None else None,
                )
            return

        if isinstance(obj, property) or py_type_name in ("getset_descriptor", "member_descriptor", "DynamicClassAttribute"):
            acc_mode = "read_only"
            if isinstance(obj, property) and obj.fset is not None:
                acc_mode = "read_write_delete" if obj.fdel is not None else "read_write"
            elif py_type_name in ("getset_descriptor", "member_descriptor"):
                acc_mode = "read_write"

            cur = self.conn.execute(
                """
                INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name,
                    symbol_kind, visibility, provenance, is_hidden, docstring
                )
                VALUES (?, ?, ?, ?, 'property', ?, ?, ?, ?)
                ON CONFLICT(container_id, name) DO NOTHING
                RETURNING symbol_id
                """,
                (parent_cid, parent_cid, name, qname, vis, override_provenance, is_hid, inspect.getdoc(obj)),
            )
            row = cur.fetchone()
            if row:
                sid = int(row[0])
                self.conn.execute(
                    """
                    INSERT INTO state_members (
                        symbol_id, declared_type_expr, runtime_type_name,
                        is_constant, is_mutable, literal_value_repr, access_mode
                    )
                    VALUES (?, ?, ?, 0, 1, NULL, ?)
                    """,
                    (sid, declared_type_expr, py_type_name, acc_mode),
                )
                self.conn.execute(
                    """
                    INSERT INTO py_symbol_facets (symbol_id, py_runtime_type, descriptor_kind, is_c_implemented, dunder_category)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (sid, py_type_name, py_type_name, 0 if isinstance(obj, property) else 1, dunder_cat),
                )
            return

        is_static = 0 if is_inside_class else 1
        is_class_bound = 0
        descriptor_kind: str | None = None
        underlying_obj = obj
        if isinstance(obj, staticmethod):
            is_static = 1
            descriptor_kind = "staticmethod"
            underlying_obj = obj.__func__
        elif isinstance(obj, classmethod):
            is_static = 0
            is_class_bound = 1
            descriptor_kind = "classmethod"
            underlying_obj = obj.__func__
        elif py_type_name == "classmethod_descriptor":
            is_class_bound = 1
            descriptor_kind = "classmethod_descriptor"

        if callable(underlying_obj) or py_type_name in (
            "method_descriptor", "wrapper_descriptor", "builtin_function_or_method", "classmethod_descriptor"
        ):
            sym_kind = "constructor" if name in ("__init__", "__new__") else ("method" if is_inside_class else "function")
            is_async = 1 if inspect.iscoroutinefunction(underlying_obj) or inspect.isasyncgenfunction(underlying_obj) else 0
            is_gen = 1 if inspect.isgeneratorfunction(underlying_obj) or inspect.isasyncgenfunction(underlying_obj) else 0
            code_obj = getattr(underlying_obj, "__code__", None)
            co_flags = getattr(code_obj, "co_flags", None)
            is_c_impl = 1 if code_obj is None else 0

            cur = self.conn.execute(
                """
                INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name,
                    symbol_kind, visibility, provenance, is_hidden, docstring
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(container_id, name) DO NOTHING
                RETURNING symbol_id
                """,
                (parent_cid, parent_cid, name, qname, sym_kind, vis, override_provenance, is_hid, inspect.getdoc(underlying_obj)),
            )
            row = cur.fetchone()
            if row:
                sid = int(row[0])
                raw_sig, sig_src, ret_expr, params = extract_callable_signature(underlying_obj)
                self._insert_callable_and_params(
                    sid,
                    is_async=is_async,
                    is_generator=is_gen,
                    is_static=is_static,
                    is_class_bound=is_class_bound,
                    return_type_expr=ret_expr,
                    raw_signature=raw_sig,
                    signature_source=sig_src,
                    params=params,
                )
                self.conn.execute(
                    """
                    INSERT INTO py_symbol_facets (
                        symbol_id, py_runtime_type, descriptor_kind,
                        is_c_implemented, co_flags, dunder_category
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (sid, py_type_name, descriptor_kind or py_type_name, is_c_impl, co_flags, dunder_cat),
                )
            return

        is_const = 1 if (name.isupper() or name in ("True", "False", "None", "Ellipsis", "NotImplemented", "__debug__")) else 0
        is_mut = 0 if isinstance(obj, (int, float, str, bytes, tuple, frozenset, bool)) or obj is None else 1
        sym_kind = "constant" if is_const else "variable"

        cur = self.conn.execute(
            """
            INSERT INTO symbols (
                container_id, origin_container_id, name, qualified_name,
                symbol_kind, visibility, provenance, is_hidden, docstring
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)
            ON CONFLICT(container_id, name) DO NOTHING
            RETURNING symbol_id
            """,
            (parent_cid, parent_cid, name, qname, sym_kind, vis, override_provenance, is_hid),
        )
        row = cur.fetchone()
        if row:
            sid = int(row[0])
            self.conn.execute(
                """
                INSERT INTO state_members (
                    symbol_id, declared_type_expr, runtime_type_name,
                    is_constant, is_mutable, literal_value_repr, access_mode
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    sid,
                    declared_type_expr,
                    py_type_name,
                    is_const,
                    is_mut,
                    safe_repr(obj),
                    "read_only" if is_const else "read_write",
                ),
            )
            self.conn.execute(
                """
                INSERT INTO py_symbol_facets (symbol_id, py_runtime_type, is_c_implemented, dunder_category)
                VALUES (?, ?, 1, ?)
                """,
                (sid, py_type_name, dunder_cat),
            )

    def _insert_callable_and_params(
        self,
        symbol_id: int,
        *,
        is_async: int,
        is_generator: int,
        is_static: int,
        is_class_bound: int,
        return_type_expr: str | None,
        raw_signature: str | None,
        signature_source: str,
        params: list[dict[str, Any]],
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO callables (
                symbol_id, is_async, is_generator, is_static, is_class_bound,
                return_type_expr, raw_signature, signature_source
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol_id) DO NOTHING
            """,
            (symbol_id, is_async, is_generator, is_static, is_class_bound, return_type_expr, raw_signature, signature_source),
        )
        for p in params:
            self.conn.execute(
                """
                INSERT INTO parameters (
                    callable_symbol_id, overload_id, ordinal, name, pass_kind,
                    type_expr, type_source, default_expr, is_optional
                )
                VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    symbol_id,
                    p["ordinal"],
                    p["name"],
                    p["pass_kind"],
                    p["type_expr"],
                    p.get("type_source"),
                    p["default_expr"],
                    p["is_optional"],
                ),
            )


# ============================================================================
# 4. PASS 4: STATIC .pyi (TYPESHED) AST OVERLAY ENGINE
# ============================================================================

class StaticPyiOverlayCataloger:
    """
    Overlays static type signatures, `@overload` variants, and generic variable annotations
    from `.pyi` stub files (Typeshed or embedded stubs) onto the runtime catalog.
    Never imports or executes code; uses pure Python `ast` analysis + static branch evaluation.
    """

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.py_version: tuple[int, int] = (sys.version_info.major, sys.version_info.minor)
        self.sys_platform: str = sys.platform
        self.enriched_callables: int = 0
        self.inserted_overloads: int = 0
        self.enriched_state_members: int = 0
        self.stub_only_symbols: int = 0

    @staticmethod
    def auto_discover_typeshed_dirs() -> list[Path]:
        """Searches installed site-packages (mypy, pyright, typeshed_client) for stdlib .pyi directories."""
        found: list[Path] = []
        for site_dir in sys.path:
            if not site_dir:
                continue
            base = Path(site_dir)
            candidates = [
                base / "mypy" / "typeshed" / "stdlib",
                base / "typeshed_client" / "typeshed",
                base / "pyright" / "dist" / "typeshed-fallback" / "stdlib",
            ]
            for c in candidates:
                if c.is_dir() and (c / "builtins.pyi").is_file():
                    found.append(c)
        return found

    def resolve_stub_file(self, typeshed_root: Path, mod_name: str) -> Path | None:
        """Resolves a dotted module name to its `.pyi` file inside a typeshed root."""
        stdlib_dir = typeshed_root / "stdlib" if (typeshed_root / "stdlib").is_dir() else typeshed_root
        parts = mod_name.split(".")
        rel_file = stdlib_dir.joinpath(*parts).with_suffix(".pyi")
        if rel_file.is_file():
            return rel_file
        rel_init = stdlib_dir.joinpath(*parts, "__init__.pyi")
        if rel_init.is_file():
            return rel_init
        # Also check third-party `stubs/<dist>/<mod>` if typeshed_root has a `stubs/` folder
        stubs_dir = typeshed_root / "stubs"
        if stubs_dir.is_dir():
            for pkg_dir in stubs_dir.iterdir():
                cand_file = pkg_dir.joinpath(*parts).with_suffix(".pyi")
                if cand_file.is_file():
                    return cand_file
                cand_init = pkg_dir.joinpath(*parts, "__init__.pyi")
                if cand_init.is_file():
                    return cand_init
        return None

    def overlay_from_directory(self, typeshed_root: Path, module_filter: set[str] | None = None) -> None:
        """Applies `.pyi` overlays for `<ambient>` (`builtins.pyi`) and harvested modules in the DB."""
        rows = self.conn.execute(
            """
            SELECT container_id, qualified_name
            FROM containers
            WHERE container_kind IN ('ambient_scope', 'module', 'package')
            """
        ).fetchall()

        for cid, qname in rows:
            lookup_mod = "builtins" if qname == "<ambient>" else qname
            if module_filter and lookup_mod != "builtins" and lookup_mod not in module_filter:
                continue
            stub_path = self.resolve_stub_file(typeshed_root, lookup_mod)
            if stub_path is not None:
                try:
                    source = stub_path.read_text(encoding="utf-8")
                    self.overlay_stub_source(
                        container_id=int(cid),
                        container_qname=qname,
                        stub_source=source,
                        stub_path_str=str(stub_path),
                    )
                except Exception:
                    continue
        self.conn.commit()

    def overlay_embedded_demo_stubs(self) -> None:
        """Overlays the built-in EMBEDDED_DEMO_STUBS (`builtins`, `sys`, `os`, `json`) for instant clean-room testing."""
        for mod_key, stub_src in EMBEDDED_DEMO_STUBS.items():
            qname = "<ambient>" if mod_key == "builtins" else mod_key
            row = self.conn.execute(
                "SELECT container_id FROM containers WHERE qualified_name = ? LIMIT 1",
                (qname,),
            ).fetchone()
            if row:
                self.overlay_stub_source(
                    container_id=int(row[0]),
                    container_qname=qname,
                    stub_source=stub_src,
                    stub_path_str=f"<embedded-typeshed:{mod_key}.pyi>",
                )
        self.conn.commit()

    def overlay_stub_source(
        self,
        *,
        container_id: int,
        container_qname: str,
        stub_source: str,
        stub_path_str: str,
    ) -> None:
        tree = ast.parse(stub_source, filename=stub_path_str)
        self.conn.execute(
            "UPDATE containers SET stub_path = ? WHERE container_id = ?",
            (stub_path_str, container_id),
        )
        active_stmts = self._flatten_active_statements(tree.body)
        self._apply_statements_to_container(container_id, container_qname, active_stmts, is_class_scope=False)

    # ------------------------------------------------------------------------
    # Static Evaluation of `if sys.version_info` and `if sys.platform` Guards
    # ------------------------------------------------------------------------

    def _flatten_active_statements(self, stmts: list[ast.stmt]) -> list[ast.stmt]:
        out: list[ast.stmt] = []
        for stmt in stmts:
            if isinstance(stmt, ast.If):
                branch_val = self._eval_static_guard(stmt.test)
                if branch_val is True:
                    out.extend(self._flatten_active_statements(stmt.body))
                elif branch_val is False:
                    out.extend(self._flatten_active_statements(stmt.orelse))
                else:
                    # Unknown condition: conservatively take the primary body
                    out.extend(self._flatten_active_statements(stmt.body))
            else:
                out.append(stmt)
        return out

    def _eval_static_guard(self, test: ast.expr) -> bool | None:
        """Evaluates `sys.version_info >= (3, 12)` and `sys.platform == 'linux'` AST expressions."""
        if isinstance(test, ast.BoolOp):
            vals = [self._eval_static_guard(v) for v in test.values]
            if isinstance(test.op, ast.And):
                if any(v is False for v in vals):
                    return False
                if all(v is True for v in vals):
                    return True
                return None
            if isinstance(test.op, ast.Or):
                if any(v is True for v in vals):
                    return True
                if all(v is False for v in vals):
                    return False
                return None

        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            inner = self._eval_static_guard(test.operand)
            return (not inner) if inner is not None else None

        if isinstance(test, ast.Compare) and len(test.ops) == 1 and len(test.comparators) == 1:
            left_s = ast.unparse(test.left).strip()
            op = test.ops[0]
            right_node = test.comparators[0]

            if left_s in ("sys.version_info", "version_info") and isinstance(right_node, ast.Tuple):
                try:
                    ver_tuple = tuple(int(ast.literal_eval(elt)) for elt in right_node.elts[:2])
                    lhs = self.py_version[: len(ver_tuple)]
                    return self._apply_cmp(lhs, op, ver_tuple)
                except Exception:
                    return None

            if left_s in ("sys.platform", "platform") and isinstance(right_node, ast.Constant) and isinstance(right_node.value, str):
                return self._apply_cmp(self.sys_platform, op, right_node.value)

        return None

    @staticmethod
    def _apply_cmp(lhs: Any, op: ast.cmpop, rhs: Any) -> bool | None:
        if isinstance(op, ast.GtE):
            return bool(lhs >= rhs)
        if isinstance(op, ast.Gt):
            return bool(lhs > rhs)
        if isinstance(op, ast.LtE):
            return bool(lhs <= rhs)
        if isinstance(op, ast.Lt):
            return bool(lhs < rhs)
        if isinstance(op, ast.Eq):
            return bool(lhs == rhs)
        if isinstance(op, ast.NotEq):
            return bool(lhs != rhs)
        return None

    # ------------------------------------------------------------------------
    # AST Statement & Overload Grouping
    # ------------------------------------------------------------------------

    def _apply_statements_to_container(
        self,
        container_id: int,
        container_qname: str,
        stmts: list[ast.stmt],
        *,
        is_class_scope: bool,
    ) -> None:
        # Group functions by name so multiple `@overload` defs for the same callable are processed together
        func_groups: dict[str, list[ast.FunctionDef | ast.AsyncFunctionDef]] = {}

        for stmt in stmts:
            if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
                func_groups.setdefault(stmt.name, []).append(stmt)
            elif isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                self._overlay_ann_assign(container_id, container_qname, stmt, is_class_scope=is_class_scope)
            elif isinstance(stmt, ast.ClassDef):
                self._overlay_class_def(container_id, container_qname, stmt)

        for func_name, defs in func_groups.items():
            self._overlay_callable_group(container_id, container_qname, func_name, defs, is_class_scope=is_class_scope)

    def _overlay_ann_assign(
        self,
        container_id: int,
        container_qname: str,
        stmt: ast.AnnAssign,
        *,
        is_class_scope: bool,
    ) -> None:
        assert isinstance(stmt.target, ast.Name)
        var_name = stmt.target.id
        type_str = ast.unparse(stmt.annotation)

        row = self.conn.execute(
            "SELECT symbol_id FROM symbols WHERE container_id = ? AND name = ? LIMIT 1",
            (container_id, var_name),
        ).fetchone()

        if row:
            sid = int(row[0])
            self.conn.execute(
                """
                UPDATE state_members
                SET declared_type_expr = ?
                WHERE symbol_id = ?
                """,
                (type_str, sid),
            )
            self.conn.execute(
                "UPDATE symbols SET provenance = 'pyi_enriched' WHERE symbol_id = ? AND provenance = 'defined_here'",
                (sid,),
            )
            self.enriched_state_members += 1
        else:
            vis, is_hid = classify_identifier_visibility(var_name)
            sym_kind = "property" if is_class_scope else ("constant" if var_name.isupper() else "variable")
            qname = f"{container_qname}.{var_name}"
            cur = self.conn.execute(
                """
                INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name,
                    symbol_kind, visibility, provenance, is_hidden, docstring
                )
                VALUES (?, ?, ?, ?, ?, ?, 'pyi_stub_only', ?, NULL)
                ON CONFLICT(container_id, name) DO NOTHING
                RETURNING symbol_id
                """,
                (container_id, container_id, var_name, qname, sym_kind, vis, is_hid),
            )
            res = cur.fetchone()
            if res:
                sid = int(res[0])
                self.conn.execute(
                    """
                    INSERT INTO state_members (
                        symbol_id, declared_type_expr, runtime_type_name,
                        is_constant, is_mutable, literal_value_repr, access_mode
                    )
                    VALUES (?, ?, '<pyi_static>', ?, ?, NULL, 'read_write')
                    """,
                    (sid, type_str, 1 if var_name.isupper() else 0, 0 if var_name.isupper() else 1),
                )
                self.stub_only_symbols += 1

    def _overlay_class_def(self, parent_cid: int, parent_qname: str, cls_node: ast.ClassDef) -> None:
        cls_qname = f"{parent_qname}.{cls_node.name}"
        row = self.conn.execute(
            "SELECT container_id FROM containers WHERE qualified_name = ? LIMIT 1",
            (cls_qname,),
        ).fetchone()
        if not row:
            return
        cls_cid = int(row[0])
        active_body = self._flatten_active_statements(cls_node.body)
        self._apply_statements_to_container(cls_cid, cls_qname, active_body, is_class_scope=True)

    def _overlay_callable_group(
        self,
        container_id: int,
        container_qname: str,
        func_name: str,
        defs: list[ast.FunctionDef | ast.AsyncFunctionDef],
        *,
        is_class_scope: bool,
    ) -> None:
        # Check if `@property` decorator is present on a single def
        if len(defs) == 1 and self._has_decorator(defs[0], "property"):
            ret_str = ast.unparse(defs[0].returns) if defs[0].returns else "Any"
            row = self.conn.execute(
                "SELECT symbol_id FROM symbols WHERE container_id = ? AND name = ? LIMIT 1",
                (container_id, func_name),
            ).fetchone()
            if row:
                self.conn.execute(
                    "UPDATE state_members SET declared_type_expr = ? WHERE symbol_id = ?",
                    (ret_str, int(row[0])),
                )
                self.enriched_state_members += 1
            return

        # Find or create the symbol & primary callable record
        row = self.conn.execute(
            "SELECT symbol_id FROM symbols WHERE container_id = ? AND name = ? LIMIT 1",
            (container_id, func_name),
        ).fetchone()

        first_def = defs[0]
        is_async = 1 if isinstance(first_def, ast.AsyncFunctionDef) else 0
        is_static = 1 if (not is_class_scope or self._has_decorator(first_def, "staticmethod")) else 0
        is_cls_bound = 1 if self._has_decorator(first_def, "classmethod") else 0

        if row:
            sid = int(row[0])
            self.conn.execute(
                "UPDATE symbols SET provenance = 'pyi_enriched' WHERE symbol_id = ? AND provenance = 'defined_here'",
                (sid,),
            )
        else:
            vis, is_hid = classify_identifier_visibility(func_name)
            sym_kind = "constructor" if func_name in ("__init__", "__new__") else ("method" if is_class_scope else "function")
            qname = f"{container_qname}.{func_name}"
            cur = self.conn.execute(
                """
                INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name,
                    symbol_kind, visibility, provenance, is_hidden, docstring
                )
                VALUES (?, ?, ?, ?, ?, ?, 'pyi_stub_only', ?, ?)
                RETURNING symbol_id
                """,
                (container_id, container_id, func_name, qname, sym_kind, vis, is_hid, ast.get_docstring(first_def)),
            )
            sid = int(cur.fetchone()[0])
            self.stub_only_symbols += 1

        # Separate `@overload` definitions from implementation/single definitions
        overload_defs = [d for d in defs if self._has_decorator(d, "overload")]
        target_defs = overload_defs if len(overload_defs) > 0 else [defs[-1]]
        is_overloaded = len(overload_defs) > 0

        # Extract the primary signature (or synthesized union return type for overloads)
        primary_sig, primary_ret, primary_tparams, primary_params = self._parse_ast_func_signature(target_defs[0])
        if is_overloaded:
            unique_rets: list[str] = []
            for d in overload_defs:
                _, r_str, _, _ = self._parse_ast_func_signature(d)
                if r_str and r_str not in unique_rets:
                    unique_rets.append(r_str)
            primary_ret = " | ".join(unique_rets) if unique_rets else primary_ret

        sig_source = "pyi_overload_overlay" if is_overloaded else "pyi_stub_overlay"

        self.conn.execute(
            """
            INSERT INTO callables (
                symbol_id, is_async, is_generator, is_static, is_class_bound,
                has_overloads, overload_count, type_params_json,
                return_type_expr, raw_signature, signature_source
            )
            VALUES (?, ?, 0, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(symbol_id) DO UPDATE SET
                has_overloads = excluded.has_overloads,
                overload_count = excluded.overload_count,
                type_params_json = COALESCE(excluded.type_params_json, callables.type_params_json),
                return_type_expr = COALESCE(excluded.return_type_expr, callables.return_type_expr),
                raw_signature = excluded.raw_signature,
                signature_source = excluded.signature_source
            """,
            (
                sid,
                is_async,
                is_static,
                is_cls_bound,
                1 if is_overloaded else 0,
                len(overload_defs),
                json.dumps(primary_tparams) if primary_tparams else None,
                primary_ret,
                primary_sig,
                sig_source,
            ),
        )

        # Replace untyped primary parameters with the rich `.pyi` primary parameters
        self.conn.execute(
            "DELETE FROM parameters WHERE callable_symbol_id = ? AND overload_id IS NULL",
            (sid,),
        )
        for p in primary_params:
            self.conn.execute(
                """
                INSERT INTO parameters (
                    callable_symbol_id, overload_id, ordinal, name, pass_kind,
                    type_expr, type_source, default_expr, is_optional
                )
                VALUES (?, NULL, ?, ?, ?, ?, 'pyi_stub', ?, ?)
                """,
                (
                    sid,
                    p["ordinal"],
                    p["name"],
                    p["pass_kind"],
                    p["type_expr"],
                    p["default_expr"],
                    p["is_optional"],
                ),
            )

        # If `@overload` variants exist, record every variant and its parameter list in `callable_overloads` + `parameters`
        if is_overloaded:
            self.conn.execute("DELETE FROM callable_overloads WHERE callable_symbol_id = ?", (sid,))
            for ov_idx, ov_def in enumerate(overload_defs):
                ov_sig, ov_ret, ov_tparams, ov_params = self._parse_ast_func_signature(ov_def)
                cur = self.conn.execute(
                    """
                    INSERT INTO callable_overloads (
                        callable_symbol_id, overload_ordinal, type_params_json,
                        return_type_expr, raw_signature
                    )
                    VALUES (?, ?, ?, ?, ?)
                    RETURNING overload_id
                    """,
                    (
                        sid,
                        ov_idx,
                        json.dumps(ov_tparams) if ov_tparams else None,
                        ov_ret,
                        ov_sig,
                    ),
                )
                ov_id = int(cur.fetchone()[0])
                self.inserted_overloads += 1

                for p in ov_params:
                    self.conn.execute(
                        """
                        INSERT INTO parameters (
                            callable_symbol_id, overload_id, ordinal, name, pass_kind,
                            type_expr, type_source, default_expr, is_optional
                        )
                        VALUES (?, ?, ?, ?, ?, ?, 'pyi_stub', ?, ?)
                        """,
                        (
                            sid,
                            ov_id,
                            p["ordinal"],
                            p["name"],
                            p["pass_kind"],
                            p["type_expr"],
                            p["default_expr"],
                            p["is_optional"],
                        ),
                    )

        self.enriched_callables += 1

    @staticmethod
    def _has_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef, dec_name: str) -> bool:
        for dec in node.decorator_list:
            unparsed = ast.unparse(dec).strip()
            if unparsed == dec_name or unparsed.endswith(f".{dec_name}"):
                return True
        return False

    @staticmethod
    def _parse_ast_func_signature(
        node: ast.FunctionDef | ast.AsyncFunctionDef,
    ) -> tuple[str, str | None, list[str], list[dict[str, Any]]]:
        """Extracts (raw_signature, return_type_expr, type_params, params_list) from an AST FunctionDef."""
        args = node.args
        params: list[dict[str, Any]] = []
        ordinal = 0

        # Positional-only + positional-or-keyword defaults align to the tail of (posonlyargs + args)
        pos_all = list(args.posonlyargs) + list(args.args)
        num_pos_defaults = len(args.defaults)
        default_start_idx = len(pos_all) - num_pos_defaults

        for idx, arg in enumerate(pos_all):
            pass_kind = "positional_only" if idx < len(args.posonlyargs) else "positional_or_keyword"
            ann_str = ast.unparse(arg.annotation) if arg.annotation else None
            def_node = args.defaults[idx - default_start_idx] if idx >= default_start_idx else None
            def_str = ast.unparse(def_node) if def_node is not None else None
            params.append({
                "ordinal": ordinal,
                "name": arg.arg,
                "pass_kind": pass_kind,
                "type_expr": ann_str,
                "default_expr": def_str,
                "is_optional": 1 if def_node is not None else 0,
            })
            ordinal += 1

        if args.vararg is not None:
            ann_str = ast.unparse(args.vararg.annotation) if args.vararg.annotation else None
            params.append({
                "ordinal": ordinal,
                "name": args.vararg.arg,
                "pass_kind": "var_positional",
                "type_expr": ann_str,
                "default_expr": None,
                "is_optional": 1,
            })
            ordinal += 1

        for kw_arg, kw_def in zip(args.kwonlyargs, args.kw_defaults):
            ann_str = ast.unparse(kw_arg.annotation) if kw_arg.annotation else None
            def_str = ast.unparse(kw_def) if kw_def is not None else None
            params.append({
                "ordinal": ordinal,
                "name": kw_arg.arg,
                "pass_kind": "keyword_only",
                "type_expr": ann_str,
                "default_expr": def_str,
                "is_optional": 1 if kw_def is not None else 0,
            })
            ordinal += 1

        if args.kwarg is not None:
            ann_str = ast.unparse(args.kwarg.annotation) if args.kwarg.annotation else None
            params.append({
                "ordinal": ordinal,
                "name": args.kwarg.arg,
                "pass_kind": "var_keyword",
                "type_expr": ann_str,
                "default_expr": None,
                "is_optional": 1,
            })
            ordinal += 1

        ret_str = ast.unparse(node.returns) if node.returns is not None else None
        raw_sig = f"({ast.unparse(args)})" + (f" -> {ret_str}" if ret_str else "")
        type_params = [ast.unparse(tp) for tp in getattr(node, "type_params", [])]
        return (raw_sig, ret_str, type_params, params)


# ============================================================================
# 5. DIAGNOSTIC REPORT & CLI ENTRYPOINT
# ============================================================================

def print_spectrum_report(conn: sqlite3.Connection, db_path: Path) -> None:
    print(f"\n======================================================================")
    print(f" PYTHON SPECTRUM + .pyi OVERLAY SUMMARY ({db_path})")
    print(f"======================================================================")

    env = conn.execute("SELECT * FROM environments LIMIT 1").fetchone()
    if env:
        print(f" Runtime   : {env[2]} {env[3]} on {env[7]} (sys.platform={env[8]!r})")

    print("\n--- 1. Callables by Signature Source (Runtime vs. Static .pyi Overlay) ---")
    sig_rows = conn.execute(
        """
        SELECT signature_source, has_overloads, COUNT(*)
        FROM callables
        GROUP BY signature_source, has_overloads
        ORDER BY COUNT(*) DESC
        """
    ).fetchall()
    for src, has_ov, cnt in sig_rows:
        print(f"  source={src:<24} | has_overloads={has_ov} : {cnt:>6,}")

    print("\n--- 2. Enriched C-Builtins & Overloaded Callables (Sample) ---")
    ov_rows = conn.execute(
        """
        SELECT s.qualified_name, c.overload_count, c.return_type_expr, c.raw_signature
        FROM callables c
        JOIN symbols s ON c.symbol_id = s.symbol_id
        WHERE c.signature_source IN ('pyi_stub_overlay', 'pyi_overload_overlay')
        ORDER BY c.overload_count DESC, s.qualified_name
        LIMIT 12
        """
    ).fetchall()
    for qname, ov_cnt, ret_t, raw_sig in ov_rows:
        sig_short = raw_sig if raw_sig and len(raw_sig) <= 68 else f"{(raw_sig or '')[:65]}..."
        print(f"  {qname:<24} [overloads={ov_cnt}] -> {str(ret_t):<32} | {sig_short}")

    print("\n--- 3. Enriched State Members (Runtime Type vs. Static .pyi Generic Type) ---")
    st_rows = conn.execute(
        """
        SELECT s.qualified_name, m.runtime_type_name, m.declared_type_expr
        FROM state_members m
        JOIN symbols s ON m.symbol_id = s.symbol_id
        WHERE m.declared_type_expr IS NOT NULL
          AND s.provenance IN ('pyi_enriched', 'pyi_stub_only')
        ORDER BY s.qualified_name
        LIMIT 12
        """
    ).fetchall()
    for qname, rt_type, decl_type in st_rows:
        print(f"  {qname:<24} | runtime={rt_type:<16} -> pyi_type={decl_type}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Clean-room Python Spectrum Harvester + Static .pyi Overlay Pass."
    )
    parser.add_argument(
        "--db",
        type=Path,
        default=Path("python_spectrum_catalog.db"),
        help="Output SQLite database path (default: ./python_spectrum_catalog.db).",
    )
    parser.add_argument(
        "--stdlib-modules",
        nargs="*",
        help="Optional subset of stdlib modules to harvest (omit to harvest all top-level stdlib + builtin + `_` modules).",
    )
    parser.add_argument(
        "--include-submodules",
        action="store_true",
        help="Also walk submodules of stdlib packages.",
    )
    parser.add_argument(
        "--third-party",
        nargs="*",
        help="Optional list of installed third-party packages to harvest.",
    )
    parser.add_argument(
        "--typeshed-dir",
        type=Path,
        default=None,
        help="Optional path to a local typeshed directory (containing stdlib/ and stubs/).",
    )
    parser.add_argument(
        "--demo-stubs",
        action="store_true",
        help="Apply the embedded mini-typeshed overlay (builtins, sys, os, json) for zero-dependency clean-room testing.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate all tables before harvesting.",
    )
    args = parser.parse_args(argv)

    conn = sqlite3.connect(str(args.db))
    cataloger = PythonSpectrumCataloger(conn)
    cataloger.init_db(reset=args.reset)
    cataloger.register_environment()

    print("[1/4] Harvesting Stratum 0: Ambient Scope (Keywords, Builtins, Site-Builtins, Implicit Dunders)...")
    cataloger.harvest_stratum_0_ambient()

    print("[2/4] Harvesting Stratum 1: Versioned Python Stdlib (Public & Hidden `_` Modules)...")
    mod_filter = set(args.stdlib_modules) if args.stdlib_modules else None
    cataloger.harvest_stratum_1_stdlib(module_filter=mod_filter, include_submodules=args.include_submodules)

    print("[3/4] Harvesting Stratum 2: Environment Third-Party Distributions...")
    tp_filter = set(args.third_party) if args.third_party is not None else set()
    cataloger.harvest_stratum_2_third_party(target_packages=tp_filter)

    print("[4/4] Running Pass 4: Static .pyi (Typeshed) AST Overlay...")
    overlay = StaticPyiOverlayCataloger(conn)
    if args.demo_stubs:
        overlay.overlay_embedded_demo_stubs()
    elif args.typeshed_dir and args.typeshed_dir.is_dir():
        overlay.overlay_from_directory(args.typeshed_dir, module_filter=mod_filter)
    else:
        discovered = overlay.auto_discover_typeshed_dirs()
        if discovered:
            print(f"      Auto-discovered installed typeshed at: {discovered[0]}")
            overlay.overlay_from_directory(discovered[0], module_filter=mod_filter)
        else:
            print("      No installed typeshed found; falling back to embedded demo stubs (--demo-stubs).")
            overlay.overlay_embedded_demo_stubs()

    print(
        f"      Overlay stats: {overlay.enriched_callables} callables enriched, "
        f"{overlay.inserted_overloads} @overloads recorded, "
        f"{overlay.enriched_state_members} state members typed, "
        f"{overlay.stub_only_symbols} static-only stub symbols added."
    )

    print_spectrum_report(conn, args.db)
    conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())