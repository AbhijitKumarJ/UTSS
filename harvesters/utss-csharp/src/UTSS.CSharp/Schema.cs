using System.Data;
using Microsoft.Data.Sqlite;

namespace UTSS.CSharp;

public static class Schema
{
    public static readonly string[] ExpectedTables =
    [
        "environments",
        "distributions",
        "containers",
        "symbols",
        "callables",
        "callable_overloads",
        "parameters",
        "state_members",
        "symbol_aliases",
        "cs_container_facets",
        "cs_symbol_facets"
    ];

    public const string SchemaSql = """
    PRAGMA journal_mode = WAL;
    PRAGMA synchronous = NORMAL;
    PRAGMA foreign_keys = ON;

    -- 1. Environments: Tracks exact language runtime versions & platforms
    CREATE TABLE IF NOT EXISTS environments (
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

    -- 2. Distributions: Logical deliverable units (Ambient, BCL/Runtime, NuGet packages, Workspace)
    CREATE TABLE IF NOT EXISTS distributions (
        dist_id INTEGER PRIMARY KEY AUTOINCREMENT,
        env_id INTEGER NOT NULL REFERENCES environments(env_id) ON DELETE CASCADE,
        stratum INTEGER NOT NULL,               -- 0 = Ambient, 1 = BCL/Runtime, 2 = NuGet/Ecosystem, 3 = Workspace
        dist_name TEXT NOT NULL,                -- '<ambient>', 'System.Runtime', 'Newtonsoft.Json', '<workspace>'
        dist_version TEXT NOT NULL,             -- .NET version for 0/1, assembly/package version for 2/3
        summary TEXT,
        UNIQUE(env_id, stratum, dist_name, dist_version)
    );

    -- 3. Containers: Universal hierarchy (ambient_scope, namespace, class, struct, record, interface, enum)
    CREATE TABLE IF NOT EXISTS containers (
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

    -- 4. Symbols: Master directory of every callable, field, property, constant, keyword, or event
    CREATE TABLE IF NOT EXISTS symbols (
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

    -- 5. Callables: Universal primary signature & execution modifiers for methods, constructors, operators
    CREATE TABLE IF NOT EXISTS callables (
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

    -- 6. Callable Overloads: Stores 1..N signatures per method
    CREATE TABLE IF NOT EXISTS callable_overloads (
        overload_id INTEGER PRIMARY KEY AUTOINCREMENT,
        callable_symbol_id INTEGER NOT NULL REFERENCES callables(symbol_id) ON DELETE CASCADE,
        overload_ordinal INTEGER NOT NULL,
        type_params_json TEXT,
        return_type_expr TEXT,
        raw_signature TEXT NOT NULL,
        UNIQUE(callable_symbol_id, overload_ordinal)
    );

    -- 7. Parameters: Ordered parameter list for callables and overload variants
    CREATE TABLE IF NOT EXISTS parameters (
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

    -- 8. State Members: Fields, properties, constants, and enum members
    CREATE TABLE IF NOT EXISTS state_members (
        symbol_id INTEGER PRIMARY KEY REFERENCES symbols(symbol_id) ON DELETE CASCADE,
        declared_type_expr TEXT,
        runtime_type_name TEXT NOT NULL,
        is_constant INTEGER NOT NULL DEFAULT 0,
        is_mutable INTEGER NOT NULL DEFAULT 1,
        literal_value_repr TEXT,
        access_mode TEXT NOT NULL DEFAULT 'read_write' -- 'read_only', 'read_write', 'init_only'
    );

    -- 9. Symbol Aliases: Using aliases (e.g. 'using ProjectOrder = CommerceEngine.Models.Order;') and global usings
    CREATE TABLE IF NOT EXISTS symbol_aliases (
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
    -- C#-SPECIFIC FIDELITY FACET TABLES (1:1 WITH CORE TABLES)
    -- ============================================================================

    -- 10. C# Container Facets: Type kind, inheritance, generic type params, attributes
    CREATE TABLE IF NOT EXISTS cs_container_facets (
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

    -- 11. C# Symbol Facets: Method/member modifiers, accessors, operators
    CREATE TABLE IF NOT EXISTS cs_symbol_facets (
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

    -- Indexes for high-performance symbol table querying
    CREATE INDEX IF NOT EXISTS idx_containers_qname ON containers(qualified_name);
    CREATE INDEX IF NOT EXISTS idx_containers_kind ON containers(container_kind, is_hidden);
    CREATE INDEX IF NOT EXISTS idx_symbols_qname ON symbols(qualified_name);
    CREATE INDEX IF NOT EXISTS idx_symbols_kind_vis ON symbols(symbol_kind, visibility);
    CREATE INDEX IF NOT EXISTS idx_symbols_container_name ON symbols(container_id, name);
    CREATE INDEX IF NOT EXISTS idx_aliases_target ON symbol_aliases(target_module_name, target_symbol_name);
    CREATE INDEX IF NOT EXISTS idx_params_callable ON parameters(callable_symbol_id, overload_id, ordinal);
    CREATE INDEX IF NOT EXISTS idx_overloads_callable ON callable_overloads(callable_symbol_id, overload_ordinal);
    CREATE INDEX IF NOT EXISTS idx_cs_container_facets_type ON cs_container_facets(type_kind);
    CREATE INDEX IF NOT EXISTS idx_cs_symbol_facets_member ON cs_symbol_facets(member_kind);
    """;

    public static void InitDb(SqliteConnection conn, bool reset = false)
    {
        if (conn.State != ConnectionState.Open)
        {
            conn.Open();
        }

        using var cmdPragma = conn.CreateCommand();
        cmdPragma.CommandText = "PRAGMA foreign_keys = ON;";
        cmdPragma.ExecuteNonQuery();

        if (reset)
        {
            string[] dropTablesOrder =
            [
                "cs_symbol_facets",
                "cs_container_facets",
                "symbol_aliases",
                "state_members",
                "parameters",
                "callable_overloads",
                "callables",
                "symbols",
                "containers",
                "distributions",
                "environments"
            ];

            foreach (var tbl in dropTablesOrder)
            {
                using var dropCmd = conn.CreateCommand();
                dropCmd.CommandText = $"DROP TABLE IF EXISTS {tbl};";
                dropCmd.ExecuteNonQuery();
            }
        }

        using var cmd = conn.CreateCommand();
        cmd.CommandText = SchemaSql;
        cmd.ExecuteNonQuery();
    }
}
