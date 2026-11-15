using Microsoft.Data.Sqlite;

namespace UTSS.CSharp;

public static class Program
{
    public static int Main(string[] args)
    {
        if (args.Length == 0 || args[0] is "-h" or "--help" or "help")
        {
            PrintHelp();
            return 0;
        }

        var subcommand = args[0].ToLowerInvariant();
        var subArgs = args.Skip(1).ToArray();

        try
        {
            return subcommand switch
            {
                "harvest" => HandleHarvest(subArgs),
                "report" => HandleReport(subArgs),
                "query" => HandleQuery(subArgs),
                _ => PrintError($"Unknown subcommand: {subcommand}")
            };
        }
        catch (Exception ex)
        {
            Console.ForegroundColor = ConsoleColor.Red;
            Console.Error.WriteLine($"\n[ERROR] {ex.Message}");
            Console.Error.WriteLine(ex.StackTrace);
            Console.ResetColor();
            return 1;
        }
    }

    private static void PrintHelp()
    {
        Console.WriteLine("""
        UTSS C# - Universal Type & Symbol System (C# / .NET Cataloger)

        Usage:
          utss-cs <command> [options]

        Commands:
          harvest          Extract type and symbol metadata into the dual-layer SQLite catalog.
          report           Generate a diagnostic summary across universal & C# facet tables.
          query            Query specific strata and facet tables.

        Harvest Options:
          --db <path>           Path to the SQLite database (default: catalog_cs.db)
          --reset               Reset/drop existing tables before harvesting
          --all                 Harvest Stratum 0, 1 (recommended BCL), and Demo Workspace
          --stratum0            Harvest Stratum 0 (Ambient C# keywords & primitive aliases)
          --stratum1            Harvest Stratum 1 (Runtime BCL assemblies via reflection)
          --bcl-recommended     Harvest curated Tier-1 BCL types (System, Linq, Collections, IO, Json, etc.)
          --bcl-full            Harvest full CoreCLR BCL runtime assemblies (all public exported types)
          --demo-workspace      Harvest Stratum 3 embedded demo workspace (CommerceEngine)
          --workspace <dir>     Harvest Stratum 3 from a directory of .cs files

        Query Options:
          --db <path>           Path to the SQLite database (default: catalog_cs.db)
          --ambient             Display Stratum 0 ambient keywords, aliases, and literals
          --bcl                 Display Stratum 1 BCL types and methods
          --bcl-summary         Display Stratum 1 BCL containers breakdown by type kind
          --bcl-overloads       Display Stratum 1 top polymorphic method overloads
          --bcl-generics        Display Stratum 1 generic types and interfaces
          --workspace-symbols   Display Stratum 3 workspace symbols and AST spans
          --facets              Display C# Container and Symbol facets
        """);
    }

    private static int PrintError(string msg)
    {
        Console.ForegroundColor = ConsoleColor.Red;
        Console.Error.WriteLine($"Error: {msg}");
        Console.ResetColor();
        Console.WriteLine("Use --help for usage information.");
        return 1;
    }

