using System.Runtime.InteropServices;
using Microsoft.Data.Sqlite;

namespace UTSS.CSharp;

public static class Stratum0Ambient
{
    public static readonly string[] ReservedKeywords =
    [
        "abstract", "as", "base", "bool", "break", "byte", "case", "catch", "char", "checked",
        "class", "const", "continue", "decimal", "default", "delegate", "do", "double", "else",
        "enum", "event", "explicit", "extern", "false", "finally", "fixed", "float", "for",
        "foreach", "goto", "if", "implicit", "in", "int", "interface", "internal", "is", "lock",
        "long", "namespace", "new", "null", "object", "operator", "out", "override", "params",
        "private", "protected", "public", "readonly", "ref", "return", "sbyte", "sealed", "short",
        "sizeof", "stackalloc", "static", "string", "struct", "switch", "this", "throw", "true",
        "try", "typeof", "uint", "ulong", "unchecked", "unsafe", "ushort", "using", "virtual",
        "void", "volatile", "while"
    ];

    public static readonly string[] ContextualKeywords =
    [
        "add", "alias", "allows", "and", "args", "ascending", "async", "await", "by", "descending",
        "dynamic", "equals", "file", "from", "get", "global", "group", "init", "into", "join",
        "let", "managed", "nameof", "nint", "not", "notnull", "nuint", "on", "or", "orderby",
        "partial", "record", "remove", "required", "scoped", "select", "set", "unmanaged", "value",
        "var", "when", "where", "with", "yield"
    ];

    public static readonly Dictionary<string, (string Namespace, string TargetType)> PrimitiveTypeAliases = new()
    {
        ["bool"] = ("System", "Boolean"),
        ["byte"] = ("System", "Byte"),
        ["sbyte"] = ("System", "SByte"),
        ["char"] = ("System", "Char"),
        ["decimal"] = ("System", "Decimal"),
        ["double"] = ("System", "Double"),
        ["float"] = ("System", "Single"),
        ["int"] = ("System", "Int32"),
        ["uint"] = ("System", "UInt32"),
        ["nint"] = ("System", "IntPtr"),
        ["nuint"] = ("System", "UIntPtr"),
        ["long"] = ("System", "Int64"),
        ["ulong"] = ("System", "UInt64"),
        ["short"] = ("System", "Int16"),
        ["ushort"] = ("System", "UInt16"),
        ["object"] = ("System", "Object"),
        ["string"] = ("System", "String"),
        ["void"] = ("System", "Void")
    };

    public static readonly string[] ImplicitGlobalUsings =
    [
        "System",
        "System.Collections.Generic",
        "System.IO",
        "System.Linq",
        "System.Net.Http",
        "System.Threading",
        "System.Threading.Tasks"
    ];

    public static readonly string[] GlobalStaticUsings =
    [
        "System.Console",
        "System.Math"
    ];

    public static readonly (string Name, string Type, string Value)[] AmbientLiterals =
    [
        ("null", "object", "null"),
        ("true", "bool", "true"),
        ("false", "bool", "false"),
        ("default", "object", "default")
    ];

