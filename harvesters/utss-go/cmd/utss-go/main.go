package main

import (
	"database/sql"
	"fmt"
	"os"
	"path/filepath"

	_ "modernc.org/sqlite"

	"utss-go/pkg/queries"
	"utss-go/pkg/schema"
	"utss-go/pkg/stratum0"
	"utss-go/pkg/stratum1"
	"utss-go/pkg/stratum3"
)

func printUsage() {
	fmt.Println(`
UTSS Go Cataloger (utss-go)

Usage:
  utss-go harvest [options]
  utss-go report  --db <path>
  utss-go query   --db <path> [options]

Harvest Options:
  --db <path>             SQLite database file path (default: catalog_go_demo.db)
  --reset                 Drop existing tables and recreate schema
  --stratum0              Harvest Stratum 0 (Ambient Scope: keywords, predeclared types, builtins)
  --std-recommended       Harvest Stratum 1 (Curated Tier-1 standard library: fmt, io, os, time, sync, etc.)
  --std-full              Harvest Stratum 1 (Full standard library package distribution, 50+ packages)
  --demo-workspace        Harvest Stratum 3 (Embedded Go demo workspace: commerce_engine)
  --workspace-dir <dir>   Harvest Stratum 3 from a physical codebase directory

Query Options:
  --spectrum              Display spectrum summary breakdown across all Strata (0, 1, 3)
  --ambient               Display breakdown of ambient keywords, primitives, and globals
  --stdlib                Display breakdown of harvested standard library packages
  --workspace-symbols     Display workspace symbols with 1-based AST source span coordinates
  --go-facets             Display Go container and symbol fidelity facets
`)
}

