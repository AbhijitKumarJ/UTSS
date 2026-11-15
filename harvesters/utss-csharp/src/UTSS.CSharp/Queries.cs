using System.Data;
using Microsoft.Data.Sqlite;

namespace UTSS.CSharp;

public static class Queries
{
    public static Dictionary<string, int> GetSpectrumSummary(SqliteConnection conn)
    {
        var summary = new Dictionary<string, int>();
        foreach (var tbl in Schema.ExpectedTables)
        {
            using var cmd = conn.CreateCommand();
            cmd.CommandText = $"SELECT COUNT(*) FROM {tbl};";
            var count = Convert.ToInt32(cmd.ExecuteScalar());
            summary[tbl] = count;
        }
        return summary;
    }

    public static List<Dictionary<string, object?>> QueryDistributions(SqliteConnection conn)
    {
        var results = new List<Dictionary<string, object?>>();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
        SELECT d.dist_id, d.stratum, d.dist_name, d.dist_version, d.summary,
               COUNT(c.container_id) as container_count
        FROM distributions d
        LEFT JOIN containers c ON d.dist_id = c.dist_id
        GROUP BY d.dist_id
        ORDER BY d.stratum, d.dist_name;
        """;
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            var row = new Dictionary<string, object?>();
            for (int i = 0; i < reader.FieldCount; i++)
            {
                row[reader.GetName(i)] = reader.IsDBNull(i) ? null : reader.GetValue(i);
            }
            results.Add(row);
        }
        return results;
    }

    public static List<Dictionary<string, object?>> QueryAmbient(SqliteConnection conn)
    {
        var results = new List<Dictionary<string, object?>>();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
        SELECT s.symbol_id, s.name, s.qualified_name, s.symbol_kind, s.provenance,
               a.target_module_name, a.target_symbol_name, a.alias_kind
        FROM symbols s
        JOIN containers c ON s.container_id = c.container_id
        JOIN distributions d ON c.dist_id = d.dist_id
        LEFT JOIN symbol_aliases a ON a.source_container_id = c.container_id AND a.exposed_name = REPLACE(s.name, 'type_alias:', '')
        WHERE d.stratum = 0
        ORDER BY s.symbol_kind, s.name;
        """;
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            var row = new Dictionary<string, object?>();
            for (int i = 0; i < reader.FieldCount; i++)
            {
                row[reader.GetName(i)] = reader.IsDBNull(i) ? null : reader.GetValue(i);
            }
            results.Add(row);
        }
        return results;
    }

    public static List<Dictionary<string, object?>> QueryBcl(SqliteConnection conn, int limit = 20)
    {
        var results = new List<Dictionary<string, object?>>();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = $"""
        SELECT c.qualified_name as container_qname, c.container_kind,
               s.name as symbol_name, s.symbol_kind,
               cal.raw_signature, cal.has_overloads, cal.overload_count,
               f.is_virtual, f.is_override, f.is_abstract
        FROM containers c
        JOIN distributions d ON c.dist_id = d.dist_id
        JOIN symbols s ON s.container_id = c.container_id
        LEFT JOIN callables cal ON cal.symbol_id = s.symbol_id
        LEFT JOIN cs_symbol_facets f ON f.symbol_id = s.symbol_id
        WHERE d.stratum = 1
        ORDER BY c.qualified_name, s.name
        LIMIT {limit};
        """;
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            var row = new Dictionary<string, object?>();
            for (int i = 0; i < reader.FieldCount; i++)
            {
                row[reader.GetName(i)] = reader.IsDBNull(i) ? null : reader.GetValue(i);
            }
            results.Add(row);
        }
        return results;
    }

    public static List<Dictionary<string, object?>> QueryWorkspaceSymbols(SqliteConnection conn)
    {
        var results = new List<Dictionary<string, object?>>();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
        SELECT c.qualified_name as container_qname, c.container_kind,
               s.name as symbol_name, s.symbol_kind, s.visibility,
               s.start_line, s.start_col, s.end_line, s.end_col,
               cal.raw_signature, cal.is_async, cal.is_generator,
               sm.declared_type_expr, sm.access_mode,
               cf.type_kind as cs_type_kind, sf.is_extension_method, sf.is_init_only
        FROM symbols s
        JOIN containers c ON s.container_id = c.container_id
        JOIN distributions d ON c.dist_id = d.dist_id
        LEFT JOIN callables cal ON cal.symbol_id = s.symbol_id
        LEFT JOIN state_members sm ON sm.symbol_id = s.symbol_id
        LEFT JOIN cs_container_facets cf ON cf.container_id = c.container_id
        LEFT JOIN cs_symbol_facets sf ON sf.symbol_id = s.symbol_id
        WHERE d.stratum = 3
        ORDER BY c.qualified_name, s.start_line, s.name;
        """;
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            var row = new Dictionary<string, object?>();
            for (int i = 0; i < reader.FieldCount; i++)
            {
                row[reader.GetName(i)] = reader.IsDBNull(i) ? null : reader.GetValue(i);
            }
            results.Add(row);
        }
        return results;
    }

    public static List<Dictionary<string, object?>> QueryFacets(SqliteConnection conn)
    {
        var results = new List<Dictionary<string, object?>>();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
        SELECT c.qualified_name, cf.type_kind, cf.is_sealed, cf.is_abstract, cf.is_static,
               cf.base_type_qname, cf.implemented_interfaces_json
        FROM cs_container_facets cf
        JOIN containers c ON cf.container_id = c.container_id
        WHERE cf.type_kind IN ('record', 'record_struct', 'interface', 'struct', 'class')
        ORDER BY cf.type_kind, c.qualified_name;
        """;
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            var row = new Dictionary<string, object?>();
            for (int i = 0; i < reader.FieldCount; i++)
            {
                row[reader.GetName(i)] = reader.IsDBNull(i) ? null : reader.GetValue(i);
            }
            results.Add(row);
        }
        return results;
    }

    public static List<Dictionary<string, object?>> QueryBclSummary(SqliteConnection conn)
    {
        var results = new List<Dictionary<string, object?>>();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
        SELECT cf.type_kind, COUNT(c.container_id) as count
        FROM containers c
        JOIN distributions d ON c.dist_id = d.dist_id
        JOIN cs_container_facets cf ON c.container_id = cf.container_id
        WHERE d.stratum = 1
        GROUP BY cf.type_kind
        ORDER BY count DESC;
        """;
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            var row = new Dictionary<string, object?>();
            for (int i = 0; i < reader.FieldCount; i++)
            {
                row[reader.GetName(i)] = reader.IsDBNull(i) ? null : reader.GetValue(i);
            }
            results.Add(row);
        }
        return results;
    }

    public static List<Dictionary<string, object?>> QueryBclOverloads(SqliteConnection conn, int limit = 25)
    {
        var results = new List<Dictionary<string, object?>>();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = $"""
        SELECT c.qualified_name as container_qname, s.name as method_name,
               cal.overload_count, cal.return_type_expr
        FROM symbols s
        JOIN containers c ON s.container_id = c.container_id
        JOIN distributions d ON c.dist_id = d.dist_id
        JOIN callables cal ON cal.symbol_id = s.symbol_id
        WHERE d.stratum = 1 AND cal.has_overloads = 1
        ORDER BY cal.overload_count DESC
        LIMIT {limit};
        """;
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            var row = new Dictionary<string, object?>();
            for (int i = 0; i < reader.FieldCount; i++)
            {
                row[reader.GetName(i)] = reader.IsDBNull(i) ? null : reader.GetValue(i);
            }
            results.Add(row);
        }
        return results;
    }

    public static List<Dictionary<string, object?>> QueryBclGenerics(SqliteConnection conn, int limit = 25)
    {
        var results = new List<Dictionary<string, object?>>();
        using var cmd = conn.CreateCommand();
        cmd.CommandText = $"""
        SELECT c.qualified_name, cf.type_kind, cf.generic_type_parameters_json, cf.implemented_interfaces_json
        FROM containers c
        JOIN distributions d ON c.dist_id = d.dist_id
        JOIN cs_container_facets cf ON c.container_id = cf.container_id
        WHERE d.stratum = 1 AND cf.generic_type_parameters_json IS NOT NULL
        ORDER BY c.qualified_name
        LIMIT {limit};
        """;
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            var row = new Dictionary<string, object?>();
            for (int i = 0; i < reader.FieldCount; i++)
            {
                row[reader.GetName(i)] = reader.IsDBNull(i) ? null : reader.GetValue(i);
            }
            results.Add(row);
        }
        return results;
    }
}