    public static long EnsureEnvironment(SqliteConnection conn)
    {
        var osDesc = RuntimeInformation.OSDescription;
        var arch = RuntimeInformation.ProcessArchitecture.ToString().ToLowerInvariant();
        var platformTriplet = $"{Environment.OSVersion.Platform}-{arch}";
        var sysPlatform = OperatingSystem.IsWindows() ? "win32" : OperatingSystem.IsMacOS() ? "darwin" : "linux";
        var exePath = Environment.ProcessPath ?? "/usr/bin/dotnet";
        var dotNetVer = Environment.Version; // e.g. 10.0.0

        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
        INSERT INTO environments (
            language, runtime_name, language_version, version_major, version_minor, version_micro,
            platform_triplet, sys_platform, executable_path
        )
        VALUES ('csharp', '.NET', @langVer, @vMaj, @vMin, @vMic, @plat, @sysPlat, @exe)
        ON CONFLICT(language, runtime_name, language_version, platform_triplet, executable_path)
        DO UPDATE SET captured_at = CURRENT_TIMESTAMP
        RETURNING env_id;
        """;
        cmd.Parameters.AddWithValue("@langVer", $"{dotNetVer.Major}.{dotNetVer.Minor}");
        cmd.Parameters.AddWithValue("@vMaj", dotNetVer.Major);
        cmd.Parameters.AddWithValue("@vMin", dotNetVer.Minor);
        cmd.Parameters.AddWithValue("@vMic", Math.Max(0, dotNetVer.Build));
        cmd.Parameters.AddWithValue("@plat", platformTriplet);
        cmd.Parameters.AddWithValue("@sysPlat", sysPlatform);
        cmd.Parameters.AddWithValue("@exe", exePath);

        return Convert.ToInt64(cmd.ExecuteScalar());
    }

    public static long EnsureDistribution(SqliteConnection conn, long envId, int stratum, string distName, string distVersion, string? summary = null)
    {
        using var cmd = conn.CreateCommand();
        cmd.CommandText = """
        INSERT INTO distributions (env_id, stratum, dist_name, dist_version, summary)
        VALUES (@envId, @stratum, @distName, @distVer, @summary)
        ON CONFLICT(env_id, stratum, dist_name, dist_version)
        DO UPDATE SET summary = excluded.summary
        RETURNING dist_id;
        """;
        cmd.Parameters.AddWithValue("@envId", envId);
        cmd.Parameters.AddWithValue("@stratum", stratum);
        cmd.Parameters.AddWithValue("@distName", distName);
        cmd.Parameters.AddWithValue("@distVer", distVersion);
        cmd.Parameters.AddWithValue("@summary", (object?)summary ?? DBNull.Value);

        return Convert.ToInt64(cmd.ExecuteScalar());
    }

    public static (int KeywordCount, int AliasCount, int GlobalUsingCount) Harvest(SqliteConnection conn)
    {
        var envId = EnsureEnvironment(conn);
        var distVer = $"{Environment.Version.Major}.{Environment.Version.Minor}";
        var distId = EnsureDistribution(conn, envId, Strata.Ambient, "<ambient>", distVer, "C# Ambient Scope: keywords, aliases, global implicit usings");

        // 1. Ambient Container
        long ambientContainerId;
        using (var cmd = conn.CreateCommand())
        {
            cmd.CommandText = """
            INSERT INTO containers (
                dist_id, parent_container_id, container_kind, qualified_name, short_name, requires_import, visibility, is_hidden
            )
            VALUES (@distId, NULL, @kind, @qname, @sname, 0, @vis, 0)
            ON CONFLICT(dist_id, qualified_name) DO UPDATE SET container_kind = excluded.container_kind
            RETURNING container_id;
            """;
            cmd.Parameters.AddWithValue("@distId", distId);
            cmd.Parameters.AddWithValue("@kind", ContainerKinds.AmbientScope);
            cmd.Parameters.AddWithValue("@qname", "<ambient>");
            cmd.Parameters.AddWithValue("@sname", "<ambient>");
            cmd.Parameters.AddWithValue("@vis", Visibilities.Public);
            ambientContainerId = Convert.ToInt64(cmd.ExecuteScalar());
        }

        // C# Container Facet for ambient scope
        using (var cmdFacet = conn.CreateCommand())
        {
            cmdFacet.CommandText = """
            INSERT INTO cs_container_facets (container_id, type_kind, is_sealed, is_abstract, is_static)
            VALUES (@cid, 'namespace', 0, 0, 0)
            ON CONFLICT(container_id) DO NOTHING;
            """;
            cmdFacet.Parameters.AddWithValue("@cid", ambientContainerId);
            cmdFacet.ExecuteNonQuery();
        }

        int keywordCount = 0;
        using var tx = conn.BeginTransaction();

        // 2. Keywords
        var allKeywords = ReservedKeywords.Select(k => (k, "keyword"))
            .Concat(ContextualKeywords.Select(k => (k, "soft_keyword")));

        foreach (var (kw, kind) in allKeywords)
        {
            long symId;
            using (var cmd = conn.CreateCommand())
            {
                cmd.Transaction = tx;
                cmd.CommandText = """
                INSERT INTO symbols (container_id, origin_container_id, name, qualified_name, symbol_kind, visibility, provenance, is_hidden)
                VALUES (@cid, @cid, @name, @qname, @kind, @vis, @prov, 0)
                ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
                RETURNING symbol_id;
                """;
                cmd.Parameters.AddWithValue("@cid", ambientContainerId);
                cmd.Parameters.AddWithValue("@name", kw);
                cmd.Parameters.AddWithValue("@qname", $"<ambient>.{kw}");
                cmd.Parameters.AddWithValue("@kind", kind);
                cmd.Parameters.AddWithValue("@vis", Visibilities.Public);
                cmd.Parameters.AddWithValue("@prov", Provenances.AmbientKeyword);
                symId = Convert.ToInt64(cmd.ExecuteScalar());
            }

            using (var cmdFacet = conn.CreateCommand())
            {
                cmdFacet.Transaction = tx;
                cmdFacet.CommandText = """
                INSERT INTO cs_symbol_facets (symbol_id, member_kind)
                VALUES (@sid, @kind)
                ON CONFLICT(symbol_id) DO NOTHING;
                """;
                cmdFacet.Parameters.AddWithValue("@sid", symId);
                cmdFacet.Parameters.AddWithValue("@kind", kind);
                cmdFacet.ExecuteNonQuery();
            }
            keywordCount++;
        }

        // 3. Primitive Type Aliases
        int aliasCount = 0;
        foreach (var (alias, target) in PrimitiveTypeAliases)
        {
            long symId;
            using (var cmd = conn.CreateCommand())
            {
                cmd.Transaction = tx;
                cmd.CommandText = """
                INSERT INTO symbols (container_id, origin_container_id, name, qualified_name, symbol_kind, visibility, provenance, is_hidden)
                VALUES (@cid, @cid, @name, @qname, @kind, @vis, @prov, 0)
                ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
                RETURNING symbol_id;
                """;
                cmd.Parameters.AddWithValue("@cid", ambientContainerId);
                cmd.Parameters.AddWithValue("@name", $"type_alias:{alias}");
                cmd.Parameters.AddWithValue("@qname", $"<ambient>.{alias}");
                cmd.Parameters.AddWithValue("@kind", SymbolKinds.TypeAlias);
                cmd.Parameters.AddWithValue("@vis", Visibilities.Public);
                cmd.Parameters.AddWithValue("@prov", Provenances.AmbientTypeAlias);
                symId = Convert.ToInt64(cmd.ExecuteScalar());
            }

            using (var cmdFacet = conn.CreateCommand())
            {
                cmdFacet.Transaction = tx;
                cmdFacet.CommandText = """
                INSERT INTO cs_symbol_facets (symbol_id, member_kind)
                VALUES (@sid, 'type_alias')
                ON CONFLICT(symbol_id) DO NOTHING;
                """;
                cmdFacet.Parameters.AddWithValue("@sid", symId);
                cmdFacet.ExecuteNonQuery();
            }

            // symbol_aliases entry
            using (var cmdAlias = conn.CreateCommand())
            {
                cmdAlias.Transaction = tx;
                cmdAlias.CommandText = """
                INSERT INTO symbol_aliases (source_container_id, exposed_name, target_module_name, target_symbol_name, alias_kind, is_in_dunder_all)
                VALUES (@srcId, @expName, @tgtMod, @tgtSym, 'primitive_type_alias', 0)
                ON CONFLICT(source_container_id, exposed_name) DO UPDATE SET target_module_name = excluded.target_module_name;
                """;
                cmdAlias.Parameters.AddWithValue("@srcId", ambientContainerId);
                cmdAlias.Parameters.AddWithValue("@expName", alias);
                cmdAlias.Parameters.AddWithValue("@tgtMod", target.Namespace);
                cmdAlias.Parameters.AddWithValue("@tgtSym", target.TargetType);
                cmdAlias.ExecuteNonQuery();
            }
            aliasCount++;
        }

        // 4. Implicit Global Usings
        int globalUsingCount = 0;
        foreach (var ns in ImplicitGlobalUsings)
        {
            using var cmdUsing = conn.CreateCommand();
            cmdUsing.Transaction = tx;
            cmdUsing.CommandText = """
            INSERT INTO symbol_aliases (source_container_id, exposed_name, target_module_name, target_symbol_name, alias_kind, is_in_dunder_all)
            VALUES (@srcId, @expName, @tgtMod, '*', 'global_using', 0)
            ON CONFLICT(source_container_id, exposed_name) DO UPDATE SET target_module_name = excluded.target_module_name;
            """;
            cmdUsing.Parameters.AddWithValue("@srcId", ambientContainerId);
            cmdUsing.Parameters.AddWithValue("@expName", $"using {ns}");
            cmdUsing.Parameters.AddWithValue("@tgtMod", ns);
            cmdUsing.ExecuteNonQuery();
            globalUsingCount++;
        }

        // 5. Global Static Usings (Console, Math)
        foreach (var staticNs in GlobalStaticUsings)
        {
            using var cmdStatic = conn.CreateCommand();
            cmdStatic.Transaction = tx;
            cmdStatic.CommandText = """
            INSERT INTO symbol_aliases (source_container_id, exposed_name, target_module_name, target_symbol_name, alias_kind, is_in_dunder_all)
            VALUES (@srcId, @expName, @tgtMod, '*', 'global_using_static', 0)
            ON CONFLICT(source_container_id, exposed_name) DO UPDATE SET target_module_name = excluded.target_module_name;
            """;
            cmdStatic.Parameters.AddWithValue("@srcId", ambientContainerId);
            cmdStatic.Parameters.AddWithValue("@expName", $"using static {staticNs}");
            cmdStatic.Parameters.AddWithValue("@tgtMod", staticNs);
            cmdStatic.ExecuteNonQuery();
            globalUsingCount++;
        }

        // 6. Ambient Literals & Constants
        foreach (var (litName, litType, litVal) in AmbientLiterals)
        {
            long litSymId;
            using (var cmd = conn.CreateCommand())
            {
                cmd.Transaction = tx;
                cmd.CommandText = """
                INSERT INTO symbols (container_id, origin_container_id, name, qualified_name, symbol_kind, visibility, provenance, is_hidden)
                VALUES (@cid, @cid, @name, @qname, 'constant', 'public', 'ambient_constant', 0)
                ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
                RETURNING symbol_id;
                """;
                cmd.Parameters.AddWithValue("@cid", ambientContainerId);
                cmd.Parameters.AddWithValue("@name", litName);
                cmd.Parameters.AddWithValue("@qname", $"<ambient>.{litName}");
                litSymId = Convert.ToInt64(cmd.ExecuteScalar());
            }

            using (var cmdState = conn.CreateCommand())
            {
                cmdState.Transaction = tx;
                cmdState.CommandText = """
                INSERT INTO state_members (symbol_id, declared_type_expr, runtime_type_name, is_constant, is_mutable, literal_value_repr, access_mode)
                VALUES (@sid, @declType, @declType, 1, 0, @val, 'read_only')
                ON CONFLICT(symbol_id) DO NOTHING;
                """;
                cmdState.Parameters.AddWithValue("@sid", litSymId);
                cmdState.Parameters.AddWithValue("@declType", litType);
                cmdState.Parameters.AddWithValue("@val", litVal);
                cmdState.ExecuteNonQuery();
            }

            using (var cmdFacet = conn.CreateCommand())
            {
                cmdFacet.Transaction = tx;
                cmdFacet.CommandText = """
                INSERT INTO cs_symbol_facets (symbol_id, member_kind)
                VALUES (@sid, 'constant')
                ON CONFLICT(symbol_id) DO NOTHING;
                """;
                cmdFacet.Parameters.AddWithValue("@sid", litSymId);
                cmdFacet.ExecuteNonQuery();
            }
        }

        tx.Commit();
        return (keywordCount, aliasCount, globalUsingCount);
    }
}
