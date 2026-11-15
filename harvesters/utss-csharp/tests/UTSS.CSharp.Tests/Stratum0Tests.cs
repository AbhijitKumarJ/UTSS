using Microsoft.Data.Sqlite;
using Xunit;

namespace UTSS.CSharp.Tests;

public class Stratum0Tests
{
    [Fact]
    public void TestStratum0HarvestPopulatesAmbientScope()
    {
        using var conn = new SqliteConnection("Data Source=:memory:");
        conn.Open();

        Schema.InitDb(conn);

        var (kwCount, aliasCount, usingCount) = Stratum0Ambient.Harvest(conn);

        Assert.True(kwCount >= 100, $"Expected >= 100 keywords, got {kwCount}");
        Assert.True(aliasCount >= 15, $"Expected >= 15 aliases, got {aliasCount}");
        Assert.True(usingCount >= 5, $"Expected >= 5 global usings, got {usingCount}");

        // Check environment record
        using (var cmd = conn.CreateCommand())
        {
            cmd.CommandText = "SELECT language, runtime_name FROM environments LIMIT 1;";
            using var reader = cmd.ExecuteReader();
            Assert.True(reader.Read());
            Assert.Equal("csharp", reader.GetString(0));
            Assert.Equal(".NET", reader.GetString(1));
        }

        // Check primitive aliases in symbol_aliases
        using (var cmd = conn.CreateCommand())
        {
            cmd.CommandText = "SELECT target_module_name, target_symbol_name FROM symbol_aliases WHERE exposed_name = 'int';";
            using var reader = cmd.ExecuteReader();
            Assert.True(reader.Read());
            Assert.Equal("System", reader.GetString(0));
            Assert.Equal("Int32", reader.GetString(1));
        }

        // Check C# container facet for ambient scope
        using (var cmd = conn.CreateCommand())
        {
            cmd.CommandText = """
            SELECT cf.type_kind
            FROM cs_container_facets cf
            JOIN containers c ON cf.container_id = c.container_id
            WHERE c.qualified_name = '<ambient>';
            """;
            var typeKind = cmd.ExecuteScalar()?.ToString();
            Assert.Equal("namespace", typeKind);
        }
    }
}
