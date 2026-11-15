-- ============================================================================
-- UTSS 11-TABLE RELATIONAL CATALOG SCHEMA: C# .NET
-- Database Source: harvesters/utss-csharp/catalog_cs_full.db
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
    language TEXT NOT NULL,                 -- 'csharp', 'python', 'rust', 'typescript'
    runtime_name TEXT NOT NULL,             -- '.NET', 'CoreCLR', 'Mono'
    language_version TEXT NOT NULL,         -- e.g. '13.0' or '10.0'
    version_major INTEGER NOT NULL,
    version_minor INTEGER NOT NULL,
    version_micro INTEGER NOT NULL,
    platform_triplet TEXT NOT NULL,         -- e.g. 'Linux-x86_64'
    sys_platform TEXT NOT NULL,             -- e.g. 'linux', 'win32', 'darwin'
    executable_path TEXT NOT NULL,
    captured_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(language, runtime_name, language_version, platform_triplet, executable_path)
);

-- Table: distributions
CREATE TABLE distributions (
    dist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    env_id INTEGER NOT NULL REFERENCES environments(env_id) ON DELETE CASCADE,
    stratum INTEGER NOT NULL,               -- 0 = Ambient, 1 = BCL/Runtime, 2 = NuGet/Ecosystem, 3 = Workspace
    dist_name TEXT NOT NULL,                -- '<ambient>', 'System.Runtime', 'Newtonsoft.Json', '<workspace>'
    dist_version TEXT NOT NULL,             -- .NET version for 0/1, assembly/package version for 2/3
    summary TEXT,
    UNIQUE(env_id, stratum, dist_name, dist_version)
);

-- Table: containers
CREATE TABLE containers (
    container_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dist_id INTEGER NOT NULL REFERENCES distributions(dist_id) ON DELETE CASCADE,
    parent_container_id INTEGER REFERENCES containers(container_id) ON DELETE CASCADE,
    container_kind TEXT NOT NULL,           -- 'ambient_scope', 'namespace', 'class', 'struct', 'record', 'interface', 'enum'
    qualified_name TEXT NOT NULL,           -- '<ambient>', 'System', 'System.Collections.Generic', 'System.String'
    short_name TEXT NOT NULL,
    requires_import INTEGER NOT NULL DEFAULT 1, -- 0 for Stratum 0 ambient containers, 1 otherwise
    visibility TEXT NOT NULL,               -- 'public', 'internal', 'private', 'protected', 'protected_internal', 'private_protected'
    is_hidden INTEGER NOT NULL DEFAULT 0,   -- 1 if internal or private
    physical_path TEXT,
    stub_path TEXT,                         -- Metadata / Reference assembly path if applicable
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
    symbol_kind TEXT NOT NULL,              -- 'keyword', 'type_alias', 'method', 'constructor', 'property',
                                            -- 'field', 'event', 'indexer', 'operator', 'constant', 'enum_member'
    visibility TEXT NOT NULL,               -- 'public', 'internal', 'private', 'protected', 'protected_internal', 'private_protected'
    provenance TEXT NOT NULL,               -- 'ambient_keyword', 'bcl_reflected', 'nuget_referenced', 'ast_defined'
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
    type_params_json TEXT,                  -- Generic type parameters e.g. '["T"]'
    return_type_expr TEXT,
    raw_signature TEXT,
    signature_source TEXT NOT NULL          -- 'reflection', 'roslyn_ast', 'ambient'
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
    pass_kind TEXT NOT NULL,                -- 'value', 'ref', 'out', 'in', 'params', 'optional'
    type_expr TEXT,
    type_source TEXT,                       -- 'reflection', 'roslyn_ast', 'ambient'
    default_expr TEXT,
    is_optional INTEGER NOT NULL DEFAULT 0
);

-- Table: state_members
CREATE TABLE state_members (
    symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
    declared_type_expr TEXT,
    runtime_type_name TEXT NOT NULL,
    is_constant INTEGER NOT NULL DEFAULT 0,
    is_mutable INTEGER NOT NULL DEFAULT 1,
    literal_value_repr TEXT,
    access_mode TEXT NOT NULL DEFAULT 'read_write' -- 'read_only', 'read_write', 'init_only'
);