func main() {
	if len(os.Args) < 2 {
		printUsage()
		os.Exit(0)
	}

	cmd := os.Args[1]
	if cmd == "--help" || cmd == "-h" || cmd == "help" {
		printUsage()
		os.Exit(0)
	}

	dbPath := "catalog_go_demo.db"
	reset := false
	stratum0Flag := false
	stdRecFlag := false
	stdFullFlag := false
	demoWsFlag := false
	wsDir := ""

	qSpectrum := false
	qAmbient := false
	qStdlib := false
	qWorkspaceSymbols := false
	qGoFacets := false

	for i := 2; i < len(os.Args); i++ {
		arg := os.Args[i]
		switch arg {
		case "--db":
			if i+1 < len(os.Args) {
				dbPath = os.Args[i+1]
				i++
			}
		case "--reset":
			reset = true
		case "--stratum0":
			stratum0Flag = true
		case "--std-recommended":
			stdRecFlag = true
		case "--std-full":
			stdFullFlag = true
		case "--demo-workspace":
			demoWsFlag = true
		case "--workspace-dir":
			if i+1 < len(os.Args) {
				wsDir = os.Args[i+1]
				i++
			}
		case "--spectrum":
			qSpectrum = true
		case "--ambient":
			qAmbient = true
		case "--stdlib":
			qStdlib = true
		case "--workspace-symbols":
			qWorkspaceSymbols = true
		case "--go-facets":
			qGoFacets = true
		}
	}

	db, err := sql.Open("sqlite", dbPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error opening SQLite database: %v\n", err)
		os.Exit(1)
	}
	defer db.Close()

	switch cmd {
	case "harvest":
		fmt.Printf("[UTSS.Go] Opening SQLite database: %s\n", dbPath)
		if reset {
			fmt.Println("[UTSS.Go] Resetting schema (dropping existing tables)...")
			if err := schema.ResetSchema(db); err != nil {
				fmt.Fprintf(os.Stderr, "Error resetting schema: %v\n", err)
				os.Exit(1)
			}
		} else {
			if err := schema.InitSchema(db); err != nil {
				fmt.Fprintf(os.Stderr, "Error initializing schema: %v\n", err)
				os.Exit(1)
			}
		}

		var envID int64 = 1

		if stratum0Flag {
			fmt.Println("[UTSS.Go] Harvesting Stratum 0 (Ambient Scope)...")
			res0, err := stratum0.HarvestStratum0Ambient(db)
			if err != nil {
				fmt.Fprintf(os.Stderr, "Error harvesting stratum 0: %v\n", err)
				os.Exit(1)
			}
			envID = res0.EnvID
			fmt.Printf("  -> Harvested %d keywords, %d primitives, %d constants, %d built-ins.\n",
				res0.KeywordCount, res0.PrimitiveCount, res0.ConstantCount, res0.BuiltinCount)
		} else {
			res0, err := stratum0.HarvestStratum0Ambient(db)
			if err == nil {
				envID = res0.EnvID
			}
		}

		if stdRecFlag {
			fmt.Println("[UTSS.Go] Harvesting Stratum 1 (Curated Tier-1 Standard Library)...")
			res1, err := stratum1.HarvestStratum1Std(db, envID, false)
			if err != nil {
				fmt.Fprintf(os.Stderr, "Error harvesting stratum 1: %v\n", err)
				os.Exit(1)
			}
			fmt.Printf("  -> Harvested %d containers, %d symbols, %d callables, %d parameters.\n",
				res1.ContainersHarvested, res1.SymbolsHarvested, res1.CallablesHarvested, res1.ParametersHarvested)
		} else if stdFullFlag {
			fmt.Println("[UTSS.Go] Harvesting Stratum 1 (Full Standard Library Distribution)...")
			res1, err := stratum1.HarvestStratum1Std(db, envID, true)
			if err != nil {
				fmt.Fprintf(os.Stderr, "Error harvesting stratum 1: %v\n", err)
				os.Exit(1)
			}
			fmt.Printf("  -> Harvested %d containers, %d symbols, %d callables, %d parameters.\n",
				res1.ContainersHarvested, res1.SymbolsHarvested, res1.CallablesHarvested, res1.ParametersHarvested)
		}

		if demoWsFlag {
			fmt.Println("[UTSS.Go] Harvesting Stratum 3 (Embedded Demo Workspace: commerce_engine)...")
			cataloger := stratum3.NewWorkspaceAstCataloger(db, envID)
			res3, err := cataloger.HarvestEmbeddedDemo()
			if err != nil {
				fmt.Fprintf(os.Stderr, "Error harvesting demo workspace: %v\n", err)
				os.Exit(1)
			}
			fmt.Printf("  -> Harvested %d files: %d containers, %d symbols, %d callables, %d parameters, %d state members, %d aliases.\n",
				res3.FilesProcessed, res3.ContainersHarvested, res3.SymbolsHarvested, res3.CallablesHarvested, res3.ParametersHarvested, res3.StateMembersHarvested, res3.AliasesHarvested)
		} else if wsDir != "" {
			fmt.Printf("[UTSS.Go] Harvesting Stratum 3 from workspace directory: %s...\n", wsDir)
			cataloger := stratum3.NewWorkspaceAstCataloger(db, envID)
			res3, err := cataloger.HarvestDirectory(wsDir, "workspace", "0.1.0")
			if err != nil {
				fmt.Fprintf(os.Stderr, "Error harvesting directory: %v\n", err)
				os.Exit(1)
			}
			fmt.Printf("  -> Harvested %d files: %d containers, %d symbols, %d callables, %d parameters, %d state members, %d aliases.\n",
				res3.FilesProcessed, res3.ContainersHarvested, res3.SymbolsHarvested, res3.CallablesHarvested, res3.ParametersHarvested, res3.StateMembersHarvested, res3.AliasesHarvested)
		}

		fmt.Printf("[UTSS.Go] Harvesting successfully completed for '%s'.\n", dbPath)

	case "report":
		if _, err := os.Stat(dbPath); os.IsNotExist(err) {
			fmt.Fprintf(os.Stderr, "Error: Database file not found: %s\n", dbPath)
			os.Exit(1)
		}
		absPath, _ := filepath.Abs(dbPath)
		fmt.Println("\n================================================================================")
		fmt.Println("                 UTSS GO CATALOG AUDIT REPORT")
		fmt.Printf("                 Database: %s\n", absPath)
		fmt.Println("================================================================================")
		queries.PrintSpectrumSummary(db)

	case "query":
		if _, err := os.Stat(dbPath); os.IsNotExist(err) {
			fmt.Fprintf(os.Stderr, "Error: Database file not found: %s\n", dbPath)
			os.Exit(1)
		}
		if qSpectrum {
			queries.PrintSpectrumSummary(db)
		}
		if qAmbient {
			queries.PrintAmbientSummary(db)
		}
		if qStdlib {
			queries.PrintStdlibSummary(db)
		}
		if qWorkspaceSymbols {
			queries.PrintWorkspaceSymbols(db)
		}
		if qGoFacets {
			queries.PrintGoFacets(db)
		}

	default:
		fmt.Fprintf(os.Stderr, "Unknown command: %s\n", cmd)
		printUsage()
		os.Exit(1)
	}
}
