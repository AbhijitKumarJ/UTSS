#!/usr/bin/env node

import { DatabaseSync } from "node:sqlite";
import * as path from "node:path";
import * as fs from "node:fs";
import { initSchema, resetSchema } from "./schema.js";
import { harvestStratum0Ambient } from "./stratum0_ambient.js";
import { harvestStratum1Std } from "./stratum1_std.js";
import { WorkspaceAstCataloger } from "./stratum3_workspace.js";
import {
  querySpectrumSummary,
  queryAmbientSummary,
  queryStdlibSummary,
  queryWorkspaceSymbols,
  queryTsFacets,
  queryOverloads,
  printTable
} from "./queries.js";

function printUsage(): void {
  console.log(`
UTSS TypeScript Cataloger (utss-ts)

Usage:
  utss-ts harvest [options]
  utss-ts report  --db <path>
  utss-ts query   --db <path> [options]

Harvest Options:
  --db <path>             SQLite database file path (default: catalog_ts_demo.db)
  --reset                 Drop existing tables and recreate schema
  --stratum0              Harvest Stratum 0 (Ambient Scope: keywords, primitives, builtins)
  --std-recommended       Harvest Stratum 1 (Curated Tier-1 Node.js/ECMAScript stdlib)
  --std-full              Harvest Stratum 1 (Full Node.js standard distribution, 46 modules)
  --demo-workspace        Harvest Stratum 3 (Embedded TypeScript demo workspace)
  --workspace-dir <dir>   Harvest Stratum 3 from a physical codebase directory

Query Options:
  --spectrum              Display spectrum summary breakdown across all Strata (0, 1, 3)
  --ambient               Display breakdown of ambient keywords, primitives, and globals
  --stdlib                Display breakdown of harvested standard library modules
  --workspace-symbols     Display workspace symbols with 1-based AST source span coordinates
  --ts-facets             Display TypeScript-specific container and symbol fidelity facets
  --overloads             Display callable overloads
`);
}

function parseArgs(args: string[]): {
  command: string;
  options: Record<string, string | boolean>;
} {
  const command = args[0] || "help";
  const options: Record<string, string | boolean> = {};

  for (let i = 1; i < args.length; i++) {
    const arg = args[i];
    if (arg.startsWith("--")) {
      const key = arg.slice(2);
      if (i + 1 < args.length && !args[i + 1].startsWith("--")) {
        options[key] = args[i + 1];
        i++;
      } else {
        options[key] = true;
      }
    }
  }

  return { command, options };
}

function main(): void {
  const argv = process.argv.slice(2);
  if (argv.length === 0 || argv[0] === "--help" || argv[0] === "-h" || argv[0] === "help") {
    printUsage();
    process.exit(0);
  }

  const { command, options } = parseArgs(argv);
  const dbPath = (options.db as string) || "catalog_ts_demo.db";

  if (command === "harvest") {
    console.log(`[UTSS.TS] Opening SQLite database: ${dbPath}`);
    const db = new DatabaseSync(dbPath);

    if (options.reset) {
      console.log("[UTSS.TS] Resetting schema (dropping existing tables)...");
      resetSchema(db);
    } else {
      initSchema(db);
    }

    let envId = 1;

    if (options.stratum0) {
      console.log("[UTSS.TS] Harvesting Stratum 0 (Ambient Scope)...");
      const res0 = harvestStratum0Ambient(db);
      envId = res0.envId;
      console.log(
        `  -> Harvested ${res0.keywordCount} keywords, ${res0.primitiveCount} primitives, ${res0.utilityTypeCount} utility types, ${res0.globalCount} built-ins.`
      );
    } else {
      // Ensure environment exists
      const res0 = harvestStratum0Ambient(db);
      envId = res0.envId;
    }

    if (options["std-recommended"]) {
      console.log("[UTSS.TS] Harvesting Stratum 1 (Curated Tier-1 Standard Library)...");
      const res1 = harvestStratum1Std(db, envId, false);
      console.log(
        `  -> Harvested ${res1.containersHarvested} containers, ${res1.symbolsHarvested} symbols, ${res1.callablesHarvested} callables, ${res1.parametersHarvested} parameters.`
      );
    } else if (options["std-full"]) {
      console.log("[UTSS.TS] Harvesting Stratum 1 (Full Node.js Standard Library Distribution)...");
      const res1 = harvestStratum1Std(db, envId, true);
      console.log(
        `  -> Harvested ${res1.containersHarvested} containers, ${res1.symbolsHarvested} symbols, ${res1.callablesHarvested} callables, ${res1.parametersHarvested} parameters.`
      );
    }

    if (options["demo-workspace"]) {
      console.log("[UTSS.TS] Harvesting Stratum 3 (Embedded Demo Workspace: commerce_engine)...");
      const cataloger = new WorkspaceAstCataloger(db, envId);
      const res3 = cataloger.harvestEmbeddedDemo();
      console.log(
        `  -> Harvested ${res3.filesProcessed} files: ${res3.containersHarvested} containers, ${res3.symbolsHarvested} symbols, ${res3.callablesHarvested} callables, ${res3.parametersHarvested} parameters, ${res3.aliasesHarvested} aliases.`
      );
    } else if (options["workspace-dir"]) {
      const dir = options["workspace-dir"] as string;
      console.log(`[UTSS.TS] Harvesting Stratum 3 from workspace directory: ${dir}...`);
      const cataloger = new WorkspaceAstCataloger(db, envId);
      const res3 = cataloger.harvestDirectory(dir);
      console.log(
        `  -> Harvested ${res3.filesProcessed} files: ${res3.containersHarvested} containers, ${res3.symbolsHarvested} symbols, ${res3.callablesHarvested} callables, ${res3.parametersHarvested} parameters, ${res3.aliasesHarvested} aliases.`
      );
    }

    db.close();
    console.log(`[UTSS.TS] Harvesting successfully completed for '${dbPath}'.`);
  } else if (command === "report") {
    if (!fs.existsSync(dbPath)) {
      console.error(`Error: Database file not found: ${dbPath}`);
      process.exit(1);
    }
    const db = new DatabaseSync(dbPath);
    console.log(`\n================================================================================`);
    console.log(`                 UTSS TYPESCRIPT CATALOG AUDIT REPORT`);
    console.log(`                 Database: ${path.resolve(dbPath)}`);
    console.log(`================================================================================`);
    const summary = querySpectrumSummary(db);
    printTable("Spectrum Summary by Stratum", summary);
    db.close();
  } else if (command === "query") {
    if (!fs.existsSync(dbPath)) {
      console.error(`Error: Database file not found: ${dbPath}`);
      process.exit(1);
    }
    const db = new DatabaseSync(dbPath);

    if (options.spectrum) {
      printTable("Spectrum Summary", querySpectrumSummary(db));
    }
    if (options.ambient) {
      printTable("Stratum 0 Ambient Summary", queryAmbientSummary(db));
    }
    if (options.stdlib) {
      printTable("Stratum 1 Standard Library Breakdown", queryStdlibSummary(db));
    }
    if (options["workspace-symbols"]) {
      printTable("Stratum 3 Workspace Symbols & AST Coordinates", queryWorkspaceSymbols(db));
    }
    if (options["ts-facets"]) {
      printTable("TypeScript Fidelity Facets", queryTsFacets(db));
    }
    if (options.overloads) {
      printTable("Callable Overloads", queryOverloads(db));
    }

    db.close();
  } else {
    console.error(`Unknown command: ${command}`);
    printUsage();
    process.exit(1);
  }
}

main();