-- Table: symbol_aliases
CREATE TABLE symbol_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_container_id INTEGER NOT NULL REFERENCES containers(container_id) ON DELETE CASCADE,
    exposed_name TEXT NOT NULL,
    target_module_name TEXT NOT NULL,
    target_symbol_name TEXT NOT NULL,
    alias_kind TEXT NOT NULL,               -- 'using_alias', 'global_using', 'extern_alias'
    is_in_dunder_all INTEGER NOT NULL DEFAULT 0,
    UNIQUE(source_container_id, exposed_name)
);

-- ============================================================================
-- LAYER 2: C# .NET FIDELITY FACET TABLES (10-11)
-- ============================================================================
-- Table: cs_container_facets
CREATE TABLE cs_container_facets (
    container_id INTEGER PRIMARY KEY REFERENCES containers(container_id) ON DELETE CASCADE,
    type_kind TEXT NOT NULL,                -- 'class', 'struct', 'record_class', 'record_struct', 'interface', 'enum', 'delegate', 'namespace'
    is_sealed INTEGER NOT NULL DEFAULT 0,
    is_abstract INTEGER NOT NULL DEFAULT 0,
    is_static INTEGER NOT NULL DEFAULT 0,
    is_readonly_struct INTEGER NOT NULL DEFAULT 0,
    is_ref_struct INTEGER NOT NULL DEFAULT 0,
    base_type_qname TEXT,
    implemented_interfaces_json TEXT,       -- JSON array of interface qualified names e.g. ["System.IDisposable"]
    generic_type_parameters_json TEXT,      -- JSON array of generic param definitions e.g. [{"name":"T","constraints":["class","new()"]}]
    attributes_json TEXT                    -- JSON array of applied attribute names
);

-- Table: cs_symbol_facets
CREATE TABLE cs_symbol_facets (
    symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
    member_kind TEXT NOT NULL,              -- 'method', 'property', 'field', 'event', 'indexer', 'constructor', 'operator', 'conversion_operator'
    is_virtual INTEGER NOT NULL DEFAULT 0,
    is_override INTEGER NOT NULL DEFAULT 0,
    is_abstract INTEGER NOT NULL DEFAULT 0,
    is_sealed INTEGER NOT NULL DEFAULT 0,
    is_async INTEGER NOT NULL DEFAULT 0,
    is_unsafe INTEGER NOT NULL DEFAULT 0,
    is_extension_method INTEGER NOT NULL DEFAULT 0,
    is_init_only INTEGER NOT NULL DEFAULT 0,
    has_getter INTEGER NOT NULL DEFAULT 0,
    has_setter INTEGER NOT NULL DEFAULT 0,
    explicit_interface_specifier TEXT,      -- e.g. "System.IDisposable.Dispose"
    operator_kind TEXT,                     -- e.g. "op_Addition", "op_Implicit", etc.
    attributes_json TEXT
);

-- ============================================================================
-- PERFORMANCE INDICES
-- ============================================================================
CREATE INDEX idx_aliases_target ON symbol_aliases(target_module_name, target_symbol_name);
CREATE INDEX idx_containers_kind ON containers(container_kind, is_hidden);
CREATE INDEX idx_containers_qname ON containers(qualified_name);
CREATE INDEX idx_cs_container_facets_type ON cs_container_facets(type_kind);
CREATE INDEX idx_cs_symbol_facets_member ON cs_symbol_facets(member_kind);
CREATE INDEX idx_overloads_callable ON callable_overloads(callable_symbol_id, overload_ordinal);
CREATE INDEX idx_params_callable ON parameters(callable_symbol_id, overload_id, ordinal);
CREATE INDEX idx_symbols_container_name ON symbols(container_id, name);
CREATE INDEX idx_symbols_kind_vis ON symbols(symbol_kind, visibility);
CREATE INDEX idx_symbols_qname ON symbols(qualified_name);
