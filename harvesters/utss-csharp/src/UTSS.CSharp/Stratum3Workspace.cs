using System.Text.Json;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.Data.Sqlite;

namespace UTSS.CSharp;

public static class Stratum3Workspace
{
    public static readonly Dictionary<string, string> EmbeddedDemoWorkspaceFiles = new()
    {
        ["CommerceEngine/Models/Order.cs"] = """
        namespace CommerceEngine.Models;

        public enum OrderStatus
        {
            Pending,
            Processing,
            Shipped,
            Delivered,
            Cancelled
        }

        public record Order(string OrderId, string CustomerId, decimal Subtotal, decimal TaxRate = 0.08m)
        {
            public OrderStatus Status { get; init; } = OrderStatus.Pending;
            public DateTime CreatedAt { get; init; } = DateTime.UtcNow;

            public decimal CalculateTotal() => Subtotal * (1 + TaxRate);
        }
        """,

        ["CommerceEngine/Models/Customer.cs"] = """
        namespace CommerceEngine.Models;

        public class Customer
        {
            private string _secretToken;

            public string CustomerId { get; }
            public string Name { get; set; }
            public string Email { get; set; }

            public Customer(string customerId, string name, string email, string secretToken = "")
            {
                CustomerId = customerId;
                Name = name;
                Email = email;
                _secretToken = secretToken;
            }

            public bool ValidateToken(string token) => _secretToken == token;
        }
        """,

        ["CommerceEngine/Services/IOrderService.cs"] = """
        namespace CommerceEngine.Services;

        using CommerceEngine.Models;

        public interface IOrderService
        {
            Task<Order> ProcessOrderAsync(string orderId, CancellationToken cancellationToken = default);
            IEnumerable<Order> StreamPendingOrders();
            bool CancelOrder(string orderId, string reason);
        }
        """,

        ["CommerceEngine/Services/OrderService.cs"] = """
        namespace CommerceEngine.Services;

        using CommerceEngine.Models;
        using CommerceEngine.Exceptions;

        public class OrderService : IOrderService
        {
            private readonly List<Order> _orders = new();

            public async Task<Order> ProcessOrderAsync(string orderId, CancellationToken cancellationToken = default)
            {
                await Task.Delay(10, cancellationToken);
                var order = _orders.FirstOrDefault(o => o.OrderId == orderId)
                    ?? throw new OrderNotFoundException($"Order {orderId} not found.");
                return order with { Status = OrderStatus.Processing };
            }

            public IEnumerable<Order> StreamPendingOrders()
            {
                foreach (var order in _orders)
                {
                    if (order.Status == OrderStatus.Pending)
                    {
                        yield return order;
                    }
                }
            }

            public bool CancelOrder(string orderId, string reason)
            {
                var idx = _orders.FindIndex(o => o.OrderId == orderId);
                if (idx >= 0)
                {
                    _orders[idx] = _orders[idx] with { Status = OrderStatus.Cancelled };
                    return true;
                }
                return false;
            }
        }
        """,

        ["CommerceEngine/Exceptions/OrderExceptions.cs"] = """
        namespace CommerceEngine.Exceptions;

        public class OrderNotFoundException : Exception
        {
            public OrderNotFoundException(string message) : base(message) { }
        }
        """,

        ["CommerceEngine/Common/Extensions.cs"] = """
        namespace CommerceEngine.Common;

        using CommerceEngine.Models;
        using ProjectOrder = CommerceEngine.Models.Order;

        public static class OrderExtensions
        {
            public static string FormatSummary(this ProjectOrder order)
            {
                return $"[Order {order.OrderId}] Customer: {order.CustomerId}, Total: {order.CalculateTotal():C}";
            }
        }
        """
    };

