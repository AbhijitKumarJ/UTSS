using System.Reflection;
using System.Text.Json;
using Microsoft.Data.Sqlite;

namespace UTSS.CSharp;

public static class Stratum1Runtime
{
    public static readonly Type[] DefaultBclTypes =
    [
        typeof(object),
        typeof(string),
        typeof(int),
        typeof(double),
        typeof(bool),
        typeof(Math),
        typeof(Exception),
        typeof(IDisposable),
        typeof(List<>),
        typeof(Dictionary<,>),
        typeof(Task),
        typeof(File)
    ];

    public static readonly Type[] RecommendedBclTypes =
    [
        // 1. Fundamental Primitives & Value Types
        typeof(object), typeof(string), typeof(bool), typeof(byte), typeof(sbyte),
        typeof(char), typeof(short), typeof(ushort), typeof(int), typeof(uint),
        typeof(long), typeof(ulong), typeof(float), typeof(double), typeof(decimal),
        typeof(IntPtr), typeof(UIntPtr), typeof(Guid), typeof(DateTime), typeof(TimeSpan),
        typeof(DateOnly), typeof(TimeOnly), typeof(Range), typeof(Index), typeof(Array),
        typeof(Span<>), typeof(ReadOnlySpan<>), typeof(Memory<>), typeof(ReadOnlyMemory<>),
        typeof(Nullable<>),

        // 2. Core Utilities & System Classes
        typeof(Console), typeof(Environment), typeof(Math), typeof(MathF), typeof(Random),

        // 3. Essential Interfaces
        typeof(IDisposable), typeof(IAsyncDisposable), typeof(IComparable), typeof(IComparable<>),
        typeof(IEquatable<>), typeof(IFormattable), typeof(ICloneable),

        // 4. Collections & Generics
        typeof(List<>), typeof(Dictionary<,>), typeof(HashSet<>), typeof(Queue<>), typeof(Stack<>),
        typeof(LinkedList<>), typeof(KeyValuePair<,>), typeof(IEnumerable<>), typeof(ICollection<>),
        typeof(IList<>), typeof(IReadOnlyList<>), typeof(IDictionary<,>), typeof(IReadOnlyDictionary<,>),
        typeof(ISet<>),

        // 5. IO & Streams
        typeof(File), typeof(Directory), typeof(Path), typeof(Stream), typeof(MemoryStream),
        typeof(FileStream), typeof(StreamReader), typeof(StreamWriter),

        // 6. LINQ
        typeof(System.Linq.Enumerable), typeof(System.Linq.Queryable),

        // 7. Text, Formatting, JSON & Regex
        typeof(System.Text.StringBuilder), typeof(System.Text.Encoding),
        typeof(System.Text.RegularExpressions.Regex),
        typeof(System.Text.Json.JsonSerializer), typeof(System.Text.Json.JsonDocument),

        // 8. Asynchronous Tasks & Concurrency
        typeof(Task), typeof(Task<>), typeof(ValueTask), typeof(ValueTask<>),
        typeof(CancellationToken), typeof(CancellationTokenSource),

        // 9. Networking
        typeof(System.Net.Http.HttpClient),

        // 10. Common Exceptions
        typeof(Exception), typeof(ArgumentException), typeof(ArgumentNullException),
        typeof(InvalidOperationException), typeof(NotSupportedException),
        typeof(KeyNotFoundException), typeof(IndexOutOfRangeException)
    ];

    public static List<Type> GetFullBclTypes()
    {
        var assemblies = new HashSet<Assembly>
        {
            typeof(object).Assembly,
            typeof(System.Linq.Enumerable).Assembly,
            typeof(List<>).Assembly,
            typeof(File).Assembly,
            typeof(System.Text.Json.JsonSerializer).Assembly,
            typeof(System.Text.RegularExpressions.Regex).Assembly,
            typeof(System.Net.Http.HttpClient).Assembly,
            typeof(Task).Assembly
        };

        var types = new List<Type>();
        foreach (var asm in assemblies)
        {
            try
            {
                var exported = asm.GetExportedTypes()
                    .Where(t => t.IsPublic && !t.Name.StartsWith("<") && !t.Name.Contains("__") && !t.IsPointer && !t.IsByRef)
                    .ToList();
                types.AddRange(exported);
            }
            catch
            {
                // Ignore types that fail to load
            }
        }
        return types.Distinct().ToList();
    }

