use rusqlite::{Connection, Result};
use std::collections::BTreeMap;
use crate::schema::EXPECTED_TABLES;

pub fn get_spectrum_summary(conn: &Connection) -> Result<BTreeMap<String, i64>> {
    let mut summary = BTreeMap::new();
    for tbl in EXPECTED_TABLES {
        let count: i64 = conn.query_row(&format!("SELECT COUNT(*) FROM {};", tbl), [], |r| r.get(0))?;
        summary.insert(tbl.to_string(), count);
    }
    Ok(summary)
}

pub fn print_spectrum_report(conn: &Connection) -> Result<()> {
    let summary = get_spectrum_summary(conn)?;

    println!("\n========================================================");
    println!("          UTSS RUST SPECTRUM CATALOG REPORT             ");
    println!("========================================================");
    println!("{:<25} | {:>10}", "Table", "Count");
    println!("{}", "-".repeat(38));
    for (tbl, count) in &summary {
        println!("{:<25} | {:>10}", tbl, count);
    }

    println!("\n--------------------------------------------------------");
    println!("DISTRIBUTIONS & STRATA:");
    println!("--------------------------------------------------------");
    println!("{:<8} | {:<22} | {:<10} | {:>10}", "Stratum", "Distribution", "Version", "Containers");
    println!("{}", "-".repeat(58));

    let mut stmt = conn.prepare(
        "SELECT d.stratum, d.dist_name, d.dist_version, COUNT(c.container_id)
        FROM distributions d
        LEFT JOIN containers c ON d.dist_id = c.dist_id
        GROUP BY d.dist_id
        ORDER BY d.stratum, d.dist_name;",
    )?;

    let rows = stmt.query_map([], |row| {
        Ok((
            row.get::<_, i64>(0)?,
            row.get::<_, String>(1)?,
            row.get::<_, String>(2)?,
            row.get::<_, i64>(3)?,
        ))
    })?;

    for r in rows.flatten() {
        println!("{:<8} | {:<22} | {:<10} | {:>10}", r.0, r.1, r.2, r.3);
    }

    println!("========================================================\n");
    Ok(())
}

pub fn query_ambient(conn: &Connection) -> Result<()> {
    println!("\n--- Stratum 0: Ambient Scope (Keywords, Primitives, Prelude, Macros) ---");
    let mut stmt = conn.prepare(
        "SELECT s.symbol_kind, s.name, a.target_module_name, a.alias_kind
        FROM symbols s
        JOIN containers c ON s.container_id = c.container_id
        JOIN distributions d ON c.dist_id = d.dist_id
        LEFT JOIN symbol_aliases a ON a.source_container_id = c.container_id AND (a.exposed_name = s.name OR a.exposed_name = REPLACE(s.name, 'type:', '') OR a.exposed_name = REPLACE(s.name, 'trait:', ''))
        WHERE d.stratum = 0
        ORDER BY s.symbol_kind, s.name;",
    )?;

    let rows = stmt.query_map([], |r| {
        Ok((
            r.get::<_, String>(0)?,
            r.get::<_, String>(1)?,
            r.get::<_, Option<String>>(2)?,
            r.get::<_, Option<String>>(3)?,
        ))
    })?;

    let all: Vec<_> = rows.flatten().collect();
    for (kind, name, target, _) in all.iter().take(30) {
        let target_str = target.as_ref().map(|t| format!(" -> {}", t)).unwrap_or_default();
        println!("[{:<12}] {}{}", kind, name, target_str);
    }
    if all.len() > 30 {
        println!("... ({} more ambient symbols)", all.len() - 30);
    }
    Ok(())
}