    public static void MaterializeDemoWorkspace(string directoryPath)
    {
        foreach (var (relPath, content) in EmbeddedDemoWorkspaceFiles)
        {
            var fullPath = Path.Combine(directoryPath, relPath);
            var dir = Path.GetDirectoryName(fullPath);
            if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir))
            {
                Directory.CreateDirectory(dir);
            }
            File.WriteAllText(fullPath, content);
        }
    }

    public static (int ContainerCount, int SymbolCount, int CallableCount) Harvest(
        SqliteConnection conn,
        string workspaceRoot,
        string distName = "<workspace>",
        string distVersion = "1.0.0")
    {
        var envId = Stratum0Ambient.EnsureEnvironment(conn);
        var distId = Stratum0Ambient.EnsureDistribution(
            conn, envId, Strata.Workspace, distName, distVersion, $"Workspace Source: {workspaceRoot}");

        var csFiles = Directory.EnumerateFiles(workspaceRoot, "*.cs", SearchOption.AllDirectories)
            .Where(f => !f.Contains($"{Path.DirectorySeparatorChar}bin{Path.DirectorySeparatorChar}") &&
                        !f.Contains($"{Path.DirectorySeparatorChar}obj{Path.DirectorySeparatorChar}") &&
                        !f.Contains($"{Path.DirectorySeparatorChar}.git{Path.DirectorySeparatorChar}"))
            .OrderBy(f => f)
            .ToList();

        return HarvestFiles(conn, distId, workspaceRoot, csFiles);
    }

    public static (int ContainerCount, int SymbolCount, int CallableCount) HarvestDemoWorkspace(
        SqliteConnection conn,
        string distName = "<workspace>",
        string distVersion = "1.0.0")
    {
        var envId = Stratum0Ambient.EnsureEnvironment(conn);
        var distId = Stratum0Ambient.EnsureDistribution(
            conn, envId, Strata.Workspace, distName, distVersion, "Embedded Demo Workspace (CommerceEngine)");

        return HarvestVirtualFiles(conn, distId, EmbeddedDemoWorkspaceFiles);
    }

    public static (int ContainerCount, int SymbolCount, int CallableCount) HarvestFiles(
        SqliteConnection conn,
        long distId,
        string workspaceRoot,
        IEnumerable<string> filePaths)
    {
        var virtualFiles = new Dictionary<string, string>();
        foreach (var fp in filePaths)
        {
            var rel = Path.GetRelativePath(workspaceRoot, fp);
            virtualFiles[rel] = File.ReadAllText(fp);
        }
        return HarvestVirtualFiles(conn, distId, virtualFiles);
    }

    public static (int ContainerCount, int SymbolCount, int CallableCount) HarvestVirtualFiles(
        SqliteConnection conn,
        long distId,
        IDictionary<string, string> files)
    {
        int totalContainers = 0;
        int totalSymbols = 0;
        int totalCallables = 0;

        using var tx = conn.BeginTransaction();

        foreach (var (relPath, code) in files)
        {
            var syntaxTree = CSharpSyntaxTree.ParseText(code, path: relPath);
            var root = syntaxTree.GetCompilationUnitRoot();

            var walker = new RoslynWorkspaceWalker(conn, tx, distId, relPath, syntaxTree);
            walker.Visit(root);

            totalContainers += walker.ContainerCount;
            totalSymbols += walker.SymbolCount;
            totalCallables += walker.CallableCount;
        }

        tx.Commit();
        return (totalContainers, totalSymbols, totalCallables);
    }

    private class RoslynWorkspaceWalker : CSharpSyntaxWalker
    {
        private readonly SqliteConnection _conn;
        private readonly SqliteTransaction _tx;
        private readonly long _distId;
        private readonly string _filePath;
        private readonly SyntaxTree _tree;

        private readonly Stack<long> _containerStack = new();
        private readonly Stack<string> _qnameStack = new();

        public int ContainerCount { get; private set; }
        public int SymbolCount { get; private set; }
        public int CallableCount { get; private set; }

        public RoslynWorkspaceWalker(
            SqliteConnection conn,
            SqliteTransaction tx,
            long distId,
            string filePath,
            SyntaxTree tree)
        {
            _conn = conn;
            _tx = tx;
            _distId = distId;
            _filePath = filePath;
            _tree = tree;
        }

        private (int startLine, int startCol, int endLine, int endCol) GetCoordinates(SyntaxNode node)
        {
            var span = _tree.GetLineSpan(node.Span);
            return (
                span.StartLinePosition.Line + 1,
                span.StartLinePosition.Character,
                span.EndLinePosition.Line + 1,
                span.EndLinePosition.Character
            );
        }

        public override void VisitUsingDirective(UsingDirectiveSyntax node)
        {
            // using Alias = Target; or using Namespace; or global using ...
            var currentContainerId = _containerStack.Count > 0 ? _containerStack.Peek() : (long?)null;
            if (currentContainerId.HasValue)
            {
                var isGlobal = node.GlobalKeyword.IsKind(SyntaxKind.GlobalKeyword);
                if (node.Alias != null && node.Name != null)
                {
                    var aliasName = node.Alias.Name.Identifier.Text;
                    var targetName = node.Name.ToString();
                    var parts = targetName.Split('.');
                    var targetSym = parts.Last();
                    var targetMod = parts.Length > 1 ? string.Join(".", parts.Take(parts.Length - 1)) : targetName;

                    using var cmd = _conn.CreateCommand();
                    cmd.Transaction = _tx;
                    cmd.CommandText = """
                    INSERT INTO symbol_aliases (source_container_id, exposed_name, target_module_name, target_symbol_name, alias_kind, is_in_dunder_all)
                    VALUES (@srcId, @expName, @tgtMod, @tgtSym, @kind, 0)
                    ON CONFLICT(source_container_id, exposed_name) DO UPDATE SET target_module_name = excluded.target_module_name;
                    """;
                    cmd.Parameters.AddWithValue("@srcId", currentContainerId.Value);
                    cmd.Parameters.AddWithValue("@expName", aliasName);
                    cmd.Parameters.AddWithValue("@tgtMod", targetMod);
                    cmd.Parameters.AddWithValue("@tgtSym", targetSym);
                    cmd.Parameters.AddWithValue("@kind", isGlobal ? "global_using_alias" : "using_alias");
                    cmd.ExecuteNonQuery();
                }
            }

            base.VisitUsingDirective(node);
        }

        public override void VisitFileScopedNamespaceDeclaration(FileScopedNamespaceDeclarationSyntax node)
        {
            HandleNamespace(node.Name.ToString(), node, () => base.VisitFileScopedNamespaceDeclaration(node));
        }

        public override void VisitNamespaceDeclaration(NamespaceDeclarationSyntax node)
        {
            HandleNamespace(node.Name.ToString(), node, () => base.VisitNamespaceDeclaration(node));
        }

        private void HandleNamespace(string nsName, SyntaxNode node, Action visitChildren)
        {
            var coords = GetCoordinates(node);
            long parentId = _containerStack.Count > 0 ? _containerStack.Peek() : 0;

            long nsId;
            using (var cmd = _conn.CreateCommand())
            {
                cmd.Transaction = _tx;
                cmd.CommandText = """
                INSERT INTO containers (
                    dist_id, parent_container_id, container_kind, qualified_name, short_name,
                    requires_import, visibility, is_hidden, physical_path,
                    start_line, start_col, end_line, end_col
                )
                VALUES (
                    @distId, @parentId, @kind, @qname, @sname,
                    1, 'public', 0, @path,
                    @sLine, @sCol, @eLine, @eCol
                )
                ON CONFLICT(dist_id, qualified_name) DO UPDATE SET
                    start_line = excluded.start_line,
                    end_line = excluded.end_line
                RETURNING container_id;
                """;
                cmd.Parameters.AddWithValue("@distId", _distId);
                cmd.Parameters.AddWithValue("@parentId", parentId > 0 ? (object)parentId : DBNull.Value);
                cmd.Parameters.AddWithValue("@kind", ContainerKinds.Namespace);
                cmd.Parameters.AddWithValue("@qname", nsName);
                cmd.Parameters.AddWithValue("@sname", nsName.Split('.').Last());
                cmd.Parameters.AddWithValue("@path", _filePath);
                cmd.Parameters.AddWithValue("@sLine", coords.startLine);
                cmd.Parameters.AddWithValue("@sCol", coords.startCol);
                cmd.Parameters.AddWithValue("@eLine", coords.endLine);
                cmd.Parameters.AddWithValue("@eCol", coords.endCol);
                nsId = Convert.ToInt64(cmd.ExecuteScalar());
            }

            using (var cmdFacet = _conn.CreateCommand())
            {
                cmdFacet.Transaction = _tx;
                cmdFacet.CommandText = """
                INSERT INTO cs_container_facets (container_id, type_kind)
                VALUES (@cid, 'namespace')
                ON CONFLICT(container_id) DO NOTHING;
                """;
                cmdFacet.Parameters.AddWithValue("@cid", nsId);
                cmdFacet.ExecuteNonQuery();
            }

            ContainerCount++;

            _containerStack.Push(nsId);
            _qnameStack.Push(nsName);

            visitChildren();

            _qnameStack.Pop();
            _containerStack.Pop();
        }

        public override void VisitClassDeclaration(ClassDeclarationSyntax node)
        {
            HandleTypeDeclaration(
                node.Identifier.Text,
                ContainerKinds.Class,
                node.Modifiers,
                node.BaseList,
                node.TypeParameterList,
                node.AttributeLists,
                node,
                () => base.VisitClassDeclaration(node)
            );
        }

        public override void VisitRecordDeclaration(RecordDeclarationSyntax node)
        {
            var isStruct = node.ClassOrStructKeyword.IsKind(SyntaxKind.StructKeyword);
            var kind = isStruct ? ContainerKinds.RecordStruct : ContainerKinds.RecordClass;

            HandleTypeDeclaration(
                node.Identifier.Text,
                kind,
                node.Modifiers,
                node.BaseList,
                node.TypeParameterList,
                node.AttributeLists,
                node,
                () =>
                {
                    // Primary constructor parameters on records
                    if (node.ParameterList != null && _containerStack.Count > 0)
                    {
                        var recordCid = _containerStack.Peek();
                        var recordQName = _qnameStack.Peek();
                        HandlePrimaryConstructor(recordCid, recordQName, node.ParameterList);
                    }
                    base.VisitRecordDeclaration(node);
                }
            );
        }

        public override void VisitStructDeclaration(StructDeclarationSyntax node)
        {
            HandleTypeDeclaration(
                node.Identifier.Text,
                ContainerKinds.Struct,
                node.Modifiers,
                node.BaseList,
                node.TypeParameterList,
                node.AttributeLists,
                node,
                () => base.VisitStructDeclaration(node)
            );
        }

        public override void VisitInterfaceDeclaration(InterfaceDeclarationSyntax node)
        {
            HandleTypeDeclaration(
                node.Identifier.Text,
                ContainerKinds.Interface,
                node.Modifiers,
                node.BaseList,
                node.TypeParameterList,
                node.AttributeLists,
                node,
                () => base.VisitInterfaceDeclaration(node)
            );
        }

        public override void VisitEnumDeclaration(EnumDeclarationSyntax node)
        {
            HandleTypeDeclaration(
                node.Identifier.Text,
                ContainerKinds.Enum,
                node.Modifiers,
                node.BaseList,
                null,
                node.AttributeLists,
                node,
                () =>
                {
                    // Enum members
                    var enumCid = _containerStack.Peek();
                    var enumQName = _qnameStack.Peek();
                    foreach (var member in node.Members)
                    {
                        var mCoords = GetCoordinates(member);
                        long mSymId;
                        using (var cmd = _conn.CreateCommand())
                        {
                            cmd.Transaction = _tx;
                            cmd.CommandText = """
                            INSERT INTO symbols (
                                container_id, origin_container_id, name, qualified_name,
                                symbol_kind, visibility, provenance, is_hidden,
                                start_line, start_col, end_line, end_col
                            )
                            VALUES (
                                @cid, @cid, @name, @qname,
                                @kind, 'public', 'ast_defined', 0,
                                @sLine, @sCol, @eLine, @eCol
                            )
                            ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
                            RETURNING symbol_id;
                            """;
                            cmd.Parameters.AddWithValue("@cid", enumCid);
                            cmd.Parameters.AddWithValue("@name", member.Identifier.Text);
                            cmd.Parameters.AddWithValue("@qname", $"{enumQName}.{member.Identifier.Text}");
                            cmd.Parameters.AddWithValue("@kind", SymbolKinds.EnumMember);
                            cmd.Parameters.AddWithValue("@sLine", mCoords.startLine);
                            cmd.Parameters.AddWithValue("@sCol", mCoords.startCol);
                            cmd.Parameters.AddWithValue("@eLine", mCoords.endLine);
                            cmd.Parameters.AddWithValue("@eCol", mCoords.endCol);
                            mSymId = Convert.ToInt64(cmd.ExecuteScalar());
                        }

                        using (var cmdFacet = _conn.CreateCommand())
                        {
                            cmdFacet.Transaction = _tx;
                            cmdFacet.CommandText = """
                            INSERT INTO cs_symbol_facets (symbol_id, member_kind)
                            VALUES (@sid, 'enum_member')
                            ON CONFLICT(symbol_id) DO NOTHING;
                            """;
                            cmdFacet.Parameters.AddWithValue("@sid", mSymId);
                            cmdFacet.ExecuteNonQuery();
                        }
                        SymbolCount++;
                    }
                    base.VisitEnumDeclaration(node);
                }
            );
        }

        private void HandleTypeDeclaration(
            string name,
            string kind,
            SyntaxTokenList modifiers,
            BaseListSyntax? baseList,
            TypeParameterListSyntax? typeParams,
            SyntaxList<AttributeListSyntax> attributes,
            SyntaxNode node,
            Action visitChildren)
        {
            var coords = GetCoordinates(node);
            long parentId = _containerStack.Count > 0 ? _containerStack.Peek() : 0;
            var parentQName = _qnameStack.Count > 0 ? _qnameStack.Peek() : "";
            var qname = string.IsNullOrEmpty(parentQName) ? name : $"{parentQName}.{name}";

            var isSealed = modifiers.Any(SyntaxKind.SealedKeyword) ? 1 : 0;
            var isAbstract = modifiers.Any(SyntaxKind.AbstractKeyword) ? 1 : 0;
            var isStatic = modifiers.Any(SyntaxKind.StaticKeyword) ? 1 : 0;
            var isReadonly = modifiers.Any(SyntaxKind.ReadOnlyKeyword) ? 1 : 0;
            var isRef = modifiers.Any(SyntaxKind.RefKeyword) ? 1 : 0;

            var visibility = DetermineVisibility(modifiers);
            var isHidden = (visibility == Visibilities.Private || visibility == Visibilities.Internal) ? 1 : 0;

            string? baseType = null;
            var ifaces = new List<string>();
            if (baseList != null)
            {
                foreach (var baseTypeSyntax in baseList.Types)
                {
                    var typeName = baseTypeSyntax.Type.ToString();
                    if (typeName.StartsWith("I") && typeName.Length > 1 && char.IsUpper(typeName[1]))
                    {
                        ifaces.Add(typeName);
                    }
                    else if (baseType == null && kind != ContainerKinds.Interface)
                    {
                        baseType = typeName;
                    }
                    else
                    {
                        ifaces.Add(typeName);
                    }
                }
            }

            var genParams = typeParams?.Parameters.Select(p => new { name = p.Identifier.Text }).ToArray();
            var genParamsJson = genParams != null && genParams.Length > 0 ? JsonSerializer.Serialize(genParams) : null;
            var ifacesJson = ifaces.Count > 0 ? JsonSerializer.Serialize(ifaces) : null;

            var attrNames = attributes.SelectMany(a => a.Attributes).Select(a => a.Name.ToString()).ToArray();
            var attrsJson = attrNames.Length > 0 ? JsonSerializer.Serialize(attrNames) : null;

            long containerId;
            using (var cmd = _conn.CreateCommand())
            {
                cmd.Transaction = _tx;
                cmd.CommandText = """
                INSERT INTO containers (
                    dist_id, parent_container_id, container_kind, qualified_name, short_name,
                    requires_import, visibility, is_hidden, physical_path,
                    start_line, start_col, end_line, end_col
                )
                VALUES (
                    @distId, @parentId, @kind, @qname, @sname,
                    1, @vis, @isHidden, @path,
                    @sLine, @sCol, @eLine, @eCol
                )
                ON CONFLICT(dist_id, qualified_name) DO UPDATE SET
                    start_line = excluded.start_line,
                    end_line = excluded.end_line
                RETURNING container_id;
                """;
                cmd.Parameters.AddWithValue("@distId", _distId);
                cmd.Parameters.AddWithValue("@parentId", parentId > 0 ? (object)parentId : DBNull.Value);
                cmd.Parameters.AddWithValue("@kind", kind);
                cmd.Parameters.AddWithValue("@qname", qname);
                cmd.Parameters.AddWithValue("@sname", name);
                cmd.Parameters.AddWithValue("@vis", visibility);
                cmd.Parameters.AddWithValue("@isHidden", isHidden);
                cmd.Parameters.AddWithValue("@path", _filePath);
                cmd.Parameters.AddWithValue("@sLine", coords.startLine);
                cmd.Parameters.AddWithValue("@sCol", coords.startCol);
                cmd.Parameters.AddWithValue("@eLine", coords.endLine);
                cmd.Parameters.AddWithValue("@eCol", coords.endCol);
                containerId = Convert.ToInt64(cmd.ExecuteScalar());
            }

            using (var cmdFacet = _conn.CreateCommand())
            {
                cmdFacet.Transaction = _tx;
                cmdFacet.CommandText = """
                INSERT INTO cs_container_facets (
                    container_id, type_kind, is_sealed, is_abstract, is_static,
                    is_readonly_struct, is_ref_struct, base_type_qname,
                    implemented_interfaces_json, generic_type_parameters_json, attributes_json
                )
                VALUES (
                    @cid, @kind, @isSealed, @isAbstract, @isStatic,
                    @isReadonly, @isRef, @baseType,
                    @ifaces, @genParams, @attrs
                )
                ON CONFLICT(container_id) DO UPDATE SET
                    type_kind = excluded.type_kind,
                    is_sealed = excluded.is_sealed,
                    is_abstract = excluded.is_abstract,
                    is_static = excluded.is_static;
                """;
                cmdFacet.Parameters.AddWithValue("@cid", containerId);
                cmdFacet.Parameters.AddWithValue("@kind", kind);
                cmdFacet.Parameters.AddWithValue("@isSealed", isSealed);
                cmdFacet.Parameters.AddWithValue("@isAbstract", isAbstract);
                cmdFacet.Parameters.AddWithValue("@isStatic", isStatic);
                cmdFacet.Parameters.AddWithValue("@isReadonly", isReadonly);
                cmdFacet.Parameters.AddWithValue("@isRef", isRef);
                cmdFacet.Parameters.AddWithValue("@baseType", (object?)baseType ?? DBNull.Value);
                cmdFacet.Parameters.AddWithValue("@ifaces", (object?)ifacesJson ?? DBNull.Value);
                cmdFacet.Parameters.AddWithValue("@genParams", (object?)genParamsJson ?? DBNull.Value);
                cmdFacet.Parameters.AddWithValue("@attrs", (object?)attrsJson ?? DBNull.Value);
                cmdFacet.ExecuteNonQuery();
            }

            ContainerCount++;

            _containerStack.Push(containerId);
            _qnameStack.Push(qname);

            visitChildren();

            _qnameStack.Pop();
            _containerStack.Pop();
        }

        private void HandlePrimaryConstructor(long containerId, string containerQName, ParameterListSyntax parameterList)
        {
            var coords = GetCoordinates(parameterList);
            long ctorSymId;
            using (var cmd = _conn.CreateCommand())
            {
                cmd.Transaction = _tx;
                cmd.CommandText = """
                INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name,
                    symbol_kind, visibility, provenance, is_hidden,
                    start_line, start_col, end_line, end_col
                )
                VALUES (
                    @cid, @cid, '.ctor', @qname,
                    'constructor', 'public', 'ast_defined', 0,
                    @sLine, @sCol, @eLine, @eCol
                )
                ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
                RETURNING symbol_id;
                """;
                cmd.Parameters.AddWithValue("@cid", containerId);
                cmd.Parameters.AddWithValue("@qname", $"{containerQName}..ctor");
                cmd.Parameters.AddWithValue("@sLine", coords.startLine);
                cmd.Parameters.AddWithValue("@sCol", coords.startCol);
                cmd.Parameters.AddWithValue("@eLine", coords.endLine);
                cmd.Parameters.AddWithValue("@eCol", coords.endCol);
                ctorSymId = Convert.ToInt64(cmd.ExecuteScalar());
            }

            using (var cmdFacet = _conn.CreateCommand())
            {
                cmdFacet.Transaction = _tx;
                cmdFacet.CommandText = """
                INSERT INTO cs_symbol_facets (symbol_id, member_kind)
                VALUES (@sid, 'constructor')
                ON CONFLICT(symbol_id) DO NOTHING;
                """;
                cmdFacet.Parameters.AddWithValue("@sid", ctorSymId);
                cmdFacet.ExecuteNonQuery();
            }
            SymbolCount++;

            var rawSig = parameterList.ToString();
            using (var cmdCall = _conn.CreateCommand())
            {
                cmdCall.Transaction = _tx;
                cmdCall.CommandText = """
                INSERT INTO callables (symbol_id, is_async, is_static, has_overloads, overload_count, return_type_expr, raw_signature, signature_source)
                VALUES (@sid, 0, 0, 0, 1, 'void', @rawSig, 'roslyn_ast')
                ON CONFLICT(symbol_id) DO UPDATE SET raw_signature = excluded.raw_signature;
                """;
                cmdCall.Parameters.AddWithValue("@sid", ctorSymId);
                cmdCall.Parameters.AddWithValue("@rawSig", rawSig);
                cmdCall.ExecuteNonQuery();
            }
            CallableCount++;

            for (int i = 0; i < parameterList.Parameters.Count; i++)
            {
                var p = parameterList.Parameters[i];
                var pType = p.Type?.ToString() ?? "object";
                var pName = p.Identifier.Text;
                var defExpr = p.Default?.Value.ToString();

                using var cmdParam = _conn.CreateCommand();
                cmdParam.Transaction = _tx;
                cmdParam.CommandText = """
                INSERT INTO parameters (callable_symbol_id, ordinal, name, pass_kind, type_expr, type_source, default_expr, is_optional)
                VALUES (@cid, @ord, @name, @passKind, @typeExpr, 'roslyn_ast', @defExpr, @isOpt);
                """;
                cmdParam.Parameters.AddWithValue("@cid", ctorSymId);
                cmdParam.Parameters.AddWithValue("@ord", i);
                cmdParam.Parameters.AddWithValue("@name", pName);
                cmdParam.Parameters.AddWithValue("@passKind", p.Modifiers.Any(SyntaxKind.RefKeyword) ? PassKinds.Ref :
                                                             p.Modifiers.Any(SyntaxKind.OutKeyword) ? PassKinds.Out :
                                                             p.Modifiers.Any(SyntaxKind.InKeyword) ? PassKinds.In :
                                                             p.Modifiers.Any(SyntaxKind.ParamsKeyword) ? PassKinds.Params : PassKinds.Value);
                cmdParam.Parameters.AddWithValue("@typeExpr", pType);
                cmdParam.Parameters.AddWithValue("@defExpr", (object?)defExpr ?? DBNull.Value);
                cmdParam.Parameters.AddWithValue("@isOpt", defExpr != null ? 1 : 0);
                cmdParam.ExecuteNonQuery();

                // Also synthesize property symbol on record for primary constructor parameter!
                long propSymId;
                using (var cmdProp = _conn.CreateCommand())
                {
                    cmdProp.Transaction = _tx;
                    cmdProp.CommandText = """
                    INSERT INTO symbols (
                        container_id, origin_container_id, name, qualified_name,
                        symbol_kind, visibility, provenance, is_hidden,
                        start_line, start_col, end_line, end_col
                    )
                    VALUES (
                        @cid, @cid, @name, @qname,
                        'property', 'public', 'ast_defined', 0,
                        @sLine, @sCol, @eLine, @eCol
                    )
                    ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
                    RETURNING symbol_id;
                    """;
                    cmdProp.Parameters.AddWithValue("@cid", containerId);
                    cmdProp.Parameters.AddWithValue("@name", pName);
                    cmdProp.Parameters.AddWithValue("@qname", $"{containerQName}.{pName}");
                    cmdProp.Parameters.AddWithValue("@sLine", coords.startLine);
                    cmdProp.Parameters.AddWithValue("@sCol", coords.startCol);
                    cmdProp.Parameters.AddWithValue("@eLine", coords.endLine);
                    cmdProp.Parameters.AddWithValue("@eCol", coords.endCol);
                    propSymId = Convert.ToInt64(cmdProp.ExecuteScalar());
                }

                using (var cmdState = _conn.CreateCommand())
                {
                    cmdState.Transaction = _tx;
                    cmdState.CommandText = """
                    INSERT INTO state_members (symbol_id, declared_type_expr, runtime_type_name, is_constant, is_mutable, access_mode)
                    VALUES (@sid, @typeExpr, @typeExpr, 0, 0, 'init_only')
                    ON CONFLICT(symbol_id) DO NOTHING;
                    """;
                    cmdState.Parameters.AddWithValue("@sid", propSymId);
                    cmdState.Parameters.AddWithValue("@typeExpr", pType);
                    cmdState.ExecuteNonQuery();
                }

                using (var cmdFacet = _conn.CreateCommand())
                {
                    cmdFacet.Transaction = _tx;
                    cmdFacet.CommandText = """
                    INSERT INTO cs_symbol_facets (symbol_id, member_kind, has_getter, has_setter, is_init_only)
                    VALUES (@sid, 'property', 1, 1, 1)
                    ON CONFLICT(symbol_id) DO NOTHING;
                    """;
                    cmdFacet.Parameters.AddWithValue("@sid", propSymId);
                    cmdFacet.ExecuteNonQuery();
                }
                SymbolCount++;
            }
        }

        public override void VisitConstructorDeclaration(ConstructorDeclarationSyntax node)
        {
            if (_containerStack.Count == 0) return;
            var containerId = _containerStack.Peek();
            var containerQName = _qnameStack.Peek();
            var coords = GetCoordinates(node);

            var visibility = DetermineVisibility(node.Modifiers);
            var isHidden = (visibility == Visibilities.Private || visibility == Visibilities.Internal) ? 1 : 0;

            long ctorSymId;
            using (var cmd = _conn.CreateCommand())
            {
                cmd.Transaction = _tx;
                cmd.CommandText = """
                INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name,
                    symbol_kind, visibility, provenance, is_hidden,
                    start_line, start_col, end_line, end_col
                )
                VALUES (
                    @cid, @cid, '.ctor', @qname,
                    'constructor', @vis, 'ast_defined', @isHidden,
                    @sLine, @sCol, @eLine, @eCol
                )
                ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
                RETURNING symbol_id;
                """;
                cmd.Parameters.AddWithValue("@cid", containerId);
                cmd.Parameters.AddWithValue("@qname", $"{containerQName}..ctor");
                cmd.Parameters.AddWithValue("@vis", visibility);
                cmd.Parameters.AddWithValue("@isHidden", isHidden);
                cmd.Parameters.AddWithValue("@sLine", coords.startLine);
                cmd.Parameters.AddWithValue("@sCol", coords.startCol);
                cmd.Parameters.AddWithValue("@eLine", coords.endLine);
                cmd.Parameters.AddWithValue("@eCol", coords.endCol);
                ctorSymId = Convert.ToInt64(cmd.ExecuteScalar());
            }

            using (var cmdFacet = _conn.CreateCommand())
            {
                cmdFacet.Transaction = _tx;
                cmdFacet.CommandText = """
                INSERT INTO cs_symbol_facets (symbol_id, member_kind)
                VALUES (@sid, 'constructor')
                ON CONFLICT(symbol_id) DO NOTHING;
                """;
                cmdFacet.Parameters.AddWithValue("@sid", ctorSymId);
                cmdFacet.ExecuteNonQuery();
            }
            SymbolCount++;

            var rawSig = $"{node.Identifier.Text}{node.ParameterList}";
            using (var cmdCall = _conn.CreateCommand())
            {
                cmdCall.Transaction = _tx;
                cmdCall.CommandText = """
                INSERT INTO callables (symbol_id, is_async, is_static, has_overloads, overload_count, return_type_expr, raw_signature, signature_source)
                VALUES (@sid, 0, 0, 0, 1, 'void', @rawSig, 'roslyn_ast')
                ON CONFLICT(symbol_id) DO UPDATE SET raw_signature = excluded.raw_signature;
                """;
                cmdCall.Parameters.AddWithValue("@sid", ctorSymId);
                cmdCall.Parameters.AddWithValue("@rawSig", rawSig);
                cmdCall.ExecuteNonQuery();
            }
            CallableCount++;

            for (int i = 0; i < node.ParameterList.Parameters.Count; i++)
            {
                var p = node.ParameterList.Parameters[i];
                var pType = p.Type?.ToString() ?? "object";
                var pName = p.Identifier.Text;
                var defExpr = p.Default?.Value.ToString();

                using var cmdParam = _conn.CreateCommand();
                cmdParam.Transaction = _tx;
                cmdParam.CommandText = """
                INSERT INTO parameters (callable_symbol_id, ordinal, name, pass_kind, type_expr, type_source, default_expr, is_optional)
                VALUES (@cid, @ord, @name, @passKind, @typeExpr, 'roslyn_ast', @defExpr, @isOpt);
                """;
                cmdParam.Parameters.AddWithValue("@cid", ctorSymId);
                cmdParam.Parameters.AddWithValue("@ord", i);
                cmdParam.Parameters.AddWithValue("@name", pName);
                cmdParam.Parameters.AddWithValue("@passKind", p.Modifiers.Any(SyntaxKind.RefKeyword) ? PassKinds.Ref :
                                                             p.Modifiers.Any(SyntaxKind.OutKeyword) ? PassKinds.Out :
                                                             p.Modifiers.Any(SyntaxKind.InKeyword) ? PassKinds.In :
                                                             p.Modifiers.Any(SyntaxKind.ParamsKeyword) ? PassKinds.Params : PassKinds.Value);
                cmdParam.Parameters.AddWithValue("@typeExpr", pType);
                cmdParam.Parameters.AddWithValue("@defExpr", (object?)defExpr ?? DBNull.Value);
                cmdParam.Parameters.AddWithValue("@isOpt", defExpr != null ? 1 : 0);
                cmdParam.ExecuteNonQuery();
            }

            base.VisitConstructorDeclaration(node);
        }

        public override void VisitMethodDeclaration(MethodDeclarationSyntax node)
        {
            if (_containerStack.Count == 0) return;
            var containerId = _containerStack.Peek();
            var containerQName = _qnameStack.Peek();
            var coords = GetCoordinates(node);

            var methodName = node.Identifier.Text;
            var visibility = DetermineVisibility(node.Modifiers);
            var isHidden = (visibility == Visibilities.Private || visibility == Visibilities.Internal) ? 1 : 0;

            var isAsync = node.Modifiers.Any(SyntaxKind.AsyncKeyword) ? 1 : 0;
            var isStatic = node.Modifiers.Any(SyntaxKind.StaticKeyword) ? 1 : 0;
            var isVirtual = node.Modifiers.Any(SyntaxKind.VirtualKeyword) ? 1 : 0;
            var isOverride = node.Modifiers.Any(SyntaxKind.OverrideKeyword) ? 1 : 0;
            var isAbstract = node.Modifiers.Any(SyntaxKind.AbstractKeyword) ? 1 : 0;
            var isSealed = node.Modifiers.Any(SyntaxKind.SealedKeyword) ? 1 : 0;

            // Generator detection in C#: yield return or yield break inside method body
            var isGenerator = node.DescendantNodes().OfType<YieldStatementSyntax>().Any() ? 1 : 0;

            // Extension method detection: static method whose first parameter has 'this' modifier
            var isExtension = (isStatic == 1 &&
                               node.ParameterList.Parameters.Count > 0 &&
                               node.ParameterList.Parameters[0].Modifiers.Any(SyntaxKind.ThisKeyword)) ? 1 : 0;

            long methodSymId;
            using (var cmd = _conn.CreateCommand())
            {
                cmd.Transaction = _tx;
                cmd.CommandText = """
                INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name,
                    symbol_kind, visibility, provenance, is_hidden,
                    start_line, start_col, end_line, end_col
                )
                VALUES (
                    @cid, @cid, @name, @qname,
                    'method', @vis, 'ast_defined', @isHidden,
                    @sLine, @sCol, @eLine, @eCol
                )
                ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
                RETURNING symbol_id;
                """;
                cmd.Parameters.AddWithValue("@cid", containerId);
                cmd.Parameters.AddWithValue("@name", methodName);
                cmd.Parameters.AddWithValue("@qname", $"{containerQName}.{methodName}");
                cmd.Parameters.AddWithValue("@vis", visibility);
                cmd.Parameters.AddWithValue("@isHidden", isHidden);
                cmd.Parameters.AddWithValue("@sLine", coords.startLine);
                cmd.Parameters.AddWithValue("@sCol", coords.startCol);
                cmd.Parameters.AddWithValue("@eLine", coords.endLine);
                cmd.Parameters.AddWithValue("@eCol", coords.endCol);
                methodSymId = Convert.ToInt64(cmd.ExecuteScalar());
            }

            var retType = node.ReturnType.ToString();
            var rawSig = $"{retType} {methodName}{node.TypeParameterList}{node.ParameterList}";

            using (var cmdFacet = _conn.CreateCommand())
            {
                cmdFacet.Transaction = _tx;
                cmdFacet.CommandText = """
                INSERT INTO cs_symbol_facets (
                    symbol_id, member_kind, is_virtual, is_override, is_abstract,
                    is_sealed, is_async, is_extension_method
                )
                VALUES (
                    @sid, 'method', @isVirt, @isOver, @isAbs,
                    @isSealed, @isAsync, @isExt
                )
                ON CONFLICT(symbol_id) DO NOTHING;
                """;
                cmdFacet.Parameters.AddWithValue("@sid", methodSymId);
                cmdFacet.Parameters.AddWithValue("@isVirt", isVirtual);
                cmdFacet.Parameters.AddWithValue("@isOver", isOverride);
                cmdFacet.Parameters.AddWithValue("@isAbs", isAbstract);
                cmdFacet.Parameters.AddWithValue("@isSealed", isSealed);
                cmdFacet.Parameters.AddWithValue("@isAsync", isAsync);
                cmdFacet.Parameters.AddWithValue("@isExt", isExtension);
                cmdFacet.ExecuteNonQuery();
            }
            SymbolCount++;

            using (var cmdCall = _conn.CreateCommand())
            {
                cmdCall.Transaction = _tx;
                cmdCall.CommandText = """
                INSERT INTO callables (symbol_id, is_async, is_generator, is_static, has_overloads, overload_count, return_type_expr, raw_signature, signature_source)
                VALUES (@sid, @isAsync, @isGen, @isStatic, 0, 1, @retType, @rawSig, 'roslyn_ast')
                ON CONFLICT(symbol_id) DO UPDATE SET raw_signature = excluded.raw_signature;
                """;
                cmdCall.Parameters.AddWithValue("@sid", methodSymId);
                cmdCall.Parameters.AddWithValue("@isAsync", isAsync);
                cmdCall.Parameters.AddWithValue("@isGen", isGenerator);
                cmdCall.Parameters.AddWithValue("@isStatic", isStatic);
                cmdCall.Parameters.AddWithValue("@retType", retType);
                cmdCall.Parameters.AddWithValue("@rawSig", rawSig);
                cmdCall.ExecuteNonQuery();
            }
            CallableCount++;

            for (int i = 0; i < node.ParameterList.Parameters.Count; i++)
            {
                var p = node.ParameterList.Parameters[i];
                var pType = p.Type?.ToString() ?? "object";
                var pName = p.Identifier.Text;
                var defExpr = p.Default?.Value.ToString();

                using var cmdParam = _conn.CreateCommand();
                cmdParam.Transaction = _tx;
                cmdParam.CommandText = """
                INSERT INTO parameters (callable_symbol_id, ordinal, name, pass_kind, type_expr, type_source, default_expr, is_optional)
                VALUES (@cid, @ord, @name, @passKind, @typeExpr, 'roslyn_ast', @defExpr, @isOpt);
                """;
                cmdParam.Parameters.AddWithValue("@cid", methodSymId);
                cmdParam.Parameters.AddWithValue("@ord", i);
                cmdParam.Parameters.AddWithValue("@name", pName);
                cmdParam.Parameters.AddWithValue("@passKind", p.Modifiers.Any(SyntaxKind.RefKeyword) ? PassKinds.Ref :
                                                             p.Modifiers.Any(SyntaxKind.OutKeyword) ? PassKinds.Out :
                                                             p.Modifiers.Any(SyntaxKind.InKeyword) ? PassKinds.In :
                                                             p.Modifiers.Any(SyntaxKind.ParamsKeyword) ? PassKinds.Params : PassKinds.Value);
                cmdParam.Parameters.AddWithValue("@typeExpr", pType);
                cmdParam.Parameters.AddWithValue("@defExpr", (object?)defExpr ?? DBNull.Value);
                cmdParam.Parameters.AddWithValue("@isOpt", defExpr != null ? 1 : 0);
                cmdParam.ExecuteNonQuery();
            }

            base.VisitMethodDeclaration(node);
        }

        public override void VisitPropertyDeclaration(PropertyDeclarationSyntax node)
        {
            if (_containerStack.Count == 0) return;
            var containerId = _containerStack.Peek();
            var containerQName = _qnameStack.Peek();
            var coords = GetCoordinates(node);

            var propName = node.Identifier.Text;
            var visibility = DetermineVisibility(node.Modifiers);
            var isHidden = (visibility == Visibilities.Private || visibility == Visibilities.Internal) ? 1 : 0;
            var propType = node.Type.ToString();

            bool hasGet = false;
            bool hasSet = false;
            bool isInit = false;

            if (node.AccessorList != null)
            {
                hasGet = node.AccessorList.Accessors.Any(a => a.IsKind(SyntaxKind.GetAccessorDeclaration));
                hasSet = node.AccessorList.Accessors.Any(a => a.IsKind(SyntaxKind.SetAccessorDeclaration));
                isInit = node.AccessorList.Accessors.Any(a => a.IsKind(SyntaxKind.InitAccessorDeclaration));
            }
            else if (node.ExpressionBody != null)
            {
                hasGet = true;
            }

            var accessMode = (hasSet || isInit)
                ? (isInit ? AccessModes.InitOnly : AccessModes.ReadWrite)
                : AccessModes.ReadOnly;

            long propSymId;
            using (var cmd = _conn.CreateCommand())
            {
                cmd.Transaction = _tx;
                cmd.CommandText = """
                INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name,
                    symbol_kind, visibility, provenance, is_hidden,
                    start_line, start_col, end_line, end_col
                )
                VALUES (
                    @cid, @cid, @name, @qname,
                    'property', @vis, 'ast_defined', @isHidden,
                    @sLine, @sCol, @eLine, @eCol
                )
                ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
                RETURNING symbol_id;
                """;
                cmd.Parameters.AddWithValue("@cid", containerId);
                cmd.Parameters.AddWithValue("@name", propName);
                cmd.Parameters.AddWithValue("@qname", $"{containerQName}.{propName}");
                cmd.Parameters.AddWithValue("@vis", visibility);
                cmd.Parameters.AddWithValue("@isHidden", isHidden);
                cmd.Parameters.AddWithValue("@sLine", coords.startLine);
                cmd.Parameters.AddWithValue("@sCol", coords.startCol);
                cmd.Parameters.AddWithValue("@eLine", coords.endLine);
                cmd.Parameters.AddWithValue("@eCol", coords.endCol);
                propSymId = Convert.ToInt64(cmd.ExecuteScalar());
            }

            using (var cmdState = _conn.CreateCommand())
            {
                cmdState.Transaction = _tx;
                cmdState.CommandText = """
                INSERT INTO state_members (symbol_id, declared_type_expr, runtime_type_name, is_constant, is_mutable, access_mode)
                VALUES (@sid, @declType, @declType, 0, @isMut, @accMode)
                ON CONFLICT(symbol_id) DO NOTHING;
                """;
                cmdState.Parameters.AddWithValue("@sid", propSymId);
                cmdState.Parameters.AddWithValue("@declType", propType);
                cmdState.Parameters.AddWithValue("@isMut", (hasSet || isInit) ? 1 : 0);
                cmdState.Parameters.AddWithValue("@accMode", accessMode);
                cmdState.ExecuteNonQuery();
            }

            using (var cmdFacet = _conn.CreateCommand())
            {
                cmdFacet.Transaction = _tx;
                cmdFacet.CommandText = """
                INSERT INTO cs_symbol_facets (symbol_id, member_kind, has_getter, has_setter, is_init_only)
                VALUES (@sid, 'property', @hasGet, @hasSet, @isInit)
                ON CONFLICT(symbol_id) DO NOTHING;
                """;
                cmdFacet.Parameters.AddWithValue("@sid", propSymId);
                cmdFacet.Parameters.AddWithValue("@hasGet", hasGet ? 1 : 0);
                cmdFacet.Parameters.AddWithValue("@hasSet", (hasSet || isInit) ? 1 : 0);
                cmdFacet.Parameters.AddWithValue("@isInit", isInit ? 1 : 0);
                cmdFacet.ExecuteNonQuery();
            }
            SymbolCount++;

            base.VisitPropertyDeclaration(node);
        }

        public override void VisitFieldDeclaration(FieldDeclarationSyntax node)
        {
            if (_containerStack.Count == 0) return;
            var containerId = _containerStack.Peek();
            var containerQName = _qnameStack.Peek();
            var coords = GetCoordinates(node);

            var visibility = DetermineVisibility(node.Modifiers);
            var isHidden = (visibility == Visibilities.Private || visibility == Visibilities.Internal) ? 1 : 0;
            var fieldType = node.Declaration.Type.ToString();
            var isConst = node.Modifiers.Any(SyntaxKind.ConstKeyword) ? 1 : 0;
            var isReadonly = node.Modifiers.Any(SyntaxKind.ReadOnlyKeyword) ? 1 : 0;

            foreach (var variable in node.Declaration.Variables)
            {
                var fieldName = variable.Identifier.Text;
                long fieldSymId;
                using (var cmd = _conn.CreateCommand())
                {
                    cmd.Transaction = _tx;
                    cmd.CommandText = """
                    INSERT INTO symbols (
                        container_id, origin_container_id, name, qualified_name,
                        symbol_kind, visibility, provenance, is_hidden,
                        start_line, start_col, end_line, end_col
                    )
                    VALUES (
                        @cid, @cid, @name, @qname,
                        @kind, @vis, 'ast_defined', @isHidden,
                        @sLine, @sCol, @eLine, @eCol
                    )
                    ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
                    RETURNING symbol_id;
                    """;
                    cmd.Parameters.AddWithValue("@cid", containerId);
                    cmd.Parameters.AddWithValue("@name", fieldName);
                    cmd.Parameters.AddWithValue("@qname", $"{containerQName}.{fieldName}");
                    cmd.Parameters.AddWithValue("@kind", isConst == 1 ? SymbolKinds.Constant : SymbolKinds.Field);
                    cmd.Parameters.AddWithValue("@vis", visibility);
                    cmd.Parameters.AddWithValue("@isHidden", isHidden);
                    cmd.Parameters.AddWithValue("@sLine", coords.startLine);
                    cmd.Parameters.AddWithValue("@sCol", coords.startCol);
                    cmd.Parameters.AddWithValue("@eLine", coords.endLine);
                    cmd.Parameters.AddWithValue("@eCol", coords.endCol);
                    fieldSymId = Convert.ToInt64(cmd.ExecuteScalar());
                }

                using (var cmdState = _conn.CreateCommand())
                {
                    cmdState.Transaction = _tx;
                    cmdState.CommandText = """
                    INSERT INTO state_members (symbol_id, declared_type_expr, runtime_type_name, is_constant, is_mutable, access_mode)
                    VALUES (@sid, @declType, @declType, @isConst, @isMut, @accMode)
                    ON CONFLICT(symbol_id) DO NOTHING;
                    """;
                    cmdState.Parameters.AddWithValue("@sid", fieldSymId);
                    cmdState.Parameters.AddWithValue("@declType", fieldType);
                    cmdState.Parameters.AddWithValue("@isConst", isConst);
                    cmdState.Parameters.AddWithValue("@isMut", (isConst == 0 && isReadonly == 0) ? 1 : 0);
                    cmdState.Parameters.AddWithValue("@accMode", (isConst == 1 || isReadonly == 1) ? AccessModes.ReadOnly : AccessModes.ReadWrite);
                    cmdState.ExecuteNonQuery();
                }

                using (var cmdFacet = _conn.CreateCommand())
                {
                    cmdFacet.Transaction = _tx;
                    cmdFacet.CommandText = """
                    INSERT INTO cs_symbol_facets (symbol_id, member_kind)
                    VALUES (@sid, 'field')
                    ON CONFLICT(symbol_id) DO NOTHING;
                    """;
                    cmdFacet.Parameters.AddWithValue("@sid", fieldSymId);
                    cmdFacet.ExecuteNonQuery();
                }
                SymbolCount++;
            }

            base.VisitFieldDeclaration(node);
        }

        private static string DetermineVisibility(SyntaxTokenList modifiers)
        {
            if (modifiers.Any(SyntaxKind.PublicKeyword)) return Visibilities.Public;
            if (modifiers.Any(SyntaxKind.ProtectedKeyword) && modifiers.Any(SyntaxKind.InternalKeyword)) return Visibilities.ProtectedInternal;
            if (modifiers.Any(SyntaxKind.PrivateKeyword) && modifiers.Any(SyntaxKind.ProtectedKeyword)) return Visibilities.PrivateProtected;
            if (modifiers.Any(SyntaxKind.ProtectedKeyword)) return Visibilities.Protected;
            if (modifiers.Any(SyntaxKind.InternalKeyword)) return Visibilities.Internal;
            if (modifiers.Any(SyntaxKind.PrivateKeyword)) return Visibilities.Private;
            return Visibilities.Internal; // Default in C# for top-level / nested without explicit modifier
        }
    }
}