    public static (int ContainerCount, int SymbolCount, int CallableCount) Harvest(
        SqliteConnection conn,
        IEnumerable<Type>? targetTypes = null)
    {
        var types = (targetTypes ?? DefaultBclTypes).ToList();
        var envId = Stratum0Ambient.EnsureEnvironment(conn);
        var distVer = $"{Environment.Version.Major}.{Environment.Version.Minor}";
        var distId = Stratum0Ambient.EnsureDistribution(
            conn, envId, Strata.Runtime, "System.Runtime", distVer, "CoreCLR Base Class Library (BCL)");

        int containerCount = 0;
        int symbolCount = 0;
        int callableCount = 0;

        var namespaceContainerIds = new Dictionary<string, long>();

        using var tx = conn.BeginTransaction();

        // 1. Ensure Namespace Containers
        foreach (var t in types)
        {
            var ns = t.Namespace ?? "global";
            if (!namespaceContainerIds.ContainsKey(ns))
            {
                long nsId;
                using (var cmd = conn.CreateCommand())
                {
                    cmd.Transaction = tx;
                    cmd.CommandText = """
                    INSERT INTO containers (
                        dist_id, parent_container_id, container_kind, qualified_name, short_name, requires_import, visibility, is_hidden
                    )
                    VALUES (@distId, NULL, @kind, @qname, @sname, 1, @vis, 0)
                    ON CONFLICT(dist_id, qualified_name) DO UPDATE SET container_kind = excluded.container_kind
                    RETURNING container_id;
                    """;
                    cmd.Parameters.AddWithValue("@distId", distId);
                    cmd.Parameters.AddWithValue("@kind", ContainerKinds.Namespace);
                    cmd.Parameters.AddWithValue("@qname", ns);
                    cmd.Parameters.AddWithValue("@sname", ns.Split('.').Last());
                    cmd.Parameters.AddWithValue("@vis", Visibilities.Public);
                    nsId = Convert.ToInt64(cmd.ExecuteScalar());
                }

                using (var cmdFacet = conn.CreateCommand())
                {
                    cmdFacet.Transaction = tx;
                    cmdFacet.CommandText = """
                    INSERT INTO cs_container_facets (container_id, type_kind)
                    VALUES (@cid, 'namespace')
                    ON CONFLICT(container_id) DO NOTHING;
                    """;
                    cmdFacet.Parameters.AddWithValue("@cid", nsId);
                    cmdFacet.ExecuteNonQuery();
                }

                namespaceContainerIds[ns] = nsId;
                containerCount++;
            }
        }

        // 2. Harvest each Type
        foreach (var t in types)
        {
            try
            {
                var ns = t.Namespace ?? "global";
                var parentNsId = namespaceContainerIds[ns];
                var typeKind = DetermineTypeKind(t);
                var isSealed = t.IsSealed ? 1 : 0;
                var isAbstract = t.IsAbstract ? 1 : 0;
                var isStatic = (t.IsAbstract && t.IsSealed) ? 1 : 0;
                var isValType = t.IsValueType;
                var isReadonly = 0;
                var qname = GetCleanTypeName(t);
                var sname = t.IsGenericType ? t.Name.Split('`')[0] : t.Name;

                var baseTypeQName = t.BaseType != null ? GetCleanTypeName(t.BaseType) : null;
                var ifaces = t.GetInterfaces().Select(GetCleanTypeName).ToArray();
                var ifacesJson = ifaces.Length > 0 ? JsonSerializer.Serialize(ifaces) : null;

                var genericParams = t.IsGenericTypeDefinition
                    ? t.GetGenericArguments().Select(a => new { name = a.Name }).ToArray()
                    : null;
                var genericParamsJson = genericParams != null ? JsonSerializer.Serialize(genericParams) : null;

                long typeContainerId;
                using (var cmd = conn.CreateCommand())
                {
                    cmd.Transaction = tx;
                    cmd.CommandText = """
                    INSERT INTO containers (
                        dist_id, parent_container_id, container_kind, qualified_name, short_name, requires_import, visibility, is_hidden
                    )
                    VALUES (@distId, @parentCid, @kind, @qname, @sname, 1, @vis, 0)
                    ON CONFLICT(dist_id, qualified_name) DO UPDATE SET container_kind = excluded.container_kind
                    RETURNING container_id;
                    """;
                    cmd.Parameters.AddWithValue("@distId", distId);
                    cmd.Parameters.AddWithValue("@parentCid", parentNsId);
                    cmd.Parameters.AddWithValue("@kind", typeKind);
                    cmd.Parameters.AddWithValue("@qname", qname);
                    cmd.Parameters.AddWithValue("@sname", sname);
                    cmd.Parameters.AddWithValue("@vis", t.IsPublic ? Visibilities.Public : Visibilities.Internal);
                    typeContainerId = Convert.ToInt64(cmd.ExecuteScalar());
                }

                using (var cmdFacet = conn.CreateCommand())
                {
                    cmdFacet.Transaction = tx;
                    cmdFacet.CommandText = """
                    INSERT INTO cs_container_facets (
                        container_id, type_kind, is_sealed, is_abstract, is_static,
                        is_readonly_struct, is_ref_struct, base_type_qname,
                        implemented_interfaces_json, generic_type_parameters_json
                    )
                    VALUES (
                        @cid, @typeKind, @isSealed, @isAbstract, @isStatic,
                        @isReadonly, 0, @baseType,
                        @ifaces, @genParams
                    )
                    ON CONFLICT(container_id) DO UPDATE SET
                        type_kind = excluded.type_kind,
                        is_sealed = excluded.is_sealed,
                        is_abstract = excluded.is_abstract,
                        is_static = excluded.is_static;
                    """;
                    cmdFacet.Parameters.AddWithValue("@cid", typeContainerId);
                    cmdFacet.Parameters.AddWithValue("@typeKind", typeKind);
                    cmdFacet.Parameters.AddWithValue("@isSealed", isSealed);
                    cmdFacet.Parameters.AddWithValue("@isAbstract", isAbstract);
                    cmdFacet.Parameters.AddWithValue("@isStatic", isStatic);
                    cmdFacet.Parameters.AddWithValue("@isReadonly", isReadonly);
                    cmdFacet.Parameters.AddWithValue("@baseType", (object?)baseTypeQName ?? DBNull.Value);
                    cmdFacet.Parameters.AddWithValue("@ifaces", (object?)ifacesJson ?? DBNull.Value);
                    cmdFacet.Parameters.AddWithValue("@genParams", (object?)genericParamsJson ?? DBNull.Value);
                    cmdFacet.ExecuteNonQuery();
                }

                containerCount++;

                // 3. Harvest Type Members: Constructors, Methods, Properties, Fields
                var bindingFlags = BindingFlags.Public | BindingFlags.Instance | BindingFlags.Static | BindingFlags.DeclaredOnly;

                // Constructors
                ConstructorInfo[] ctors = [];
                try { ctors = t.GetConstructors(bindingFlags); } catch { }
                if (ctors.Length > 0)
                {
                    long ctorSymId;
                    using (var cmd = conn.CreateCommand())
                    {
                        cmd.Transaction = tx;
                        cmd.CommandText = """
                        INSERT INTO symbols (container_id, origin_container_id, name, qualified_name, symbol_kind, visibility, provenance, is_hidden)
                        VALUES (@cid, @cid, '.ctor', @qname, @kind, @vis, @prov, 0)
                        ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
                        RETURNING symbol_id;
                        """;
                        cmd.Parameters.AddWithValue("@cid", typeContainerId);
                        cmd.Parameters.AddWithValue("@qname", $"{qname}..ctor");
                        cmd.Parameters.AddWithValue("@kind", SymbolKinds.Constructor);
                        cmd.Parameters.AddWithValue("@vis", Visibilities.Public);
                        cmd.Parameters.AddWithValue("@prov", Provenances.BclReflected);
                        ctorSymId = Convert.ToInt64(cmd.ExecuteScalar());
                    }

                    using (var cmdFacet = conn.CreateCommand())
                    {
                        cmdFacet.Transaction = tx;
                        cmdFacet.CommandText = """
                        INSERT INTO cs_symbol_facets (symbol_id, member_kind)
                        VALUES (@sid, 'constructor')
                        ON CONFLICT(symbol_id) DO NOTHING;
                        """;
                        cmdFacet.Parameters.AddWithValue("@sid", ctorSymId);
                        cmdFacet.ExecuteNonQuery();
                    }

                    symbolCount++;

                    // Register primary callable
                    var primaryCtor = ctors[0];
                    var ctorSig = BuildMethodSignature(primaryCtor);
                    using (var cmd = conn.CreateCommand())
                    {
                        cmd.Transaction = tx;
                        cmd.CommandText = """
                        INSERT INTO callables (symbol_id, is_async, is_static, has_overloads, overload_count, return_type_expr, raw_signature, signature_source)
                        VALUES (@sid, 0, 0, @hasOverloads, @overloadCount, 'void', @rawSig, 'reflection')
                        ON CONFLICT(symbol_id) DO UPDATE SET raw_signature = excluded.raw_signature;
                        """;
                        cmd.Parameters.AddWithValue("@sid", ctorSymId);
                        cmd.Parameters.AddWithValue("@hasOverloads", ctors.Length > 1 ? 1 : 0);
                        cmd.Parameters.AddWithValue("@overloadCount", ctors.Length);
                        cmd.Parameters.AddWithValue("@rawSig", ctorSig);
                        cmd.ExecuteNonQuery();
                    }
                    callableCount++;

                    // Overloads and parameters
                    for (int i = 0; i < ctors.Length; i++)
                    {
                        var c = ctors[i];
                        long? overloadId = null;
                        if (ctors.Length > 1)
                        {
                            using var cmdOverload = conn.CreateCommand();
                            cmdOverload.Transaction = tx;
                            cmdOverload.CommandText = """
                            INSERT INTO callable_overloads (callable_symbol_id, overload_ordinal, return_type_expr, raw_signature)
                            VALUES (@cid, @ord, 'void', @rawSig)
                            ON CONFLICT(callable_symbol_id, overload_ordinal) DO UPDATE SET raw_signature = excluded.raw_signature
                            RETURNING overload_id;
                            """;
                            cmdOverload.Parameters.AddWithValue("@cid", ctorSymId);
                            cmdOverload.Parameters.AddWithValue("@ord", i + 1);
                            cmdOverload.Parameters.AddWithValue("@rawSig", BuildMethodSignature(c));
                            overloadId = Convert.ToInt64(cmdOverload.ExecuteScalar());
                        }

                        var parameters = c.GetParameters();
                        for (int pIdx = 0; pIdx < parameters.Length; pIdx++)
                        {
                            var p = parameters[pIdx];
                            using var cmdParam = conn.CreateCommand();
                            cmdParam.Transaction = tx;
                            cmdParam.CommandText = """
                            INSERT INTO parameters (callable_symbol_id, overload_id, ordinal, name, pass_kind, type_expr, type_source, is_optional)
                            VALUES (@cid, @oid, @ord, @name, @passKind, @typeExpr, 'reflection', @isOpt);
                            """;
                            cmdParam.Parameters.AddWithValue("@cid", ctorSymId);
                            cmdParam.Parameters.AddWithValue("@oid", (object?)overloadId ?? DBNull.Value);
                            cmdParam.Parameters.AddWithValue("@ord", pIdx);
                            cmdParam.Parameters.AddWithValue("@name", p.Name ?? $"p{pIdx}");
                            cmdParam.Parameters.AddWithValue("@passKind", DeterminePassKind(p));
                            cmdParam.Parameters.AddWithValue("@typeExpr", GetCleanTypeName(p.ParameterType));
                            cmdParam.Parameters.AddWithValue("@isOpt", p.IsOptional ? 1 : 0);
                            cmdParam.ExecuteNonQuery();
                        }
                    }
                }

                // Methods
                MethodInfo[] rawMethods = [];
                try { rawMethods = t.GetMethods(bindingFlags); } catch { }
                var methodsByName = rawMethods
                    .Where(m => !m.IsSpecialName)
                    .GroupBy(m => m.Name);

                foreach (var group in methodsByName)
                {
                    var methodName = group.Key;
                    var methodList = group.ToList();
                    var primaryMethod = methodList[0];

                    long methodSymId;
                    using (var cmd = conn.CreateCommand())
                    {
                        cmd.Transaction = tx;
                        cmd.CommandText = """
                        INSERT INTO symbols (container_id, origin_container_id, name, qualified_name, symbol_kind, visibility, provenance, is_hidden)
                        VALUES (@cid, @cid, @name, @qname, @kind, @vis, @prov, 0)
                        ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
                        RETURNING symbol_id;
                        """;
                        cmd.Parameters.AddWithValue("@cid", typeContainerId);
                        cmd.Parameters.AddWithValue("@name", methodName);
                        cmd.Parameters.AddWithValue("@qname", $"{qname}.{methodName}");
                        cmd.Parameters.AddWithValue("@kind", SymbolKinds.Method);
                        cmd.Parameters.AddWithValue("@vis", primaryMethod.IsPublic ? Visibilities.Public : Visibilities.Internal);
                        cmd.Parameters.AddWithValue("@prov", Provenances.BclReflected);
                        methodSymId = Convert.ToInt64(cmd.ExecuteScalar());
                    }

                    using (var cmdFacet = conn.CreateCommand())
                    {
                        cmdFacet.Transaction = tx;
                        cmdFacet.CommandText = """
                        INSERT INTO cs_symbol_facets (
                            symbol_id, member_kind, is_virtual, is_override, is_abstract, is_sealed
                        )
                        VALUES (@sid, 'method', @isVirt, @isOver, @isAbs, @isSealed)
                        ON CONFLICT(symbol_id) DO NOTHING;
                        """;
                        cmdFacet.Parameters.AddWithValue("@sid", methodSymId);
                        cmdFacet.Parameters.AddWithValue("@isVirt", primaryMethod.IsVirtual && !primaryMethod.IsFinal ? 1 : 0);
                        cmdFacet.Parameters.AddWithValue("@isOver", primaryMethod.GetBaseDefinition() != primaryMethod ? 1 : 0);
                        cmdFacet.Parameters.AddWithValue("@isAbs", primaryMethod.IsAbstract ? 1 : 0);
                        cmdFacet.Parameters.AddWithValue("@isSealed", primaryMethod.IsFinal ? 1 : 0);
                        cmdFacet.ExecuteNonQuery();
                    }

                    symbolCount++;

                    var retType = GetCleanTypeName(primaryMethod.ReturnType);
                    var rawSig = BuildMethodSignature(primaryMethod);
                    using (var cmd = conn.CreateCommand())
                    {
                        cmd.Transaction = tx;
                        cmd.CommandText = """
                        INSERT INTO callables (symbol_id, is_async, is_static, has_overloads, overload_count, return_type_expr, raw_signature, signature_source)
                        VALUES (@sid, 0, @isStatic, @hasOverloads, @overloadCount, @retType, @rawSig, 'reflection')
                        ON CONFLICT(symbol_id) DO UPDATE SET raw_signature = excluded.raw_signature;
                        """;
                        cmd.Parameters.AddWithValue("@sid", methodSymId);
                        cmd.Parameters.AddWithValue("@isStatic", primaryMethod.IsStatic ? 1 : 0);
                        cmd.Parameters.AddWithValue("@hasOverloads", methodList.Count > 1 ? 1 : 0);
                        cmd.Parameters.AddWithValue("@overloadCount", methodList.Count);
                        cmd.Parameters.AddWithValue("@retType", retType);
                        cmd.Parameters.AddWithValue("@rawSig", rawSig);
                        cmd.ExecuteNonQuery();
                    }
                    callableCount++;

                    for (int i = 0; i < methodList.Count; i++)
                    {
                        var m = methodList[i];
                        long? overloadId = null;
                        if (methodList.Count > 1)
                        {
                            using var cmdOverload = conn.CreateCommand();
                            cmdOverload.Transaction = tx;
                            cmdOverload.CommandText = """
                            INSERT INTO callable_overloads (callable_symbol_id, overload_ordinal, return_type_expr, raw_signature)
                            VALUES (@cid, @ord, @retType, @rawSig)
                            ON CONFLICT(callable_symbol_id, overload_ordinal) DO UPDATE SET raw_signature = excluded.raw_signature
                            RETURNING overload_id;
                            """;
                            cmdOverload.Parameters.AddWithValue("@cid", methodSymId);
                            cmdOverload.Parameters.AddWithValue("@ord", i + 1);
                            cmdOverload.Parameters.AddWithValue("@retType", GetCleanTypeName(m.ReturnType));
                            cmdOverload.Parameters.AddWithValue("@rawSig", BuildMethodSignature(m));
                            overloadId = Convert.ToInt64(cmdOverload.ExecuteScalar());
                        }

                        var parameters = m.GetParameters();
                        for (int pIdx = 0; pIdx < parameters.Length; pIdx++)
                        {
                            var p = parameters[pIdx];
                            using var cmdParam = conn.CreateCommand();
                            cmdParam.Transaction = tx;
                            cmdParam.CommandText = """
                            INSERT INTO parameters (callable_symbol_id, overload_id, ordinal, name, pass_kind, type_expr, type_source, is_optional)
                            VALUES (@cid, @oid, @ord, @name, @passKind, @typeExpr, 'reflection', @isOpt);
                            """;
                            cmdParam.Parameters.AddWithValue("@cid", methodSymId);
                            cmdParam.Parameters.AddWithValue("@oid", (object?)overloadId ?? DBNull.Value);
                            cmdParam.Parameters.AddWithValue("@ord", pIdx);
                            cmdParam.Parameters.AddWithValue("@name", p.Name ?? $"p{pIdx}");
                            cmdParam.Parameters.AddWithValue("@passKind", DeterminePassKind(p));
                            cmdParam.Parameters.AddWithValue("@typeExpr", GetCleanTypeName(p.ParameterType));
                            cmdParam.Parameters.AddWithValue("@isOpt", p.IsOptional ? 1 : 0);
                            cmdParam.ExecuteNonQuery();
                        }
                    }
                }

                // Properties
                PropertyInfo[] properties = [];
                try { properties = t.GetProperties(bindingFlags); } catch { }
                foreach (var p in properties)
                {
                    long propSymId;
                    using (var cmd = conn.CreateCommand())
                    {
                        cmd.Transaction = tx;
                        cmd.CommandText = """
                        INSERT INTO symbols (container_id, origin_container_id, name, qualified_name, symbol_kind, visibility, provenance, is_hidden)
                        VALUES (@cid, @cid, @name, @qname, @kind, @vis, @prov, 0)
                        ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
                        RETURNING symbol_id;
                        """;
                        cmd.Parameters.AddWithValue("@cid", typeContainerId);
                        cmd.Parameters.AddWithValue("@name", p.Name);
                        cmd.Parameters.AddWithValue("@qname", $"{qname}.{p.Name}");
                        cmd.Parameters.AddWithValue("@kind", SymbolKinds.Property);
                        cmd.Parameters.AddWithValue("@vis", Visibilities.Public);
                        cmd.Parameters.AddWithValue("@prov", Provenances.BclReflected);
                        propSymId = Convert.ToInt64(cmd.ExecuteScalar());
                    }

                    var propType = GetCleanTypeName(p.PropertyType);
                    var hasGetter = p.CanRead ? 1 : 0;
                    var hasSetter = p.CanWrite ? 1 : 0;
                    var accessMode = (hasGetter == 1 && hasSetter == 1) ? AccessModes.ReadWrite : AccessModes.ReadOnly;

                    using (var cmdState = conn.CreateCommand())
                    {
                        cmdState.Transaction = tx;
                        cmdState.CommandText = """
                        INSERT INTO state_members (symbol_id, declared_type_expr, runtime_type_name, is_constant, is_mutable, access_mode)
                        VALUES (@sid, @declType, @rtType, 0, @isMut, @accMode)
                        ON CONFLICT(symbol_id) DO NOTHING;
                        """;
                        cmdState.Parameters.AddWithValue("@sid", propSymId);
                        cmdState.Parameters.AddWithValue("@declType", propType);
                        cmdState.Parameters.AddWithValue("@rtType", p.PropertyType.Name);
                        cmdState.Parameters.AddWithValue("@isMut", hasSetter);
                        cmdState.Parameters.AddWithValue("@accMode", accessMode);
                        cmdState.ExecuteNonQuery();
                    }

                    using (var cmdFacet = conn.CreateCommand())
                    {
                        cmdFacet.Transaction = tx;
                        cmdFacet.CommandText = """
                        INSERT INTO cs_symbol_facets (symbol_id, member_kind, has_getter, has_setter)
                        VALUES (@sid, 'property', @hasGet, @hasSet)
                        ON CONFLICT(symbol_id) DO NOTHING;
                        """;
                        cmdFacet.Parameters.AddWithValue("@sid", propSymId);
                        cmdFacet.Parameters.AddWithValue("@hasGet", hasGetter);
                        cmdFacet.Parameters.AddWithValue("@hasSet", hasSetter);
                        cmdFacet.ExecuteNonQuery();
                    }

                    symbolCount++;
                }

                // Fields
                FieldInfo[] fields = [];
                try { fields = t.GetFields(bindingFlags); } catch { }
                foreach (var f in fields)
                {
                    long fSymId;
                    using (var cmd = conn.CreateCommand())
                    {
                        cmd.Transaction = tx;
                        cmd.CommandText = """
                        INSERT INTO symbols (container_id, origin_container_id, name, qualified_name, symbol_kind, visibility, provenance, is_hidden)
                        VALUES (@cid, @cid, @name, @qname, @kind, @vis, @prov, 0)
                        ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
                        RETURNING symbol_id;
                        """;
                        cmd.Parameters.AddWithValue("@cid", typeContainerId);
                        cmd.Parameters.AddWithValue("@name", f.Name);
                        cmd.Parameters.AddWithValue("@qname", $"{qname}.{f.Name}");
                        cmd.Parameters.AddWithValue("@kind", f.IsLiteral ? SymbolKinds.Constant : SymbolKinds.Field);
                        cmd.Parameters.AddWithValue("@vis", Visibilities.Public);
                        cmd.Parameters.AddWithValue("@prov", Provenances.BclReflected);
                        fSymId = Convert.ToInt64(cmd.ExecuteScalar());
                    }

                    var fType = GetCleanTypeName(f.FieldType);
                    using (var cmdState = conn.CreateCommand())
                    {
                        cmdState.Transaction = tx;
                        cmdState.CommandText = """
                        INSERT INTO state_members (symbol_id, declared_type_expr, runtime_type_name, is_constant, is_mutable, access_mode)
                        VALUES (@sid, @declType, @rtType, @isConst, @isMut, @accMode)
                        ON CONFLICT(symbol_id) DO NOTHING;
                        """;
                        cmdState.Parameters.AddWithValue("@sid", fSymId);
                        cmdState.Parameters.AddWithValue("@declType", fType);
                        cmdState.Parameters.AddWithValue("@rtType", f.FieldType.Name);
                        cmdState.Parameters.AddWithValue("@isConst", f.IsLiteral ? 1 : 0);
                        cmdState.Parameters.AddWithValue("@isMut", (f.IsLiteral || f.IsInitOnly) ? 0 : 1);
                        cmdState.Parameters.AddWithValue("@accMode", (f.IsLiteral || f.IsInitOnly) ? AccessModes.ReadOnly : AccessModes.ReadWrite);
                        cmdState.ExecuteNonQuery();
                    }

                    using (var cmdFacet = conn.CreateCommand())
                    {
                        cmdFacet.Transaction = tx;
                        cmdFacet.CommandText = """
                        INSERT INTO cs_symbol_facets (symbol_id, member_kind)
                        VALUES (@sid, 'field')
                        ON CONFLICT(symbol_id) DO NOTHING;
                        """;
                        cmdFacet.Parameters.AddWithValue("@sid", fSymId);
                        cmdFacet.ExecuteNonQuery();
                    }

                    symbolCount++;
                }
            }
            catch
            {
                // Silently skip obscure types with unresolvable dependencies
            }
        }

        tx.Commit();
        return (containerCount, symbolCount, callableCount);
    }

