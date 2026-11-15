"""
Dual-Layer SQLite Database Schema for UTSS.
Layer 1: Universal Language-Agnostic Core Tables (1 to 9).
Layer 2: Python-Fidelity Facet Tables (10 to 11).
Includes Phase 2 Static .pyi Overlay & Polymorphic @overload extensions.
"""

from __future__ import annotations

import sqlite3

EXPECTED_TABLES: frozenset[str] = frozenset({
    "environments",
    "distributions",
    "containers",
    "symbols",
    "callables",
    "callable_overloads",
    "parameters",
    "state_members",
    "symbol_aliases",
    "py_container_facets",
    "py_symbol_facets",
})

SCHEMA_SQL = """
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

-- 1. Environments: Tracks exact language runtime versions & platforms
CREATE TABLE IF NOT EXISTS environments (
    env_id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,                 -- 'python', 'rust', 'csharp', 'typescript'
    runtime_name TEXT NOT NULL,             -- 'CPython', 'PyPy', 'rustc', '.NET'
    language_version TEXT NOT NULL,         -- e.g. '3.13.1'
    version_major INTEGER NOT NULL,
    version_minor INTEGER NOT NULL,
    version_micro INTEGER NOT NULL,
    platform_triplet TEXT NOT NULL,         -- e.g. 'Linux-x86_64'
    sys_platform TEXT NOT NULL,             -- e.g. 'linux', 'darwin', 'win32'
    executable_path TEXT NOT NULL,
    captured_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(language, runtime_name, language_version, platform_triplet, executable_path)
);

-- 2. Distributions: Logical deliverable units (Ambient, Stdlib, 3rd-party packages, or Workspace)
CREATE TABLE IF NOT EXISTS distributions (
    dist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    env_id INTEGER NOT NULL REFERENCES environments(env_id) ON DELETE CASCADE,
    stratum INTEGER NOT NULL,               -- 0 = Ambient, 1 = Stdlib, 2 = Third-Party, 3 = Workspace
    dist_name TEXT NOT NULL,                -- '<ambient>', 'python-stdlib', 'numpy', '<workspace>'
    dist_version TEXT NOT NULL,             -- Python version for 0/1, package version for 2/3
    summary TEXT,
    UNIQUE(env_id, stratum, dist_name, dist_version)
);

-- 3. Containers: Universal hierarchy (ambient_scope, package, module, class, exception_class)
CREATE TABLE IF NOT EXISTS containers (
    container_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dist_id INTEGER NOT NULL REFERENCES distributions(dist_id) ON DELETE CASCADE,
    parent_container_id INTEGER REFERENCES containers(container_id) ON DELETE CASCADE,
    container_kind TEXT NOT NULL,           -- 'ambient_scope', 'package', 'module', 'class', 'exception_class'
    qualified_name TEXT NOT NULL,           -- '<ambient>', 'os', 'os.path', 'builtins.int', 'json.JSONDecoder'
    short_name TEXT NOT NULL,
    requires_import INTEGER NOT NULL DEFAULT 1, -- 0 for Stratum 0 ambient containers, 1 otherwise
    visibility TEXT NOT NULL,               -- 'public', 'hidden_internal', 'system_dunder'
    is_hidden INTEGER NOT NULL DEFAULT 0,   -- 1 if leading '_' (non-dunder)
    physical_path TEXT,
    stub_path TEXT,                         -- Path to overlaid .pyi stub file if enriched
    sha256_hash TEXT,
    start_line INTEGER,
    start_col INTEGER,
    end_line INTEGER,
    end_col INTEGER,
    docstring TEXT,
    UNIQUE(dist_id, qualified_name)
);

-- 4. Symbols: Master language-agnostic directory of every callable, variable, constant, property, or keyword
CREATE TABLE IF NOT EXISTS symbols (
    symbol_id INTEGER PRIMARY KEY AUTOINCREMENT,
    container_id INTEGER NOT NULL REFERENCES containers(container_id) ON DELETE CASCADE,
    origin_container_id INTEGER REFERENCES containers(container_id), -- Where symbol was originally defined
    name TEXT NOT NULL,
    qualified_name TEXT NOT NULL,
    symbol_kind TEXT NOT NULL,              -- 'keyword', 'soft_keyword', 'function', 'method', 'constructor',
                                            -- 'class', 'exception', 'constant', 'variable', 'property', 'descriptor', 'type_alias'
    visibility TEXT NOT NULL,               -- 'exported_all', 'public_implicit', 'hidden_internal',
                                            -- 'private_mangled', 'system_dunder'
    provenance TEXT NOT NULL,               -- 'defined_here', 're_exported', 'site_injected',
                                            -- 'implicit_dunder', 'pyi_stub_only', 'pyi_enriched',
                                            -- 'ast_defined', 'ast_init_attribute', 'ast_type_checking_only', 'ast_main_guard'
    is_hidden INTEGER NOT NULL DEFAULT 0,
    start_line INTEGER,
    start_col INTEGER,
    end_line INTEGER,
    end_col INTEGER,
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
    signature_source TEXT NOT NULL          -- 'inspect_signature', 'text_signature', 'ast', 'docstring_first_line',
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

-- 7. Parameters: Ordered parameter list for primary callables and @overload variants
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
    access_mode TEXT NOT NULL DEFAULT 'read_write' -- 'read_only', 'read_write', 'read_write_delete'
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

-- 10. Python Container Facets: Module origin kind, __all__, PEP 562 __getattr__, Class MRO
CREATE TABLE IF NOT EXISTS py_container_facets (
    container_id INTEGER PRIMARY KEY REFERENCES containers(container_id) ON DELETE CASCADE,
    module_origin_kind TEXT,                -- 'ambient', 'builtin_c', 'frozen', 'pure_python', 'c_extension', 'namespace_pkg', 'class_body', 'workspace_ast'
    has_dunder_all INTEGER NOT NULL DEFAULT 0,
    dunder_all_json TEXT,
    has_lazy_getattr INTEGER NOT NULL DEFAULT 0,
    base_classes_json TEXT,
    mro_json TEXT,
    metaclass_name TEXT
);

-- 11. Python Symbol Facets: C-slot wrappers, descriptors, code object flags, dunder category
CREATE TABLE IF NOT EXISTS py_symbol_facets (
    symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
    py_runtime_type TEXT NOT NULL,          -- e.g. 'builtin_function_or_method', 'function', 'method_descriptor', 'getset_descriptor'
    descriptor_kind TEXT,                   -- 'property', 'classmethod', 'staticmethod', 'getset_descriptor', 'member_descriptor', 'slot_wrapper'
    is_c_implemented INTEGER NOT NULL DEFAULT 0,
    co_flags INTEGER,
    dunder_category TEXT                    -- 'lifecycle', 'comparison', 'numeric', 'container', 'context_manager', 'async', 'attribute_access', 'meta'
);

-- Indexes for high-performance symbol table querying
CREATE INDEX IF NOT EXISTS idx_containers_qname ON containers(qualified_name);
CREATE INDEX IF NOT EXISTS idx_containers_kind ON containers(container_kind, is_hidden);
CREATE INDEX IF NOT EXISTS idx_symbols_qname ON symbols(qualified_name);
CREATE INDEX IF NOT EXISTS idx_symbols_kind_vis ON symbols(symbol_kind, visibility);
CREATE INDEX IF NOT EXISTS idx_symbols_container_name ON symbols(container_id, name);
CREATE INDEX IF NOT EXISTS idx_aliases_target ON symbol_aliases(target_module_name, target_symbol_name);
CREATE INDEX IF NOT EXISTS idx_params_callable ON parameters(callable_symbol_id, overload_id, ordinal);
CREATE INDEX IF NOT EXISTS idx_overloads_callable ON callable_overloads(callable_symbol_id, overload_ordinal);
"""


def init_db(conn: sqlite3.Connection, reset: bool = False) -> None:
    """Initializes the database schema. If reset is True, drops all existing tables."""
    conn.execute("PRAGMA foreign_keys = ON;")
    if reset:
        drop_tables_order = (
            "py_symbol_facets",
            "py_container_facets",
            "symbol_aliases",
            "state_members",
            "parameters",
            "callable_overloads",
            "callables",
            "symbols",
            "containers",
            "distributions",
            "environments",
        )
        for tbl in drop_tables_order:
            conn.execute(f"DROP TABLE IF EXISTS {tbl};")
    conn.executescript(SCHEMA_SQL)
    conn.commit()
