using Microsoft.Data.Sqlite;
using Xunit;

namespace UTSS.CSharp.Tests;

public class Stratum1Tests
{
    [Fact]
    public void TestStratum1HarvestPopulatesBclTypes()
    {
        using var conn = new SqliteConnection("Data Source=:memory:");
        conn.Open();

        Schema.InitDb(conn);
        Stratum0Ambient.Harvest(conn);

        var (containerCount, symbolCount, callableCount) = Stratum1Runtime.Harvest(
            conn,
            [typeof(string), typeof(List<int>), typeof(Math)]);

        Assert.True(containerCount >= 3);
        Assert.True(symbolCount >= 20);
        Assert.True(callableCount >= 10);

        // Check string methods with overloads (e.g. Substring, IndexOf, Replace)
        using (var cmd = conn.CreateCommand())
        {
            cmd.CommandText = """
            SELECT s.name, cal.has_overloads, cal.overload_count
            FROM symbols s
            JOIN containers c ON s.container_id = c.container_id
            JOIN callables cal ON cal.symbol_id = s.symbol_id
            WHERE c.qualified_name = 'string' AND s.name = 'Substring';
            """;
            using var reader = cmd.ExecuteReader();
            Assert.True(reader.Read(), "Expected Substring method on string");
            var hasOverloads = reader.GetInt32(1);
            var overloadCount = reader.GetInt32(2);
            Assert.Equal(1, hasOverloads);
            Assert.True(overloadCount >= 2);
        }

        // Check parameters of Math.Max
        using (var cmd = conn.CreateCommand())
        {
            cmd.CommandText = """
            SELECT COUNT(*)
            FROM parameters p
            JOIN callables cal ON p.callable_symbol_id = cal.symbol_id
            JOIN symbols s ON s.symbol_id = cal.symbol_id
            JOIN containers c ON s.container_id = c.container_id
            WHERE c.qualified_name = 'System.Math' AND s.name = 'Max';
            """;
            var paramCount = Convert.ToInt32(cmd.ExecuteScalar());
            Assert.True(paramCount >= 2);
        }

        // Check C# container facets
        using (var cmd = conn.CreateCommand())
        {
            cmd.CommandText = """
            SELECT cf.type_kind, cf.is_sealed, cf.is_static
            FROM cs_container_facets cf
            JOIN containers c ON cf.container_id = c.container_id
            WHERE c.qualified_name = 'System.Math';
            """;
            using var reader = cmd.ExecuteReader();
            Assert.True(reader.Read());
            Assert.Equal("class", reader.GetString(0));
            Assert.Equal(1, reader.GetInt32(1)); // sealed
            Assert.Equal(1, reader.GetInt32(2)); // static (abstract & sealed in CLR)
        }
    }
}
