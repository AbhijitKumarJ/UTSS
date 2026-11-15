-- ============================================================================
-- UTSS 11-TABLE RELATIONAL CATALOG SCHEMA: TYPESCRIPT
-- Database Source: harvesters/utss-typescript/catalog_ts_full.db
-- ============================================================================
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

-- ============================================================================
-- LAYER 1: UNIVERSAL CORE TABLES (1-9)
-- ============================================================================
-- Table: environments
CREATE TABLE environments (
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

-- Table: distributions
CREATE TABLE distributions (
    dist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    env_id INTEGER NOT NULL REFERENCES environments(env_id) ON DELETE CASCADE,
    stratum INTEGER NOT NULL,
    dist_name TEXT NOT NULL,
    dist_version TEXT NOT NULL,
    summary TEXT,
    UNIQUE(env_id, stratum, dist_name, dist_version)
);

-- Table: containers
CREATE TABLE containers (
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

-- Table: symbols
CREATE TABLE symbols (
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

-- Table: callables
CREATE TABLE callables (
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

-- Table: callable_overloads
CREATE TABLE callable_overloads (
    overload_id INTEGER PRIMARY KEY AUTOINCREMENT,
    callable_symbol_id INTEGER NOT NULL REFERENCES callables(symbol_id) ON DELETE CASCADE,
    overload_ordinal INTEGER NOT NULL,
    type_params_json TEXT,
    return_type_expr TEXT,
    raw_signature TEXT NOT NULL,
    UNIQUE(callable_symbol_id, overload_ordinal)
);

-- Table: parameters
CREATE TABLE parameters (
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

-- Table: state_members
CREATE TABLE state_members (
    symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
    declared_type_expr TEXT,
    runtime_type_name TEXT NOT NULL,
    is_constant INTEGER NOT NULL DEFAULT 0,
    is_mutable INTEGER NOT NULL DEFAULT 0,
    literal_value_repr TEXT,
    access_mode TEXT NOT NULL DEFAULT 'read_write'
);

-- Table: symbol_aliases
CREATE TABLE symbol_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_container_id INTEGER NOT NULL REFERENCES containers(container_id) ON DELETE CASCADE,
    exposed_name TEXT NOT NULL,
    target_module_name TEXT NOT NULL,
    target_symbol_name TEXT NOT NULL,
    alias_kind TEXT NOT NULL,
    is_in_dunder_all INTEGER NOT NULL DEFAULT 0,
    UNIQUE(source_container_id, exposed_name)
);

-- ============================================================================
-- LAYER 2: TYPESCRIPT FIDELITY FACET TABLES (10-11)
-- ============================================================================
-- Table: ts_container_facets
CREATE TABLE ts_container_facets (
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

-- Table: ts_symbol_facets
CREATE TABLE ts_symbol_facets (
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

-- ============================================================================
-- PERFORMANCE INDICES
-- ============================================================================
CREATE INDEX idx_aliases_source ON symbol_aliases(source_container_id);
CREATE INDEX idx_containers_dist ON containers(dist_id);
CREATE INDEX idx_containers_parent ON containers(parent_container_id);
CREATE INDEX idx_parameters_callable ON parameters(callable_symbol_id);
CREATE INDEX idx_symbols_container ON symbols(container_id);
CREATE INDEX idx_symbols_kind ON symbols(symbol_kind);
