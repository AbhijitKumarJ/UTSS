import { DatabaseSync } from "node:sqlite";

export function querySpectrumSummary(db: DatabaseSync): Array<Record<string, unknown>> {
  const query = db.prepare(`
    SELECT
      d.stratum,
      d.dist_name,
      d.dist_version,
      COUNT(DISTINCT c.container_id) AS total_containers,
      COUNT(DISTINCT s.symbol_id) AS total_symbols,
      COUNT(DISTINCT cal.symbol_id) AS total_callables,
      COUNT(DISTINCT p.param_id) AS total_parameters,
      COUNT(DISTINCT a.alias_id) AS total_aliases
    FROM distributions d
    LEFT JOIN containers c ON c.dist_id = d.dist_id
    LEFT JOIN symbols s ON s.container_id = c.container_id
    LEFT JOIN callables cal ON cal.symbol_id = s.symbol_id
    LEFT JOIN parameters p ON p.callable_symbol_id = cal.symbol_id
    LEFT JOIN symbol_aliases a ON a.source_container_id = c.container_id
    GROUP BY d.dist_id
    ORDER BY d.stratum, d.dist_name;
  `);
  return query.all();
}

export function queryAmbientSummary(db: DatabaseSync): Array<Record<string, unknown>> {
  const query = db.prepare(`
    SELECT
      s.symbol_kind,
      COUNT(*) AS item_count,
      GROUP_CONCAT(s.name, ', ') AS sample_items
    FROM symbols s
    JOIN containers c ON s.container_id = c.container_id
    JOIN distributions d ON c.dist_id = d.dist_id
    WHERE d.stratum = 0
    GROUP BY s.symbol_kind
    ORDER BY item_count DESC;
  `);
  return query.all();
}

export function queryStdlibSummary(db: DatabaseSync): Array<Record<string, unknown>> {
  const query = db.prepare(`
    SELECT
      c.qualified_name AS module_name,
      c.container_kind,
      COUNT(s.symbol_id) AS symbol_count,
      COUNT(cal.symbol_id) AS callable_count
    FROM containers c
    JOIN distributions d ON c.dist_id = d.dist_id
    LEFT JOIN symbols s ON s.container_id = c.container_id
    LEFT JOIN callables cal ON cal.symbol_id = s.symbol_id
    WHERE d.stratum = 1
    GROUP BY c.container_id
    ORDER BY symbol_count DESC, c.qualified_name;
  `);
  return query.all();
}

export function queryWorkspaceSymbols(db: DatabaseSync): Array<Record<string, unknown>> {
  const query = db.prepare(`
    SELECT
      c.qualified_name AS container,
      s.name AS symbol_name,
      s.symbol_kind,
      f.access_modifier,
      f.is_readonly,
      s.start_line,
      s.start_col,
      s.end_line,
      s.end_col,
      cal.raw_signature,
      cal.return_type_expr
    FROM symbols s
    JOIN containers c ON s.container_id = c.container_id
    JOIN distributions d ON c.dist_id = d.dist_id
    LEFT JOIN ts_symbol_facets f ON f.symbol_id = s.symbol_id
    LEFT JOIN callables cal ON cal.symbol_id = s.symbol_id
    WHERE d.stratum = 3
    ORDER BY c.qualified_name, s.start_line, s.name;
  `);
  return query.all();
}

export function queryTsFacets(db: DatabaseSync): Array<Record<string, unknown>> {
  const query = db.prepare(`
    SELECT
      c.qualified_name AS container,
      cf.item_kind AS container_kind,
      cf.is_export,
      cf.heritage_clauses_json,
      s.name AS symbol,
      sf.member_kind,
      sf.access_modifier,
      sf.is_readonly,
      sf.is_optional,
      sf.modifiers_json
    FROM symbols s
    JOIN containers c ON s.container_id = c.container_id
    JOIN ts_container_facets cf ON cf.container_id = c.container_id
    JOIN ts_symbol_facets sf ON sf.symbol_id = s.symbol_id
    ORDER BY c.qualified_name, s.name
    LIMIT 30;
  `);
  return query.all();
}

export function queryOverloads(db: DatabaseSync): Array<Record<string, unknown>> {
  const query = db.prepare(`
    SELECT
      s.qualified_name,
      cal.raw_signature,
      co.overload_ordinal,
      co.raw_signature AS overload_signature,
      co.return_type_expr
    FROM callable_overloads co
    JOIN callables cal ON co.callable_symbol_id = cal.symbol_id
    JOIN symbols s ON cal.symbol_id = s.symbol_id
    ORDER BY s.qualified_name, co.overload_ordinal;
  `);
  return query.all();
}

export function printTable(title: string, rows: Array<Record<string, unknown>>): void {
  console.log(`\n=== ${title} ===`);
  if (!rows || rows.length === 0) {
    console.log("  (no rows returned)");
    return;
  }
  console.table(rows);
}
