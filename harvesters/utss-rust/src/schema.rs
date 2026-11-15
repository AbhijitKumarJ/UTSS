use rusqlite::{Connection, Result};

pub const EXPECTED_TABLES: &[&str] = &[
    "environments",
    "distributions",
    "containers",
    "symbols",
    "callables",
    "callable_overloads",
    "parameters",
    "state_members",
    "symbol_aliases",
    "rust_container_facets",
    "rust_symbol_facets",
];

pub const SCHEMA_SQL: &str = r#"
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

-- 1. Environments: Tracks exact language runtime versions & platforms
CREATE TABLE IF NOT EXISTS environments (
    env_id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,                 -- 'rust', 'csharp', 'python', 'typescript'
    runtime_name TEXT NOT NULL,             -- 'rustc', 'LLVM'
    language_version TEXT NOT NULL,         -- e.g. '1.85.0'
    version_major INTEGER NOT NULL,
    version_minor INTEGER NOT NULL,
    version_micro INTEGER NOT NULL,
    platform_triplet TEXT NOT NULL,         -- e.g. 'x86_64-unknown-linux-gnu'
    sys_platform TEXT NOT NULL,             -- e.g. 'linux', 'windows', 'macos'
    executable_path TEXT NOT NULL,
    captured_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(language, runtime_name, language_version, platform_triplet, executable_path)
);

-- 2. Distributions: Logical deliverable units (Ambient, Stdlib/Core, Crates.io packages, Workspace)
CREATE TABLE IF NOT EXISTS distributions (
    dist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    env_id INTEGER NOT NULL REFERENCES environments(env_id) ON DELETE CASCADE,
    stratum INTEGER NOT NULL,               -- 0 = Ambient, 1 = Stdlib (std/core/alloc), 2 = Crates.io, 3 = Workspace
    dist_name TEXT NOT NULL,                -- '<ambient>', 'std', 'core', 'alloc', 'serde', '<workspace>'
    dist_version TEXT NOT NULL,             -- Rust version for 0/1, crate version for 2/3
    summary TEXT,
    UNIQUE(env_id, stratum, dist_name, dist_version)
);

-- 3. Containers: Universal hierarchy (ambient_scope, crate, module, struct, enum, trait, union)
CREATE TABLE IF NOT EXISTS containers (
    container_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dist_id INTEGER NOT NULL REFERENCES distributions(dist_id) ON DELETE CASCADE,
    parent_container_id INTEGER REFERENCES containers(container_id) ON DELETE CASCADE,
    container_kind TEXT NOT NULL,           -- 'ambient_scope', 'crate', 'module', 'struct', 'enum', 'trait', 'union'
    qualified_name TEXT NOT NULL,           -- '<ambient>', 'std::collections', 'std::collections::HashMap'
    short_name TEXT NOT NULL,
    requires_import INTEGER NOT NULL DEFAULT 1, -- 0 for Stratum 0 ambient containers, 1 otherwise
    visibility TEXT NOT NULL,               -- 'public', 'pub_crate', 'pub_super', 'private'
    is_hidden INTEGER NOT NULL DEFAULT 0,
    physical_path TEXT,
    stub_path TEXT,
    sha256_hash TEXT,
    start_line INTEGER,
    start_col INTEGER,
    end_line INTEGER,
    end_col INTEGER,
    docstring TEXT,
    UNIQUE(dist_id, qualified_name)
);