    private static string DetermineTypeKind(Type t)
    {
        if (t.IsInterface) return ContainerKinds.Interface;
        if (t.IsEnum) return ContainerKinds.Enum;
        if (typeof(Delegate).IsAssignableFrom(t)) return ContainerKinds.Delegate;
        if (t.IsValueType) return ContainerKinds.Struct;
        return ContainerKinds.Class;
    }

    private static string DeterminePassKind(ParameterInfo p)
    {
        if (p.GetCustomAttribute<ParamArrayAttribute>() != null) return PassKinds.Params;
        if (p.IsOut) return PassKinds.Out;
        if (p.ParameterType.IsByRef) return PassKinds.Ref;
        if (p.IsOptional) return PassKinds.Optional;
        return PassKinds.Value;
    }

    public static string GetCleanTypeName(Type t)
    {
        if (t.IsGenericParameter)
        {
            return t.Name;
        }

        if (t.IsByRef)
        {
            var el = t.GetElementType();
            return el != null ? $"ref {GetCleanTypeName(el)}" : t.Name;
        }

        if (t.IsPointer)
        {
            var el = t.GetElementType();
            return el != null ? $"{GetCleanTypeName(el)}*" : t.Name;
        }

        if (t.IsArray)
        {
            var el = t.GetElementType();
            var rank = t.GetArrayRank();
            var commas = new string(',', rank - 1);
            return el != null ? $"{GetCleanTypeName(el)}[{commas}]" : t.Name;
        }

        if (Stratum0Ambient.PrimitiveTypeAliases.TryGetValue(t.Name.ToLowerInvariant(), out var primitive) && primitive.TargetType == t.Name)
        {
            return t.Name.ToLowerInvariant();
        }

        if (t.IsGenericType)
        {
            try
            {
                var genericTypeDef = t.IsGenericTypeDefinition ? t : t.GetGenericTypeDefinition();
                var baseName = genericTypeDef.FullName?.Split('`')[0] ?? t.Name.Split('`')[0];
                var args = t.GetGenericArguments().Select(GetCleanTypeName);
                return $"{baseName}<{string.Join(", ", args)}>";
            }
            catch
            {
                return t.Name;
            }
        }

        return t.FullName ?? t.Name;
    }

    private static string BuildMethodSignature(MethodBase m)
    {
        try
        {
            var parameters = string.Join(", ", m.GetParameters().Select(p => $"{GetCleanTypeName(p.ParameterType)} {p.Name}"));
            if (m is MethodInfo mi)
            {
                return $"{GetCleanTypeName(mi.ReturnType)} {m.Name}({parameters})";
            }
            return $"{m.DeclaringType?.Name ?? "void"}({parameters})";
        }
        catch
        {
            return $"{m.Name}()";
        }
    }
}