pub fn query_std_summary(conn: &Connection) -> Result<()> {
    println!("\n--- Stratum 1: Standard Library Breakdown by Item Kind ---");
    let mut stmt = conn.prepare(
        "SELECT f.item_kind, COUNT(c.container_id) as count
        FROM containers c
        JOIN distributions d ON c.dist_id = d.dist_id
        JOIN rust_container_facets f ON c.container_id = f.container_id
        WHERE d.stratum = 1
        GROUP BY f.item_kind
        ORDER BY count DESC;",
    )?;

    let rows = stmt.query_map([], |r| {
        Ok((r.get::<_, String>(0)?, r.get::<_, i64>(1)?))
    })?;

    println!("{:<15} | {:>8}", "Item Kind", "Count");
    println!("{}", "-".repeat(26));
    for r in rows.flatten() {
        println!("{:<15} | {:>8}", r.0, r.1);
    }
    Ok(())
}

pub fn query_workspace_symbols(conn: &Connection) -> Result<()> {
    println!("\n--- Stratum 3: Workspace Symbols & AST Coordinates ---");
    let mut stmt = conn.prepare(
        "SELECT c.qualified_name, s.name, s.symbol_kind, s.visibility,
                s.start_line, s.start_col, s.end_line, s.end_col,
                f.self_kind, cal.raw_signature
        FROM symbols s
        JOIN containers c ON s.container_id = c.container_id
        JOIN distributions d ON c.dist_id = d.dist_id
        LEFT JOIN rust_symbol_facets f ON s.symbol_id = f.symbol_id
        LEFT JOIN callables cal ON s.symbol_id = cal.symbol_id
        WHERE d.stratum = 3
        ORDER BY c.qualified_name, s.start_line, s.name;",
    )?;

    let rows = stmt.query_map([], |r| {
        Ok((
            r.get::<_, String>(0)?,
            r.get::<_, String>(1)?,
            r.get::<_, String>(2)?,
            r.get::<_, String>(3)?,
            r.get::<_, Option<i64>>(4)?,
            r.get::<_, Option<i64>>(5)?,
            r.get::<_, Option<i64>>(6)?,
            r.get::<_, Option<i64>>(7)?,
            r.get::<_, Option<String>>(8)?,
            r.get::<_, Option<String>>(9)?,
        ))
    })?;

    for r in rows.flatten() {
        let (cqname, sname, kind, vis, sline, scol, eline, ecol, self_kind, _) = r;
        let loc = match (sline, scol, eline, ecol) {
            (Some(sl), Some(sc), Some(el), Some(ec)) => format!("L{}:C{}-L{}:C{}", sl, sc, el, ec),
            _ => "unknown".to_string(),
        };
        let self_str = self_kind.map(|s| format!(" self={}", s)).unwrap_or_default();
        println!("[{:<14}] {}::{:<22} @ {:<15} vis={}{}", kind, cqname, sname, loc, vis, self_str);
    }
    Ok(())
}

pub fn query_facets(conn: &Connection) -> Result<()> {
    println!("\n--- Rust Container Facets (Generics, Attributes) ---");
    let mut stmt = conn.prepare(
        "SELECT c.qualified_name, f.item_kind, f.is_pub, f.generics_json, f.attributes_json
        FROM rust_container_facets f
        JOIN containers c ON f.container_id = c.container_id
        WHERE f.item_kind IN ('struct', 'enum', 'trait')
        ORDER BY f.item_kind, c.qualified_name;",
    )?;

    let rows = stmt.query_map([], |r| {
        Ok((
            r.get::<_, String>(0)?,
            r.get::<_, String>(1)?,
            r.get::<_, i64>(2)?,
            r.get::<_, Option<String>>(3)?,
            r.get::<_, Option<String>>(4)?,
        ))
    })?;

    for (qname, kind, is_pub, gen, attrs) in rows.flatten() {
        let pub_str = if is_pub == 1 { "pub " } else { "" };
        let gen_str = gen.map(|g| format!(" <generics: {}>", g)).unwrap_or_default();
        let attr_str = attrs.map(|a| format!(" #[{}]", a)).unwrap_or_default();
        println!("[{:<8}] {}{}{}{}", kind, pub_str, qname, gen_str, attr_str);
    }
    Ok(())
}