    private static int HandleHarvest(string[] args)
    {
        string dbPath = "catalog_cs.db";
        bool reset = false;
        bool doStratum0 = false;
        bool doStratum1 = false;
        bool bclFull = false;
        bool bclRecommended = false;
        bool doDemoWorkspace = false;
        string? workspacePath = null;

        for (int i = 0; i < args.Length; i++)
        {
            switch (args[i])
            {
                case "--db" when i + 1 < args.Length:
                    dbPath = args[++i];
                    break;
                case "--reset":
                    reset = true;
                    break;
                case "--all":
                    doStratum0 = true;
                    doStratum1 = true;
                    bclRecommended = true;
                    doDemoWorkspace = true;
                    break;
                case "--stratum0":
                    doStratum0 = true;
                    break;
                case "--stratum1":
                    doStratum1 = true;
                    break;
                case "--bcl-recommended":
                    doStratum1 = true;
                    bclRecommended = true;
                    break;
                case "--bcl-full":
                    doStratum1 = true;
                    bclFull = true;
                    break;
                case "--demo-workspace":
                    doDemoWorkspace = true;
                    break;
                case "--workspace" when i + 1 < args.Length:
                    workspacePath = args[++i];
                    break;
            }
        }

        if (!doStratum0 && !doStratum1 && !doDemoWorkspace && workspacePath == null)
        {
            // Default to --all
            doStratum0 = true;
            doStratum1 = true;
            bclRecommended = true;
            doDemoWorkspace = true;
        }

        Console.WriteLine($"[UTSS.CSharp] Initializing SQLite catalog: {dbPath}");
        var connStr = new SqliteConnectionStringBuilder { DataSource = dbPath }.ToString();
        using var conn = new SqliteConnection(connStr);
        conn.Open();

        Schema.InitDb(conn, reset: reset);

        if (doStratum0)
        {
            Console.WriteLine("[UTSS.CSharp] Harvesting Stratum 0 (Ambient Scope)...");
            var (kwCount, aliasCount, usingCount) = Stratum0Ambient.Harvest(conn);
            Console.WriteLine($"  -> Harvested {kwCount} keywords, {aliasCount} primitive aliases, {usingCount} global/static usings & literals.");
        }

        if (doStratum1)
        {
            if (bclFull)
            {
                Console.WriteLine("[UTSS.CSharp] Harvesting Stratum 1 (Full CoreCLR BCL Runtime Assemblies)...");
                var allTypes = Stratum1Runtime.GetFullBclTypes();
                Console.WriteLine($"  -> Discovered {allTypes.Count} public exported types across core assemblies.");
                var (cCount, sCount, callCount) = Stratum1Runtime.Harvest(conn, allTypes);
                Console.WriteLine($"  -> Harvested {cCount} containers, {sCount} symbols, {callCount} callables.");
            }
            else if (bclRecommended)
            {
                Console.WriteLine("[UTSS.CSharp] Harvesting Stratum 1 (Curated Tier-1 BCL Standard Libraries)...");
                var (cCount, sCount, callCount) = Stratum1Runtime.Harvest(conn, Stratum1Runtime.RecommendedBclTypes);
                Console.WriteLine($"  -> Harvested {cCount} containers, {sCount} symbols, {callCount} callables.");
            }
            else
            {
                Console.WriteLine("[UTSS.CSharp] Harvesting Stratum 1 (Runtime BCL Sample)...");
                var (cCount, sCount, callCount) = Stratum1Runtime.Harvest(conn);
                Console.WriteLine($"  -> Harvested {cCount} containers, {sCount} symbols, {callCount} callables.");
            }
        }

        if (doDemoWorkspace)
        {
            Console.WriteLine("[UTSS.CSharp] Harvesting Stratum 3 (Embedded Demo Workspace: CommerceEngine)...");
            var (cCount, sCount, callCount) = Stratum3Workspace.HarvestDemoWorkspace(conn);
            Console.WriteLine($"  -> Harvested {cCount} containers, {sCount} symbols, {callCount} callables.");
        }

        if (!string.IsNullOrEmpty(workspacePath))
        {
            Console.WriteLine($"[UTSS.CSharp] Harvesting Stratum 3 (Workspace: {workspacePath})...");
            var (cCount, sCount, callCount) = Stratum3Workspace.Harvest(conn, workspacePath);
            Console.WriteLine($"  -> Harvested {cCount} containers, {sCount} symbols, {callCount} callables.");
        }

        Console.WriteLine("[UTSS.CSharp] Harvesting complete!");
        PrintReportSummary(conn);
        return 0;
    }

    private static int HandleReport(string[] args)
    {
        string dbPath = "catalog_cs.db";
        for (int i = 0; i < args.Length; i++)
        {
            if (args[i] == "--db" && i + 1 < args.Length)
            {
                dbPath = args[++i];
            }
        }

        if (!File.Exists(dbPath))
        {
            return PrintError($"Database file not found: {dbPath}");
        }

        using var conn = new SqliteConnection($"Data Source={dbPath}");
        conn.Open();
        PrintReportSummary(conn);
        return 0;
    }

    private static void PrintReportSummary(SqliteConnection conn)
    {
        var summary = Queries.GetSpectrumSummary(conn);
        var dists = Queries.QueryDistributions(conn);

        Console.WriteLine("\n========================================================");
        Console.WriteLine("          UTSS C# SPECTRUM CATALOG REPORT               ");
        Console.WriteLine("========================================================");
        Console.WriteLine($"{"Table",-25} | {"Count",10}");
        Console.WriteLine(new string('-', 38));
        foreach (var (tbl, count) in summary)
        {
            Console.WriteLine($"{tbl,-25} | {count,10}");
        }

        Console.WriteLine("\n--------------------------------------------------------");
        Console.WriteLine("DISTRIBUTIONS & STRATA:");
        Console.WriteLine("--------------------------------------------------------");
        Console.WriteLine($"{"Stratum",-8} | {"Distribution",-22} | {"Version",-10} | {"Containers",10}");
        Console.WriteLine(new string('-', 58));
        foreach (var d in dists)
        {
            var stratum = d["stratum"]?.ToString() ?? "";
            var name = d["dist_name"]?.ToString() ?? "";
            var ver = d["dist_version"]?.ToString() ?? "";
            var cCount = d["container_count"]?.ToString() ?? "0";
            Console.WriteLine($"{stratum,-8} | {name,-22} | {ver,-10} | {cCount,10}");
        }
        Console.WriteLine("========================================================\n");
    }

