import test from "node:test";
import assert from "node:assert/strict";
import { DatabaseSync } from "node:sqlite";
import { initSchema, resetSchema, EXPECTED_TABLES } from "../schema.js";
import { harvestStratum0Ambient } from "../stratum0_ambient.js";
import { harvestStratum1Std } from "../stratum1_std.js";
import { WorkspaceAstCataloger } from "../stratum3_workspace.js";

test("Schema initialization and reset creates all 11 expected tables", () => {
  const db = new DatabaseSync(":memory:");
  initSchema(db);

  const query = db.prepare(`SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';`);
  const tables = query.all().map((r) => (r as { name: string }).name);

  for (const expected of EXPECTED_TABLES) {
    assert.ok(tables.includes(expected), `Missing expected table: ${expected}`);
  }

  // Test reset
  resetSchema(db);
  const tablesAfterReset = query.all().map((r) => (r as { name: string }).name);
  for (const expected of EXPECTED_TABLES) {
    assert.ok(tablesAfterReset.includes(expected), `Missing expected table after reset: ${expected}`);
  }
  db.close();
});

test("Stratum 0 Ambient harvester populates keywords, primitives, and globals", () => {
  const db = new DatabaseSync(":memory:");
  initSchema(db);

  const res = harvestStratum0Ambient(db);
  assert.ok(res.keywordCount >= 50, `Expected at least 50 keywords, got ${res.keywordCount}`);
  assert.ok(res.primitiveCount >= 10, `Expected at least 10 primitives, got ${res.primitiveCount}`);
  assert.ok(res.utilityTypeCount >= 15, `Expected at least 15 utility types, got ${res.utilityTypeCount}`);
  assert.ok(res.globalCount >= 40, `Expected at least 40 globals, got ${res.globalCount}`);

  // Check specific symbols
  const checkSym = db.prepare(`SELECT symbol_kind FROM symbols WHERE name = ?;`);
  const kw = checkSym.get("function") as { symbol_kind: string } | undefined;
  assert.equal(kw?.symbol_kind, "keyword");

  const prim = checkSym.get("string") as { symbol_kind: string } | undefined;
  assert.equal(prim?.symbol_kind, "primitive_type");

  const util = checkSym.get("Partial") as { symbol_kind: string } | undefined;
  assert.equal(util?.symbol_kind, "utility_type");

  const glob = checkSym.get("Promise") as { symbol_kind: string } | undefined;
  assert.equal(glob?.symbol_kind, "class");

  db.close();
});

test("Stratum 1 Standard Library harvester creates modules and callables", () => {
  const db = new DatabaseSync(":memory:");
  initSchema(db);
  const envRes = harvestStratum0Ambient(db);

  const res = harvestStratum1Std(db, envRes.envId, false);
  assert.ok(res.containersHarvested >= 10, "Expected at least 10 stdlib containers");
  assert.ok(res.symbolsHarvested >= 30, "Expected at least 30 stdlib symbols");
  assert.ok(res.callablesHarvested >= 30, "Expected at least 30 stdlib callables");
  assert.ok(res.parametersHarvested >= 40, "Expected at least 40 stdlib parameters");

  // Check node:fs readFile
  const checkFunc = db.prepare(`
    SELECT cal.is_async, cal.return_type_expr
    FROM symbols s
    JOIN callables cal ON cal.symbol_id = s.symbol_id
    WHERE s.name = 'readFile';
  `);
  const rf = checkFunc.get() as { is_async: number; return_type_expr: string } | undefined;
  assert.ok(rf, "readFile function must exist in node:fs/promises");
  assert.equal(rf?.is_async, 1, "readFile must be async");

  db.close();
});

test("Stratum 3 Workspace pure AST harvester parses classes, methods, coordinates, and facets", () => {
  const db = new DatabaseSync(":memory:");
  initSchema(db);
  const envRes = harvestStratum0Ambient(db);

  const cataloger = new WorkspaceAstCataloger(db, envRes.envId);
  const res = cataloger.harvestEmbeddedDemo();

  assert.equal(res.filesProcessed, 4, "Expected 4 files processed");
  assert.ok(res.containersHarvested >= 8, `Expected at least 8 containers, got ${res.containersHarvested}`);
  assert.ok(res.symbolsHarvested >= 30, `Expected at least 30 symbols, got ${res.symbolsHarvested}`);
  assert.ok(res.callablesHarvested >= 10, `Expected at least 10 callables, got ${res.callablesHarvested}`);
  assert.ok(res.aliasesHarvested >= 5, `Expected at least 5 aliases, got ${res.aliasesHarvested}`);

  // Check Order class container and coordinates
  const checkOrder = db.prepare(`
    SELECT container_kind, start_line, start_col, end_line, end_col
    FROM containers
    WHERE short_name = 'Order' AND container_kind = 'class';
  `);
  const orderClass = checkOrder.get() as {
    container_kind: string;
    start_line: number;
    start_col: number;
    end_line: number;
    end_col: number;
  };
  assert.ok(orderClass, "Order class container must exist");
  assert.ok(orderClass.start_line > 0, "start_line must be positive 1-based");
  assert.ok(orderClass.end_line >= orderClass.start_line, "end_line must be >= start_line");

  // Check async processOrder method in OrderService class
  const checkAsync = db.prepare(`
    SELECT cal.is_async, cal.is_generator, f.access_modifier
    FROM symbols s
    JOIN containers c ON s.container_id = c.container_id
    JOIN callables cal ON cal.symbol_id = s.symbol_id
    LEFT JOIN ts_symbol_facets f ON f.symbol_id = s.symbol_id
    WHERE s.name = 'processOrder' AND c.short_name = 'OrderService';
  `);
  const asyncMethod = checkAsync.get() as { is_async: number; is_generator: number; access_modifier: string };
  assert.ok(asyncMethod, "processOrder method must exist");
  assert.equal(asyncMethod.is_async, 1, "processOrder must be marked is_async=1");
  assert.equal(asyncMethod.access_modifier, "public", "processOrder must be public");

  // Check generator streamAuditEvents method in OrderService class
  const checkGen = db.prepare(`
    SELECT cal.is_async, cal.is_generator
    FROM symbols s
    JOIN containers c ON s.container_id = c.container_id
    JOIN callables cal ON cal.symbol_id = s.symbol_id
    WHERE s.name = 'streamAuditEvents' AND c.short_name = 'OrderService';
  `);
  const genMethod = checkGen.get() as { is_async: number; is_generator: number };
  assert.ok(genMethod, "streamAuditEvents method must exist");
  assert.equal(genMethod.is_generator, 1, "streamAuditEvents must be marked is_generator=1");

  // Check re-exports in symbol_aliases
  const checkAliases = db.prepare(`
    SELECT exposed_name, alias_kind
    FROM symbol_aliases
    WHERE exposed_name LIKE '%PrimaryOrder%';
  `);
  const alias = checkAliases.get() as { exposed_name: string; alias_kind: string } | undefined;
  assert.ok(alias, "PrimaryOrder export alias must exist in symbol_aliases");
  assert.equal(alias?.alias_kind, "export_reexport");

  db.close();
});
