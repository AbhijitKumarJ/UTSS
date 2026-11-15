use rusqlite::Connection;
use utss_rust::schema;
use utss_rust::stratum0_ambient;
use utss_rust::stratum1_std;
use utss_rust::stratum3_workspace;

#[test]
fn test_schema_init_and_reset() {
    let conn = Connection::open_in_memory().unwrap();
    schema::init_db(&conn, false).unwrap();

    for tbl in schema::EXPECTED_TABLES {
        let count: Result<i64, _> = conn.query_row(&format!("SELECT COUNT(*) FROM {};", tbl), [], |r| r.get(0));
        assert!(count.is_ok(), "Table {} should exist", tbl);
    }

    // Insert dummy environment
    conn.execute(
        "INSERT INTO environments (language, runtime_name, language_version, version_major, version_minor, version_micro, platform_triplet, sys_platform, executable_path)
        VALUES ('rust', 'rustc', '1.85.0', 1, 85, 0, 'linux-x86_64', 'linux', '/usr/bin/cargo');",
        [],
    ).unwrap();

    let count: i64 = conn.query_row("SELECT COUNT(*) FROM environments;", [], |r| r.get(0)).unwrap();
    assert_eq!(count, 1);

    // Reset drops and recreates
    schema::init_db(&conn, true).unwrap();
    let count: i64 = conn.query_row("SELECT COUNT(*) FROM environments;", [], |r| r.get(0)).unwrap();
    assert_eq!(count, 0);
}

#[test]
fn test_stratum0_ambient_harvest() {
    let mut conn = Connection::open_in_memory().unwrap();
    schema::init_db(&conn, false).unwrap();

    let (kw_count, prim_count, prel_count) = stratum0_ambient::harvest(&mut conn).unwrap();

    assert!(kw_count >= 50, "Expected >= 50 keywords, got {}", kw_count);
    assert!(prim_count >= 20, "Expected >= 20 primitives, got {}", prim_count);
    assert!(prel_count >= 40, "Expected >= 40 prelude items, got {}", prel_count);

    // Verify primitive alias
    let target_mod: String = conn.query_row(
        "SELECT target_module_name FROM symbol_aliases WHERE exposed_name = 'i32';",
        [],
        |r| r.get(0),
    ).unwrap();
    assert_eq!(target_mod, "core::primitive");

    // Verify prelude trait
    let target_mod: String = conn.query_row(
        "SELECT target_module_name FROM symbol_aliases WHERE exposed_name = 'Iterator';",
        [],
        |r| r.get(0),
    ).unwrap();
    assert_eq!(target_mod, "core::iter");
}

#[test]
fn test_stratum1_std_harvest() {
    let mut conn = Connection::open_in_memory().unwrap();
    schema::init_db(&conn, false).unwrap();
    stratum0_ambient::harvest(&mut conn).unwrap();

    let (c_count, s_count, call_count) = stratum1_std::harvest(&mut conn, false).unwrap();

    assert!(c_count >= 15, "Expected >= 15 containers, got {}", c_count);
    assert!(s_count >= 30, "Expected >= 30 symbols, got {}", s_count);
    assert!(call_count >= 30, "Expected >= 30 callables, got {}", call_count);

    // Check HashMap::insert method
    let (self_kind, ret_type): (String, String) = conn.query_row(
        "SELECT f.self_kind, c.return_type_expr
        FROM symbols s
        JOIN rust_symbol_facets f ON s.symbol_id = f.symbol_id
        JOIN callables c ON s.symbol_id = c.symbol_id
        WHERE s.qualified_name = 'std::collections::HashMap::insert';",
        [],
        |r| Ok((r.get(0)?, r.get(1)?)),
    ).unwrap();

    assert_eq!(self_kind, "mut_ref");
    assert_eq!(ret_type, "Option<V>");
}

#[test]
fn test_stratum3_workspace_harvest() {
    let mut conn = Connection::open_in_memory().unwrap();
    schema::init_db(&conn, false).unwrap();
    stratum0_ambient::harvest(&mut conn).unwrap();

    let (c_count, s_count, call_count) = stratum3_workspace::harvest_demo_workspace(&mut conn).unwrap();

    assert!(c_count >= 8, "Expected >= 8 containers, got {}", c_count);
    assert!(s_count >= 15, "Expected >= 15 symbols, got {}", s_count);
    assert!(call_count >= 2, "Expected >= 2 callables, got {}", call_count);

    // Check Order struct fields
    let field_count: i64 = conn.query_row(
        "SELECT COUNT(*) FROM symbols s
        JOIN containers c ON s.container_id = c.container_id
        WHERE c.qualified_name = 'commerce_engine::models::Order' AND s.symbol_kind = 'struct_field';",
        [],
        |r| r.get(0),
    ).unwrap();
    assert_eq!(field_count, 5);

    // Check Customer private field
    let vis: String = conn.query_row(
        "SELECT visibility FROM symbols
        WHERE qualified_name = 'commerce_engine::models::Customer::secret_token';",
        [],
        |r| r.get(0),
    ).unwrap();
    assert_eq!(vis, "private");

    // Check exact AST coordinates
    let (s_line, s_col, e_line, e_col): (i64, i64, i64, i64) = conn.query_row(
        "SELECT start_line, start_col, end_line, end_col
        FROM symbols
        WHERE qualified_name = 'commerce_engine::models::Order::order_id';",
        [],
        |r| Ok((r.get(0)?, r.get(1)?, r.get(2)?, r.get(3)?)),
    ).unwrap();

    assert!(s_line > 0);
    assert!(e_line >= s_line);
    assert!(e_col >= s_col);

    // Check trait method self_kind
    let self_kind: String = conn.query_row(
        "SELECT f.self_kind FROM symbols s
        JOIN rust_symbol_facets f ON s.symbol_id = f.symbol_id
        WHERE s.qualified_name = 'commerce_engine::services::OrderService::process_order';",
        [],
        |r| r.get(0),
    ).unwrap();
    assert_eq!(self_kind, "mut_ref");
}
