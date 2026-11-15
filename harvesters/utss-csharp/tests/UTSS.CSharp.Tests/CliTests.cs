using Xunit;

namespace UTSS.CSharp.Tests;

public class CliTests
{
    [Fact]
    public void TestCliHelpReturnsZero()
    {
        var result = Program.Main(["--help"]);
        Assert.Equal(0, result);
    }

    [Fact]
    public void TestCliHarvestReportAndQuery()
    {
        var testDb = $"test_cli_{Guid.NewGuid():N}.db";
        try
        {
            // 1. Harvest
            var harvestResult = Program.Main(["harvest", "--db", testDb, "--reset", "--demo-workspace", "--stratum0"]);
            Assert.Equal(0, harvestResult);
            Assert.True(File.Exists(testDb));

            // 2. Report
            var reportResult = Program.Main(["report", "--db", testDb]);
            Assert.Equal(0, reportResult);

            // 3. Query
            var queryResult = Program.Main(["query", "--db", testDb, "--ambient", "--workspace-symbols", "--facets"]);
            Assert.Equal(0, queryResult);
        }
        finally
        {
            if (File.Exists(testDb))
            {
                File.Delete(testDb);
            }
        }
    }
}
