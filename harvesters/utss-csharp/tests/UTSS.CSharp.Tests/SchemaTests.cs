using Microsoft.Data.Sqlite;
using Xunit;

namespace UTSS.CSharp.Tests;

public class SchemaTests
{
    [Fact]
    public void TestInitDbCreatesAllExpectedTables()
    {
        using var conn = new SqliteConnection("Data Source=:memory:");
        conn.Open();

        Schema.InitDb(conn);

        var existingTables = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        using var cmd = conn.CreateCommand();
        cmd.CommandText = "SELECT name FROM sqlite_master WHERE type='table';";
        using var reader = cmd.ExecuteReader();
        while (reader.Read())
        {
            existingTables.Add(reader.GetString(0));
        }

        foreach (var expectedTable in Schema.ExpectedTables)
        {
            Assert.Contains(expectedTable, existingTables);
        }
    }

    [Fact]
    public void TestInitDbResetDropsAndRecreates()
    {
        using var conn = new SqliteConnection("Data Source=:memory:");
        conn.Open();

        Schema.InitDb(conn);

        // Insert a dummy environment
        using (var cmd = conn.CreateCommand())
        {
            cmd.CommandText = """
            INSERT INTO environments (language, runtime_name, language_version, version_major, version_minor, version_micro, platform_triplet, sys_platform, executable_path)
            VALUES ('csharp', '.NET', '10.0', 10, 0, 0, 'Linux-x86_64', 'linux', '/usr/bin/dotnet');
            """;
            cmd.ExecuteNonQuery();
        }

        // Verify row exists
        using (var checkCmd = conn.CreateCommand())
        {
            checkCmd.CommandText = "SELECT COUNT(*) FROM environments;";
            Assert.Equal(1L, (long)checkCmd.ExecuteScalar()!);
        }

        // Re-init with reset=true
        Schema.InitDb(conn, reset: true);

        // Verify table was dropped and re-created empty
        using (var checkCmd = conn.CreateCommand())
        {
            checkCmd.CommandText = "SELECT COUNT(*) FROM environments;";
            Assert.Equal(0L, (long)checkCmd.ExecuteScalar()!);
        }
    }
}
