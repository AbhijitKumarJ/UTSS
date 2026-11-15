using Microsoft.Data.Sqlite;
using Xunit;

namespace UTSS.CSharp.Tests;

public class Stratum3Tests
{
    [Fact]
    public void TestStratum3HarvestDemoWorkspace()
    {
        using var conn = new SqliteConnection("Data Source=:memory:");
        conn.Open();

        Schema.InitDb(conn);
        Stratum0Ambient.Harvest(conn);

        var (containerCount, symbolCount, callableCount) = Stratum3Workspace.HarvestDemoWorkspace(conn);

        Assert.True(containerCount >= 10, $"Expected >= 10 containers, got {containerCount}");
        Assert.True(symbolCount >= 20, $"Expected >= 20 symbols, got {symbolCount}");
        Assert.True(callableCount >= 10, $"Expected >= 10 callables, got {callableCount}");

        // 1. Verify Record Container & Facet
        using (var cmd = conn.CreateCommand())
        {
            cmd.CommandText = """
            SELECT c.container_kind, cf.type_kind
            FROM containers c
            JOIN cs_container_facets cf ON c.container_id = cf.container_id
            WHERE c.qualified_name = 'CommerceEngine.Models.Order';
            """;
            using var reader = cmd.ExecuteReader();
            Assert.True(reader.Read(), "Expected CommerceEngine.Models.Order");
            Assert.Equal("record", reader.GetString(0));
            Assert.Equal("record", reader.GetString(1));
        }

        // 2. Verify Primary Constructor Parameter Synthesis on Record
        using (var cmd = conn.CreateCommand())
        {
            cmd.CommandText = """
            SELECT s.symbol_kind, sm.access_mode, sf.is_init_only
            FROM symbols s
            JOIN containers c ON s.container_id = c.container_id
            LEFT JOIN state_members sm ON sm.symbol_id = s.symbol_id
            LEFT JOIN cs_symbol_facets sf ON sf.symbol_id = s.symbol_id
            WHERE c.qualified_name = 'CommerceEngine.Models.Order' AND s.name = 'Subtotal';
            """;
            using var reader = cmd.ExecuteReader();
            Assert.True(reader.Read(), "Expected Subtotal property on Order");
            Assert.Equal("property", reader.GetString(0));
            Assert.Equal("init_only", reader.GetString(1));
            Assert.Equal(1, reader.GetInt32(2));
        }

        // 3. Verify Async Method & Generator Detection
        using (var cmd = conn.CreateCommand())
        {
            cmd.CommandText = """
            SELECT s.name, cal.is_async, cal.is_generator
            FROM symbols s
            JOIN containers c ON s.container_id = c.container_id
            JOIN callables cal ON cal.symbol_id = s.symbol_id
            WHERE c.qualified_name = 'CommerceEngine.Services.OrderService'
            ORDER BY s.name;
            """;
            using var reader = cmd.ExecuteReader();
            var methods = new Dictionary<string, (int IsAsync, int IsGen)>();
            while (reader.Read())
            {
                methods[reader.GetString(0)] = (reader.GetInt32(1), reader.GetInt32(2));
            }

            Assert.Contains("ProcessOrderAsync", methods);
            Assert.Equal(1, methods["ProcessOrderAsync"].IsAsync);
            Assert.Equal(0, methods["ProcessOrderAsync"].IsGen);

            Assert.Contains("StreamPendingOrders", methods);
            Assert.Equal(0, methods["StreamPendingOrders"].IsAsync);
            Assert.Equal(1, methods["StreamPendingOrders"].IsGen);
        }

        // 4. Verify Extension Method Detection
        using (var cmd = conn.CreateCommand())
        {
            cmd.CommandText = """
            SELECT sf.is_extension_method
            FROM symbols s
            JOIN containers c ON s.container_id = c.container_id
            JOIN cs_symbol_facets sf ON sf.symbol_id = s.symbol_id
            WHERE c.qualified_name = 'CommerceEngine.Common.OrderExtensions' AND s.name = 'FormatSummary';
            """;
            var isExt = Convert.ToInt32(cmd.ExecuteScalar());
            Assert.Equal(1, isExt);
        }

        // 5. Verify Using Alias (using ProjectOrder = CommerceEngine.Models.Order;)
        using (var cmd = conn.CreateCommand())
        {
            cmd.CommandText = """
            SELECT exposed_name, target_module_name, target_symbol_name, alias_kind
            FROM symbol_aliases
            WHERE exposed_name = 'ProjectOrder';
            """;
            using var reader = cmd.ExecuteReader();
            Assert.True(reader.Read(), "Expected using alias ProjectOrder");
            Assert.Equal("CommerceEngine.Models", reader.GetString(1));
            Assert.Equal("Order", reader.GetString(2));
            Assert.Equal("using_alias", reader.GetString(3));
        }

        // 6. Verify Exact AST Coordinates
        using (var cmd = conn.CreateCommand())
        {
            cmd.CommandText = """
            SELECT start_line, start_col, end_line, end_col
            FROM symbols
            WHERE qualified_name = 'CommerceEngine.Models.Order.CalculateTotal';
            """;
            using var reader = cmd.ExecuteReader();
            Assert.True(reader.Read());
            var sLine = reader.GetInt32(0);
            var sCol = reader.GetInt32(1);
            var eLine = reader.GetInt32(2);
            var eCol = reader.GetInt32(3);
            Assert.True(sLine > 0);
            Assert.True(eLine >= sLine);
        }
    }
}
