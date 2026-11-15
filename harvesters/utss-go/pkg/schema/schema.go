package schema

import (
	"database/sql"
	"fmt"
)

var ExpectedTables = []string{
	"environments",
	"distributions",
	"containers",
	"symbols",
	"callables",
	"callable_overloads",
	"parameters",
	"state_members",
	"symbol_aliases",
	"go_container_facets",
	"go_symbol_facets",
}

const SchemaSQL = `
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA foreign_keys = ON;

-- 1. Environments: Tracks exact language runtime versions & platforms
CREATE TABLE IF NOT EXISTS environments (
    env_id INTEGER PRIMARY KEY AUTOINCREMENT,
    language TEXT NOT NULL,                 -- 'go'
    runtime_name TEXT NOT NULL,             -- 'gc'
    language_version TEXT NOT NULL,         -- 'go1.27.4'
    version_major INTEGER NOT NULL,
    version_minor INTEGER NOT NULL,
    version_micro INTEGER NOT NULL,
    platform_triplet TEXT NOT NULL,         -- 'linux-amd64'
    sys_platform TEXT NOT NULL,             -- 'linux'
    executable_path TEXT NOT NULL,
    captured_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(language, runtime_name, language_version, platform_triplet, executable_path)
);

-- 2. Distributions: Logical deliverable units
CREATE TABLE IF NOT EXISTS distributions (
    dist_id INTEGER PRIMARY KEY AUTOINCREMENT,
    env_id INTEGER NOT NULL REFERENCES environments(env_id) ON DELETE CASCADE,
    stratum INTEGER NOT NULL,               -- 0 = Ambient, 1 = Stdlib, 3 = Workspace
    dist_name TEXT NOT NULL,                -- '<ambient>', 'std', 'commerce_engine'
    dist_version TEXT NOT NULL,             -- Go version for 0/1, module version for 3
    summary TEXT,
    UNIQUE(env_id, stratum, dist_name, dist_version)
);

-- 3. Containers: Universal hierarchy (ambient_scope, package, struct, interface, type)
CREATE TABLE IF NOT EXISTS containers (
    container_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dist_id INTEGER NOT NULL REFERENCES distributions(dist_id) ON DELETE CASCADE,
    parent_container_id INTEGER REFERENCES containers(container_id) ON DELETE CASCADE,
    container_kind TEXT NOT NULL,           -- 'ambient_scope', 'package', 'struct', 'interface', 'type'
    qualified_name TEXT NOT NULL,           -- '<ambient>', 'fmt', 'commerce/models.Order'
    short_name TEXT NOT NULL,
    requires_import INTEGER NOT NULL DEFAULT 1,
    visibility TEXT NOT NULL,               -- 'public', 'private'
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
    symbol_kind TEXT NOT NULL,              -- 'keyword', 'primitive_type', 'function', 'method',
                                            -- 'struct_field', 'interface_method', 'constant', 'variable', 'type'
    visibility TEXT NOT NULL,               -- 'public', 'private'
    provenance TEXT NOT NULL,               -- 'ambient_keyword', 'ambient_builtin', 'std_item', 'ast_defined'
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
    type_params_json TEXT,                  -- Generics e.g. '[T any]'
    return_type_expr TEXT,
    raw_signature TEXT,
    signature_source TEXT NOT NULL          -- 'go_std_metadata', 'go_ast', 'ambient'
);

-- 6. Callable Overloads: Overloads placeholder (Go does not support overloading directly)
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
    pass_kind TEXT NOT NULL,                -- 'val', 'pointer', 'slice', 'variadic'
    type_expr TEXT,
    type_source TEXT,
    default_expr TEXT,
    is_optional INTEGER NOT NULL DEFAULT 0
);

-- 8. State Members: Struct fields, package-level vars, constants
CREATE TABLE IF NOT EXISTS state_members (
    symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
    declared_type_expr TEXT,
    runtime_type_name TEXT NOT NULL,
    is_constant INTEGER NOT NULL DEFAULT 0,
    is_mutable INTEGER NOT NULL DEFAULT 0,
    literal_value_repr TEXT,
    access_mode TEXT NOT NULL DEFAULT 'read_write'
);

-- 9. Symbol Aliases: Package imports and type aliases
CREATE TABLE IF NOT EXISTS symbol_aliases (
    alias_id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_container_id INTEGER NOT NULL REFERENCES containers(container_id) ON DELETE CASCADE,
    exposed_name TEXT NOT NULL,
    target_module_name TEXT NOT NULL,
    target_symbol_name TEXT NOT NULL,
    alias_kind TEXT NOT NULL,               -- 'package_import', 'type_alias'
    is_in_dunder_all INTEGER NOT NULL DEFAULT 0,
    UNIQUE(source_container_id, exposed_name)
);

-- 10. Go Container Facets: Package, struct embedding, generics
CREATE TABLE IF NOT EXISTS go_container_facets (
    container_id INTEGER PRIMARY KEY REFERENCES containers(container_id) ON DELETE CASCADE,
    package_name TEXT NOT NULL,
    item_kind TEXT NOT NULL,                -- 'package', 'struct', 'interface', 'type_alias'
    type_params_json TEXT,                  -- Generics e.g. '[T any]'
    embedded_fields_json TEXT,              -- Embedded structs/interfaces
    is_exported INTEGER NOT NULL DEFAULT 0
);

-- 11. Go Symbol Facets: Receiver kinds, variadics, exported state
CREATE TABLE IF NOT EXISTS go_symbol_facets (
    symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
    member_kind TEXT NOT NULL,              -- 'func', 'method', 'field', 'const', 'var', 'type', 'builtin'
    receiver_kind TEXT NOT NULL DEFAULT 'none', -- 'none', 'value', 'pointer'
    receiver_type TEXT,                     -- e.g. '*Order', 'Order'
    is_exported INTEGER NOT NULL DEFAULT 0,
    is_variadic INTEGER NOT NULL DEFAULT 0,
    signature_json TEXT
);

-- Indices
CREATE INDEX IF NOT EXISTS idx_go_containers_dist ON containers(dist_id);
CREATE INDEX IF NOT EXISTS idx_go_symbols_container ON symbols(container_id);
CREATE INDEX IF NOT EXISTS idx_go_symbols_kind ON symbols(symbol_kind);
CREATE INDEX IF NOT EXISTS idx_go_parameters_callable ON parameters(callable_symbol_id);
`

func InitSchema(db *sql.DB) error {
	_, err := db.Exec(SchemaSQL)
	return err
}

func ResetSchema(db *sql.DB) error {
	for i := len(ExpectedTables) - 1; i >= 0; i-- {
		table := ExpectedTables[i]
		dropSQL := fmt.Sprintf("DROP TABLE IF EXISTS %s;", table)
		if _, err := db.Exec(dropSQL); err != nil {
			return fmt.Errorf("failed to drop table %s: %w", table, err)
		}
	}
	return InitSchema(db)
}