    private static int HandleQuery(string[] args)
    {
        string dbPath = "catalog_cs.db";
        bool showAmbient = false;
        bool showBcl = false;
        bool showBclSummary = false;
        bool showBclOverloads = false;
        bool showBclGenerics = false;
        bool showWorkspace = false;
        bool showFacets = false;

        for (int i = 0; i < args.Length; i++)
        {
            switch (args[i])
            {
                case "--db" when i + 1 < args.Length:
                    dbPath = args[++i];
                    break;
                case "--ambient":
                    showAmbient = true;
                    break;
                case "--bcl":
                    showBcl = true;
                    break;
                case "--bcl-summary":
                    showBclSummary = true;
                    break;
                case "--bcl-overloads":
                    showBclOverloads = true;
                    break;
                case "--bcl-generics":
                    showBclGenerics = true;
                    break;
                case "--workspace-symbols":
                    showWorkspace = true;
                    break;
                case "--facets":
                    showFacets = true;
                    break;
            }
        }

        if (!File.Exists(dbPath))
        {
            return PrintError($"Database file not found: {dbPath}");
        }

        using var conn = new SqliteConnection($"Data Source={dbPath}");
        conn.Open();

        if (showAmbient)
        {
            Console.WriteLine("\n--- Stratum 0: Ambient Keywords, Aliases & Literals ---");
            var rows = Queries.QueryAmbient(conn);
            foreach (var r in rows.Take(30))
            {
                var name = r["name"];
                var kind = r["symbol_kind"];
                var mod = r["target_module_name"];
                var sym = r["target_symbol_name"];
                var map = mod != null ? $" -> {mod}.{sym}" : "";
                Console.WriteLine($"[{kind}] {name}{map}");
            }
            if (rows.Count > 30) Console.WriteLine($"... ({rows.Count - 30} more items)");
        }

        if (showBclSummary)
        {
            Console.WriteLine("\n--- Stratum 1: BCL Type Kind Breakdown ---");
            var rows = Queries.QueryBclSummary(conn);
            Console.WriteLine($"{"Type Kind",-15} | {"Count",8}");
            Console.WriteLine(new string('-', 26));
            foreach (var r in rows)
            {
                Console.WriteLine($"{r["type_kind"],-15} | {r["count"],8}");
            }
        }

        if (showBclOverloads)
        {
            Console.WriteLine("\n--- Stratum 1: Top Polymorphic Method Overloads ---");
            var rows = Queries.QueryBclOverloads(conn, limit: 15);
            Console.WriteLine($"{"Overloads",-10} | {"Container",-35} | {"Method",-25}");
            Console.WriteLine(new string('-', 75));
            foreach (var r in rows)
            {
                Console.WriteLine($"{r["overload_count"],-10} | {r["container_qname"],-35} | {r["method_name"],-25}");
            }
        }

        if (showBclGenerics)
        {
            Console.WriteLine("\n--- Stratum 1: Generic Types & Implemented Interfaces ---");
            var rows = Queries.QueryBclGenerics(conn, limit: 15);
            foreach (var r in rows)
            {
                var qname = r["qualified_name"];
                var gen = r["generic_type_parameters_json"];
                var ifaces = r["implemented_interfaces_json"];
                Console.WriteLine($"[{r["type_kind"]}] {qname} (Params: {gen})");
                if (ifaces != null) Console.WriteLine($"    Implements: {ifaces}");
            }
        }

        if (showBcl)
        {
            Console.WriteLine("\n--- Stratum 1: Runtime BCL Sample ---");
            var rows = Queries.QueryBcl(conn, limit: 15);
            foreach (var r in rows)
            {
                Console.WriteLine($"[{r["container_kind"]}] {r["container_qname"]} :: {r["symbol_name"]} ({r["raw_signature"]})");
            }
        }

        if (showWorkspace)
        {
            Console.WriteLine("\n--- Stratum 3: Workspace Symbols & AST Coordinates ---");
            var rows = Queries.QueryWorkspaceSymbols(conn);
            foreach (var r in rows)
            {
                var loc = $"L{r["start_line"]}:C{r["start_col"]}-L{r["end_line"]}:C{r["end_col"]}";
                Console.WriteLine($"[{r["symbol_kind"],-12}] {r["container_qname"]}.{r["symbol_name"],-25} @ {loc,-15} vis={r["visibility"]}");
            }
        }

        if (showFacets)
        {
            Console.WriteLine("\n--- C# Container Facets ---");
            var facets = Queries.QueryFacets(conn);
            foreach (var f in facets)
            {
                var qname = f["qualified_name"];
                var kind = f["type_kind"];
                var ifaces = f["implemented_interfaces_json"];
                var ifaceStr = ifaces != null ? $" : {ifaces}" : "";
                Console.WriteLine($"[{kind}] {qname}{ifaceStr}");
            }
        }

        return 0;
    }
}