-- 4. Symbols: Master directory of functions, methods, fields, variants, constants, keywords, macros
CREATE TABLE IF NOT EXISTS symbols (
    symbol_id INTEGER PRIMARY KEY AUTOINCREMENT,
    container_id INTEGER NOT NULL REFERENCES containers(container_id) ON DELETE CASCADE,
    origin_container_id INTEGER REFERENCES containers(container_id),
    name TEXT NOT NULL,
    qualified_name TEXT NOT NULL,
    symbol_kind TEXT NOT NULL,              -- 'keyword', 'type_alias', 'function', 'method', 'associated_fn',
                                            -- 'struct_field', 'enum_variant', 'constant', 'static_var', 'macro'
    visibility TEXT NOT NULL,               -- 'public', 'pub_crate', 'pub_super', 'private'
    provenance TEXT NOT NULL,               -- 'ambient_keyword', 'ambient_prelude', 'std_item', 'crate_item', 'ast_defined'
    is_hidden INTEGER NOT NULL DEFAULT 0,
    start_line INTEGER,
    start_col INTEGER,
    end_line INTEGER,
    end_col INTEGER,
    docstring TEXT,
    UNIQUE(container_id, name)
);

-- 5. Callables: Universal primary signature & execution modifiers for functions and methods
CREATE TABLE IF NOT EXISTS callables (
    symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
    is_async INTEGER NOT NULL DEFAULT 0,
    is_generator INTEGER NOT NULL DEFAULT 0,
    is_static INTEGER NOT NULL DEFAULT 0,
    is_class_bound INTEGER NOT NULL DEFAULT 0,
    has_overloads INTEGER NOT NULL DEFAULT 0,
    overload_count INTEGER NOT NULL DEFAULT 0,
    type_params_json TEXT,                  -- Generic parameters e.g. '["T", "const N: usize"]'
    return_type_expr TEXT,
    raw_signature TEXT,
    signature_source TEXT NOT NULL          -- 'rust_std_metadata', 'syn_ast', 'ambient'
);

-- 6. Callable Overloads: Trait implementation variants or macro arms
CREATE TABLE IF NOT EXISTS callable_overloads (
    overload_id INTEGER PRIMARY KEY AUTOINCREMENT,
    callable_symbol_id INTEGER NOT NULL REFERENCES callables(symbol_id) ON DELETE CASCADE,
    overload_ordinal INTEGER NOT NULL,
    type_params_json TEXT,
    return_type_expr TEXT,
    raw_signature TEXT NOT NULL,
    UNIQUE(callable_symbol_id, overload_ordinal)
);

-- 7. Parameters: Ordered parameter list for callables
CREATE TABLE IF NOT EXISTS parameters (
    param_id INTEGER PRIMARY KEY AUTOINCREMENT,
    callable_symbol_id INTEGER NOT NULL REFERENCES callables(symbol_id) ON DELETE CASCADE,
    overload_id INTEGER REFERENCES callable_overloads(overload_id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    name TEXT NOT NULL,
    pass_kind TEXT NOT NULL,                -- 'val', 'ref', 'mut_ref', 'self_val', 'self_ref', 'self_mut_ref'
    type_expr TEXT,
    type_source TEXT,                       -- 'syn_ast', 'rust_std_metadata'
    default_expr TEXT,
    is_optional INTEGER NOT NULL DEFAULT 0
);

-- 8. State Members: Struct fields, constants, statics, and enum unit variants
CREATE TABLE IF NOT EXISTS state_members (
    symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
    declared_type_expr TEXT,
    runtime_type_name TEXT NOT NULL,
    is_constant INTEGER NOT NULL DEFAULT 0,
    is_mutable INTEGER NOT NULL DEFAULT 0,
    literal_value_repr TEXT,
    access_mode TEXT NOT NULL DEFAULT 'read_write' -- 'read_only', 'read_write'
);

-- 9. Symbol Aliases: Re-exports (`pub use a::b;`) and aliases (`use a as b;`)
CREATE TABLE IF NOT EXISTS symbol_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_container_id INTEGER NOT NULL REFERENCES containers(container_id) ON DELETE CASCADE,
    exposed_name TEXT NOT NULL,
    target_module_name TEXT NOT NULL,
    target_symbol_name TEXT NOT NULL,
    alias_kind TEXT NOT NULL,               -- 'use_alias', 'pub_use_reexport', 'prelude_import'
    is_in_dunder_all INTEGER NOT NULL DEFAULT 0,
    UNIQUE(source_container_id, exposed_name)
);

