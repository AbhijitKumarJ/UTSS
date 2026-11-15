import { DatabaseSync } from "node:sqlite";

export const EXPECTED_TABLES = [
  "environments",
  "distributions",
  "containers",
  "symbols",
  "callables",
  "callable_overloads",
  "parameters",
  "state_members",
  "symbol_aliases",
  "ts_container_facets",
  "ts_symbol_facets",
] as const;

export const SCHEMA_SQL = `
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

-- 1. Environments: Host platform, runtime, language version
CREATE TABLE IF NOT EXISTS environments (
    env_id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,
    runtime_name TEXT NOT NULL,
    language_version TEXT NOT NULL,
    version_major INTEGER NOT NULL,
    version_minor INTEGER NOT NULL,
    version_micro INTEGER NOT NULL,
    platform_triplet TEXT NOT NULL,
    sys_platform TEXT NOT NULL,
    executable_path TEXT NOT NULL,
    captured_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(language, runtime_name, language_version, platform_triplet, executable_path)
);

-- 2. Distributions: Packaging and strata units
CREATE TABLE IF NOT EXISTS distributions (
    dist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    env_id INTEGER NOT NULL REFERENCES environments(env_id) ON DELETE CASCADE,
    stratum INTEGER NOT NULL,
    dist_name TEXT NOT NULL,
    dist_version TEXT NOT NULL,
    summary TEXT,
    UNIQUE(env_id, stratum, dist_name, dist_version)
);

-- 3. Containers: Logical and physical code structures
CREATE TABLE IF NOT EXISTS containers (
    container_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dist_id INTEGER NOT NULL REFERENCES distributions(dist_id) ON DELETE CASCADE,
    parent_container_id INTEGER REFERENCES containers(container_id) ON DELETE CASCADE,
    container_kind TEXT NOT NULL,
    qualified_name TEXT NOT NULL,
    short_name TEXT NOT NULL,
    requires_import INTEGER NOT NULL DEFAULT 1,
    visibility TEXT NOT NULL,
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

-- 4. Symbols: Member directory
CREATE TABLE IF NOT EXISTS symbols (
    symbol_id INTEGER PRIMARY KEY AUTOINCREMENT,
    container_id INTEGER NOT NULL REFERENCES containers(container_id) ON DELETE CASCADE,
    origin_container_id INTEGER REFERENCES containers(container_id),
    name TEXT NOT NULL,
    qualified_name TEXT NOT NULL,
    symbol_kind TEXT NOT NULL,
    visibility TEXT NOT NULL,
    provenance TEXT NOT NULL,
    is_hidden INTEGER NOT NULL DEFAULT 0,
    start_line INTEGER,
    start_col INTEGER,
    end_line INTEGER,
    end_col INTEGER,
    docstring TEXT,
    UNIQUE(container_id, name)
);

-- 5. Callables: Primary invocation signatures
CREATE TABLE IF NOT EXISTS callables (
    symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
    is_async INTEGER NOT NULL DEFAULT 0,
    is_generator INTEGER NOT NULL DEFAULT 0,
    is_static INTEGER NOT NULL DEFAULT 0,
    is_class_bound INTEGER NOT NULL DEFAULT 0,
    has_overloads INTEGER NOT NULL DEFAULT 0,
    overload_count INTEGER NOT NULL DEFAULT 0,
    type_params_json TEXT,
    return_type_expr TEXT,
    raw_signature TEXT,
    signature_source TEXT NOT NULL
);

-- 6. Callable Overloads: Function/method overload signatures
CREATE TABLE IF NOT EXISTS callable_overloads (
    overload_id INTEGER PRIMARY KEY AUTOINCREMENT,
    callable_symbol_id INTEGER NOT NULL REFERENCES callables(symbol_id) ON DELETE CASCADE,
    overload_ordinal INTEGER NOT NULL,
    type_params_json TEXT,
    return_type_expr TEXT,
    raw_signature TEXT NOT NULL,
    UNIQUE(callable_symbol_id, overload_ordinal)
);

-- 7. Parameters: Ordered parameter metadata
CREATE TABLE IF NOT EXISTS parameters (
    param_id INTEGER PRIMARY KEY AUTOINCREMENT,
    callable_symbol_id INTEGER NOT NULL REFERENCES callables(symbol_id) ON DELETE CASCADE,
    overload_id INTEGER REFERENCES callable_overloads(overload_id) ON DELETE CASCADE,
    ordinal INTEGER NOT NULL,
    name TEXT NOT NULL,
    pass_kind TEXT NOT NULL,
    type_expr TEXT,
    type_source TEXT,
    default_expr TEXT,
    is_optional INTEGER NOT NULL DEFAULT 0
);

-- 8. State Members: Fields, properties, constants, variables
CREATE TABLE IF NOT EXISTS state_members (
    symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
    declared_type_expr TEXT,
    runtime_type_name TEXT NOT NULL,
    is_constant INTEGER NOT NULL DEFAULT 0,
    is_mutable INTEGER NOT NULL DEFAULT 0,
    literal_value_repr TEXT,
    access_mode TEXT NOT NULL DEFAULT 'read_write'
);

-- 9. Symbol Aliases: Re-exports and aliases
CREATE TABLE IF NOT EXISTS symbol_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_container_id INTEGER NOT NULL REFERENCES containers(container_id) ON DELETE CASCADE,
    exposed_name TEXT NOT NULL,
    target_module_name TEXT NOT NULL,
    target_symbol_name TEXT NOT NULL,
    alias_kind TEXT NOT NULL,
    is_in_dunder_all INTEGER NOT NULL DEFAULT 0,
    UNIQUE(source_container_id, exposed_name)
);

-- 10. TypeScript Container Facets: TS language-specific container details
CREATE TABLE IF NOT EXISTS ts_container_facets (
    container_id INTEGER PRIMARY KEY REFERENCES containers(container_id) ON DELETE CASCADE,
    item_kind TEXT NOT NULL,
    is_export INTEGER NOT NULL DEFAULT 0,
    is_default_export INTEGER NOT NULL DEFAULT 0,
    is_ambient INTEGER NOT NULL DEFAULT 0,
    is_abstract INTEGER NOT NULL DEFAULT 0,
    type_params_json TEXT,
    heritage_clauses_json TEXT,
    modifiers_json TEXT
);

-- 11. TypeScript Symbol Facets: TS language-specific symbol details
CREATE TABLE IF NOT EXISTS ts_symbol_facets (
    symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
    member_kind TEXT NOT NULL,
    access_modifier TEXT NOT NULL DEFAULT 'public',
    is_readonly INTEGER NOT NULL DEFAULT 0,
    is_optional INTEGER NOT NULL DEFAULT 0,
    is_abstract INTEGER NOT NULL DEFAULT 0,
    is_override INTEGER NOT NULL DEFAULT 0,
    is_declare INTEGER NOT NULL DEFAULT 0,
    type_annotation_json TEXT,
    modifiers_json TEXT
);

-- Indices for performance
CREATE INDEX IF NOT EXISTS idx_containers_dist ON containers(dist_id);
CREATE INDEX IF NOT EXISTS idx_containers_parent ON containers(parent_container_id);
CREATE INDEX IF NOT EXISTS idx_symbols_container ON symbols(container_id);
CREATE INDEX IF NOT EXISTS idx_symbols_kind ON symbols(symbol_kind);
CREATE INDEX IF NOT EXISTS idx_parameters_callable ON parameters(callable_symbol_id);
CREATE INDEX IF NOT EXISTS idx_aliases_source ON symbol_aliases(source_container_id);
`;

export function initSchema(db: DatabaseSync): void {
  db.exec(SCHEMA_SQL);
}

export function resetSchema(db: DatabaseSync): void {
  for (const table of [...EXPECTED_TABLES].reverse()) {
    db.exec(`DROP TABLE IF EXISTS ${table};`);
  }
  initSchema(db);
}
