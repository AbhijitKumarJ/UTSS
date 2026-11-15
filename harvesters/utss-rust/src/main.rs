use std::path::Path;
use rusqlite::Connection;
use utss_rust::queries::*;
use utss_rust::schema;
use utss_rust::stratum0_ambient;
use utss_rust::stratum1_std;
use utss_rust::stratum3_workspace;

fn print_help() {
    println!(r#"UTSS Rust - Universal Type & Symbol System (Rust Harvester)

Usage:
  utss-rs <command> [options]

Commands:
  harvest          Extract Rust types, symbols, and metadata into SQLite catalog.
  report           Generate diagnostic summary across universal & Rust facet tables.
  query            Run targeted diagnostic queries.

Harvest Options:
  --db <path>           Path to the SQLite database (default: catalog_rust.db)
  --reset               Reset/drop existing tables before harvesting
  --all                 Harvest Stratum 0, 1 (recommended std), and Demo Workspace
  --stratum0            Harvest Stratum 0 (Ambient keywords, primitives, prelude, macros)
  --std-recommended     Harvest curated Tier-1 Rust Standard Library (std, core, alloc)
  --std-full            Harvest full Rust Standard Library modules
  --demo-workspace      Harvest Stratum 3 embedded demo workspace (commerce_engine)
  --workspace <dir>     Harvest Stratum 3 from a directory of .rs files

Query Options:
  --db <path>           Path to the SQLite database (default: catalog_rust.db)
  --ambient             Display Stratum 0 ambient keywords, primitives, prelude & macros
  --std-summary         Display Stratum 1 standard library breakdown by item kind
  --workspace-symbols   Display Stratum 3 workspace symbols and exact AST span coordinates
  --facets              Display Rust Container and Symbol facets
"#);
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.is_empty() || args[0] == "-h" || args[0] == "--help" || args[0] == "help" {
        print_help();
        return Ok(());
    }

    let command = args[0].to_lowercase();
    let sub_args = &args[1..];

    match command.as_str() {
        "harvest" => handle_harvest(sub_args)?,
        "report" => handle_report(sub_args)?,
        "query" => handle_query(sub_args)?,
        unknown => {
            eprintln!("Unknown command: {}", unknown);
            print_help();
            std::process::exit(1);
        }
    }

    Ok(())
}

fn handle_harvest(args: &[String]) -> Result<(), Box<dyn std::error::Error>> {
    let mut db_path = "catalog_rust.db".to_string();
    let mut reset = false;
    let mut do_stratum0 = false;
    let mut do_std_rec = false;
    let mut do_std_full = false;
    let mut do_demo_ws = false;
    let mut ws_path: Option<String> = None;

    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--db" if i + 1 < args.len() => {
                i += 1;
                db_path = args[i].clone();
            }
            "--reset" => reset = true,
            "--all" => {
                do_stratum0 = true;
                do_std_rec = true;
                do_demo_ws = true;
            }
            "--stratum0" => do_stratum0 = true,
            "--std-recommended" => do_std_rec = true,
            "--std-full" => do_std_full = true,
            "--demo-workspace" => do_demo_ws = true,
            "--workspace" if i + 1 < args.len() => {
                i += 1;
                ws_path = Some(args[i].clone());
            }
            _ => {}
        }
        i += 1;
    }

    if !do_stratum0 && !do_std_rec && !do_std_full && !do_demo_ws && ws_path.is_none() {
        // Default to --all
        do_stratum0 = true;
        do_std_rec = true;
        do_demo_ws = true;
    }

    println!("[UTSS.Rust] Initializing SQLite catalog: {}", db_path);
    let mut conn = Connection::open(&db_path)?;
    schema::init_db(&conn, reset)?;

    if do_stratum0 {
        println!("[UTSS.Rust] Harvesting Stratum 0 (Ambient Scope)...");
        let (kw, prim, prel) = stratum0_ambient::harvest(&mut conn)?;
        println!("  -> Harvested {} keywords, {} primitive aliases, {} prelude/macro items.", kw, prim, prel);
    }

    if do_std_full {
        println!("[UTSS.Rust] Harvesting Stratum 1 (Full Rust Standard Library)...");
        let (c, s, call) = stratum1_std::harvest(&mut conn, true)?;
        println!("  -> Harvested {} containers, {} symbols, {} callables.", c, s, call);
    } else if do_std_rec {
        println!("[UTSS.Rust] Harvesting Stratum 1 (Curated Tier-1 Standard Library)...");
        let (c, s, call) = stratum1_std::harvest(&mut conn, false)?;
        println!("  -> Harvested {} containers, {} symbols, {} callables.", c, s, call);
    }

    if do_demo_ws {
        println!("[UTSS.Rust] Harvesting Stratum 3 (Embedded Demo Workspace: commerce_engine)...");
        let (c, s, call) = stratum3_workspace::harvest_demo_workspace(&mut conn)?;
        println!("  -> Harvested {} containers, {} symbols, {} callables.", c, s, call);
    }

    if let Some(ws) = ws_path {
        println!("[UTSS.Rust] Harvesting Stratum 3 (Workspace Source: {})...", ws);
        let crate_name = Path::new(&ws)
            .file_name()
            .and_then(|s| s.to_str())
            .unwrap_or("workspace");
        let (c, s, call) = stratum3_workspace::harvest_workspace_dir(&mut conn, Path::new(&ws), crate_name)?;
        println!("  -> Harvested {} containers, {} symbols, {} callables.", c, s, call);
    }

    println!("[UTSS.Rust] Harvesting complete!");
    print_spectrum_report(&conn)?;
    Ok(())
}

fn handle_report(args: &[String]) -> Result<(), Box<dyn std::error::Error>> {
    let mut db_path = "catalog_rust.db".to_string();
    let mut i = 0;
    while i < args.len() {
        if args[i] == "--db" && i + 1 < args.len() {
            i += 1;
            db_path = args[i].clone();
        }
        i += 1;
    }

    if !Path::new(&db_path).exists() {
        eprintln!("Error: Database file not found: {}", db_path);
        std::process::exit(1);
    }

    let conn = Connection::open(&db_path)?;
    print_spectrum_report(&conn)?;
    Ok(())
}

fn handle_query(args: &[String]) -> Result<(), Box<dyn std::error::Error>> {
    let mut db_path = "catalog_rust.db".to_string();
    let mut show_ambient = false;
    let mut show_std_summary = false;
    let mut show_ws = false;
    let mut show_facets = false;

    let mut i = 0;
    while i < args.len() {
        match args[i].as_str() {
            "--db" if i + 1 < args.len() => {
                i += 1;
                db_path = args[i].clone();
            }
            "--ambient" => show_ambient = true,
            "--std-summary" => show_std_summary = true,
            "--workspace-symbols" => show_ws = true,
            "--facets" => show_facets = true,
            _ => {}
        }
        i += 1;
    }

    if !Path::new(&db_path).exists() {
        eprintln!("Error: Database file not found: {}", db_path);
        std::process::exit(1);
    }

    let conn = Connection::open(&db_path)?;

    if show_ambient {
        query_ambient(&conn)?;
    }

    if show_std_summary {
        query_std_summary(&conn)?;
    }

    if show_ws {
        query_workspace_symbols(&conn)?;
    }

    if show_facets {
        query_facets(&conn)?;
    }

    Ok(())
}