-- ============================================================================
-- RUST-SPECIFIC FIDELITY FACET TABLES (1:1 WITH CORE TABLES)
-- ============================================================================

-- 10. Rust Container Facets: Generics, traits, attributes
CREATE TABLE IF NOT EXISTS rust_container_facets (
    container_id INTEGER PRIMARY KEY REFERENCES containers(container_id) ON DELETE CASCADE,
    item_kind TEXT NOT NULL,                -- 'struct', 'enum', 'trait', 'union', 'module', 'crate'
    is_pub INTEGER NOT NULL DEFAULT 0,
    is_pub_crate INTEGER NOT NULL DEFAULT 0,
    is_unsafe INTEGER NOT NULL DEFAULT 0,
    is_auto_trait INTEGER NOT NULL DEFAULT 0,
    generics_json TEXT,                     -- e.g. '[{"name": "T", "bounds": ["Clone", "Send"]}]'
    where_clause_json TEXT,                 -- e.g. '["T: Display"]'
    attributes_json TEXT                    -- e.g. '["derive(Debug, Clone)"]'
);

-- 11. Rust Symbol Facets: Function qualifiers, self kinds, visibilities
CREATE TABLE IF NOT EXISTS rust_symbol_facets (
    symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
    member_kind TEXT NOT NULL,              -- 'fn', 'method', 'associated_fn', 'const', 'static', 'variant', 'field', 'macro', 'type_alias'
    is_const INTEGER NOT NULL DEFAULT 0,
    is_async INTEGER NOT NULL DEFAULT 0,
    is_unsafe INTEGER NOT NULL DEFAULT 0,
    is_extern INTEGER NOT NULL DEFAULT 0,
    abi TEXT,                               -- 'Rust', 'C', 'system'
    self_kind TEXT NOT NULL DEFAULT 'none', -- 'none', 'val', 'ref', 'mut_ref'
    visibility TEXT NOT NULL DEFAULT 'private', -- 'pub', 'pub_crate', 'pub_super', 'private'
    attributes_json TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_rust_containers_qname ON containers(qualified_name);
CREATE INDEX IF NOT EXISTS idx_rust_containers_kind ON containers(container_kind, is_hidden);
CREATE INDEX IF NOT EXISTS idx_rust_symbols_qname ON symbols(qualified_name);
CREATE INDEX IF NOT EXISTS idx_rust_symbols_kind_vis ON symbols(symbol_kind, visibility);
CREATE INDEX IF NOT EXISTS idx_rust_symbols_container_name ON symbols(container_id, name);
CREATE INDEX IF NOT EXISTS idx_rust_aliases_target ON symbol_aliases(target_module_name, target_symbol_name);
CREATE INDEX IF NOT EXISTS idx_rust_params_callable ON parameters(callable_symbol_id, overload_id, ordinal);
CREATE INDEX IF NOT EXISTS idx_rust_overloads_callable ON callable_overloads(callable_symbol_id, overload_ordinal);
CREATE INDEX IF NOT EXISTS idx_rust_container_facets_item ON rust_container_facets(item_kind);
CREATE INDEX IF NOT EXISTS idx_rust_symbol_facets_member ON rust_symbol_facets(member_kind);
"#;

pub fn init_db(conn: &Connection, reset: bool) -> Result<()> {
    conn.execute_batch("PRAGMA foreign_keys = ON;")?;

    if reset {
        let drop_order = [
            "rust_symbol_facets",
            "rust_container_facets",
            "symbol_aliases",
            "state_members",
            "parameters",
            "callable_overloads",
            "callables",
            "symbols",
            "containers",
            "distributions",
            "environments",
        ];
        for tbl in drop_order {
            conn.execute(&format!("DROP TABLE IF EXISTS {};", tbl), [])?;
        }
    }

    conn.execute_batch(SCHEMA_SQL)?;
    Ok(())
}
