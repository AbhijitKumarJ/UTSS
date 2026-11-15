-- ============================================================================
-- UTSS 11-TABLE RELATIONAL CATALOG SCHEMA: C/C++
-- Database Source: harvesters/utss-cpp/catalog_cpp_full.db
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
    language TEXT NOT NULL,                 -- 'cpp'
    runtime_name TEXT NOT NULL,             -- 'g++', 'clang++', 'MSVC'
    language_version TEXT NOT NULL,         -- 'C++20'
    version_major INTEGER NOT NULL,
    version_minor INTEGER NOT NULL,
    version_micro INTEGER NOT NULL,
    platform_triplet TEXT NOT NULL,         -- 'x86_64-linux-gnu'
    sys_platform TEXT NOT NULL,             -- 'linux'
    executable_path TEXT NOT NULL,
    captured_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(language, runtime_name, language_version, platform_triplet, executable_path)
);

-- Table: distributions
CREATE TABLE distributions (
    dist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    env_id INTEGER NOT NULL REFERENCES environments(env_id) ON DELETE CASCADE,
    stratum INTEGER NOT NULL,               -- 0 = Ambient, 1 = Stdlib, 3 = Workspace
    dist_name TEXT NOT NULL,                -- '<ambient>', 'libstdc++', 'commerce_engine'
    dist_version TEXT NOT NULL,             -- Compiler version for 0/1, workspace version for 3
    summary TEXT,
    UNIQUE(env_id, stratum, dist_name, dist_version)
);

-- Table: containers
CREATE TABLE containers (
    container_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dist_id INTEGER NOT NULL REFERENCES distributions(dist_id) ON DELETE CASCADE,
    parent_container_id INTEGER REFERENCES containers(container_id) ON DELETE CASCADE,
    container_kind TEXT NOT NULL,           -- 'ambient_scope', 'namespace', 'class', 'struct', 'union', 'enum'
    qualified_name TEXT NOT NULL,           -- '<ambient>', 'std', 'commerce::Order'
    short_name TEXT NOT NULL,
    requires_import INTEGER NOT NULL DEFAULT 1,
    visibility TEXT NOT NULL,               -- 'public', 'protected', 'private'
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
    symbol_kind TEXT NOT NULL,              -- 'keyword', 'primitive_type', 'function', 'method',
                                            -- 'constructor', 'destructor', 'operator', 'field',
                                            -- 'enum_member', 'type_alias', 'constant', 'macro'
    visibility TEXT NOT NULL,               -- 'public', 'protected', 'private'
    provenance TEXT NOT NULL,               -- 'ambient_keyword', 'ambient_builtin', 'std_item', 'ast_defined'
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
    type_params_json TEXT,                  -- Template parameters e.g. '["typename T", "size_t N"]'
    return_type_expr TEXT,
    raw_signature TEXT,
    signature_source TEXT NOT NULL          -- 'cpp_std_metadata', 'cpp_ast', 'ambient'
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
    pass_kind TEXT NOT NULL,                -- 'val', 'ref', 'const_ref', 'rvalue_ref', 'pointer', 'const_pointer'
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
    alias_kind TEXT NOT NULL,               -- 'using_decl', 'type_alias', 'include_header'
    is_in_dunder_all INTEGER NOT NULL DEFAULT 0,
    UNIQUE(source_container_id, exposed_name)
);

-- ============================================================================
-- LAYER 2: C/C++ FIDELITY FACET TABLES (10-11)
-- ============================================================================
-- Table: cpp_container_facets
CREATE TABLE cpp_container_facets (
    container_id INTEGER PRIMARY KEY REFERENCES containers(container_id) ON DELETE CASCADE,
    item_kind TEXT NOT NULL,                -- 'namespace', 'class', 'struct', 'enum', 'enum_class', 'union', 'concept'
    is_template INTEGER NOT NULL DEFAULT 0,
    template_params_json TEXT,
    base_classes_json TEXT,                 -- e.g. '["public IOrderService"]'
    is_final INTEGER NOT NULL DEFAULT 0,
    is_abstract INTEGER NOT NULL DEFAULT 0,
    attributes_json TEXT
);

-- Table: cpp_symbol_facets
CREATE TABLE cpp_symbol_facets (
    symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
    member_kind TEXT NOT NULL,              -- 'function', 'method', 'constructor', 'destructor', 'operator', 'field', 'enum_constant', 'type_alias', 'macro'
    access_specifier TEXT NOT NULL DEFAULT 'public', -- 'public', 'protected', 'private'
    is_virtual INTEGER NOT NULL DEFAULT 0,
    is_pure_virtual INTEGER NOT NULL DEFAULT 0,
    is_override INTEGER NOT NULL DEFAULT 0,
    is_const INTEGER NOT NULL DEFAULT 0,
    is_noexcept INTEGER NOT NULL DEFAULT 0,
    is_constexpr INTEGER NOT NULL DEFAULT 0,
    is_inline INTEGER NOT NULL DEFAULT 0,
    is_static INTEGER NOT NULL DEFAULT 0,
    pass_by TEXT,                           -- 'val', 'ref', 'const_ref', 'rvalue_ref', 'pointer'
    attributes_json TEXT
);

-- ============================================================================
-- PERFORMANCE INDICES
-- ============================================================================
CREATE INDEX idx_cpp_containers_dist ON containers(dist_id);
CREATE INDEX idx_cpp_parameters_callable ON parameters(callable_symbol_id);
CREATE INDEX idx_cpp_symbols_container ON symbols(container_id);
CREATE INDEX idx_cpp_symbols_kind ON symbols(symbol_kind);
