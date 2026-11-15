use rusqlite::{params, Connection, Result};
use crate::models::*;

pub const STRICT_KEYWORDS: &[&str] = &[
    "as", "async", "await", "break", "const", "continue", "crate", "dyn", "else", "enum",
    "extern", "false", "fn", "for", "if", "impl", "in", "let", "loop", "match",
    "mod", "move", "mut", "pub", "ref", "return", "self", "Self", "static", "struct",
    "super", "trait", "true", "type", "unsafe", "use", "where", "while",
];

pub const RESERVED_KEYWORDS: &[&str] = &[
    "abstract", "become", "box", "do", "final", "macro", "override", "priv", "try",
    "typeof", "unsized", "virtual", "yield",
];

pub const PRIMITIVE_TYPES: &[(&str, &str)] = &[
    ("bool", "core::primitive"),
    ("char", "core::primitive"),
    ("str", "core::primitive"),
    ("i8", "core::primitive"),
    ("i16", "core::primitive"),
    ("i32", "core::primitive"),
    ("i64", "core::primitive"),
    ("i128", "core::primitive"),
    ("isize", "core::primitive"),
    ("u8", "core::primitive"),
    ("u16", "core::primitive"),
    ("u32", "core::primitive"),
    ("u64", "core::primitive"),
    ("u128", "core::primitive"),
    ("usize", "core::primitive"),
    ("f32", "core::primitive"),
    ("f64", "core::primitive"),
    ("never", "core::primitive"),
    ("unit", "core::primitive"),
    ("array", "core::primitive"),
    ("slice", "core::primitive"),
    ("tuple", "core::primitive"),
];

pub const PRELUDE_TYPES: &[(&str, &str, &str)] = &[
    ("Option", "enum", "core::option"),
    ("Some", "enum_variant", "core::option::Option"),
    ("None", "enum_variant", "core::option::Option"),
    ("Result", "enum", "core::result"),
    ("Ok", "enum_variant", "core::result::Result"),
    ("Err", "enum_variant", "core::result::Result"),
    ("Box", "struct", "alloc::boxed"),
    ("String", "struct", "alloc::string"),
    ("Vec", "struct", "alloc::vec"),
];

pub const PRELUDE_TRAITS: &[(&str, &str)] = &[
    ("Clone", "core::clone"),
    ("Copy", "core::marker"),
    ("Debug", "core::fmt"),
    ("Default", "core::default"),
    ("Eq", "core::cmp"),
    ("PartialEq", "core::cmp"),
    ("Ord", "core::cmp"),
    ("PartialOrd", "core::cmp"),
    ("Hash", "core::hash"),
    ("Drop", "core::ops"),
    ("Iterator", "core::iter"),
    ("IntoIterator", "core::iter"),
    ("Send", "core::marker"),
    ("Sync", "core::marker"),
    ("Sized", "core::marker"),
    ("AsRef", "core::convert"),
    ("AsMut", "core::convert"),
    ("From", "core::convert"),
    ("Into", "core::convert"),
];

pub const PRELUDE_MACROS: &[&str] = &[
    "println!", "eprintln!", "format!", "panic!", "assert!", "assert_eq!", "assert_ne!",
    "vec!", "todo!", "unimplemented!", "unreachable!", "cfg!", "env!", "matches!",
    "dbg!", "write!", "writeln!",
];

pub fn ensure_environment(conn: &Connection) -> Result<i64> {
    let lang_ver = "1.85.0"; // Current stable toolchain version
    let platform = format!("{}-{}", std::env::consts::OS, std::env::consts::ARCH);
    let exe = std::env::current_exe()
        .map(|p| p.to_string_lossy().to_string())
        .unwrap_or_else(|_| "/usr/bin/cargo".to_string());

    let mut stmt = conn.prepare(
        "INSERT INTO environments (
            language, runtime_name, language_version, version_major, version_minor, version_micro,
            platform_triplet, sys_platform, executable_path
        )
        VALUES ('rust', 'rustc', ?1, 1, 85, 0, ?2, ?3, ?4)
        ON CONFLICT(language, runtime_name, language_version, platform_triplet, executable_path)
        DO UPDATE SET captured_at = CURRENT_TIMESTAMP
        RETURNING env_id;",
    )?;

    let env_id: i64 = stmt.query_row(params![lang_ver, platform, std::env::consts::OS, exe], |row| {
        row.get(0)
    })?;

    Ok(env_id)
}

pub fn ensure_distribution(
    conn: &Connection,
    env_id: i64,
    stratum: i64,
    dist_name: &str,
    dist_version: &str,
    summary: Option<&str>,
) -> Result<i64> {
    let mut stmt = conn.prepare(
        "INSERT INTO distributions (env_id, stratum, dist_name, dist_version, summary)
        VALUES (?1, ?2, ?3, ?4, ?5)
        ON CONFLICT(env_id, stratum, dist_name, dist_version)
        DO UPDATE SET summary = excluded.summary
        RETURNING dist_id;",
    )?;

    let dist_id: i64 = stmt.query_row(
        params![env_id, stratum, dist_name, dist_version, summary],
        |row| row.get(0),
    )?;

    Ok(dist_id)
}

pub fn harvest(conn: &mut Connection) -> Result<(usize, usize, usize)> {
    let env_id = ensure_environment(conn)?;
    let dist_id = ensure_distribution(
        conn,
        env_id,
        strata::AMBIENT,
        "<ambient>",
        "1.85.0",
        Some("Rust Ambient Scope: keywords, primitive types, standard prelude items, and built-in macros"),
    )?;

    // 1. Ambient Container
    let ambient_container_id: i64 = conn.query_row(
        "INSERT INTO containers (
            dist_id, parent_container_id, container_kind, qualified_name, short_name, requires_import, visibility, is_hidden
        )
        VALUES (?1, NULL, ?2, ?3, ?4, 0, ?5, 0)
        ON CONFLICT(dist_id, qualified_name) DO UPDATE SET container_kind = excluded.container_kind
        RETURNING container_id;",
        params![
            dist_id,
            container_kinds::AMBIENT_SCOPE,
            "<ambient>",
            "<ambient>",
            visibilities::PUBLIC,
        ],
        |row| row.get(0),
    )?;

    conn.execute(
        "INSERT INTO rust_container_facets (container_id, item_kind, is_pub)
        VALUES (?1, 'module', 1)
        ON CONFLICT(container_id) DO NOTHING;",
        params![ambient_container_id],
    )?;

    let tx = conn.transaction()?;
    let mut keyword_count = 0;

    // 2. Keywords
    let all_keywords = STRICT_KEYWORDS
        .iter()
        .map(|k| (*k, "keyword"))
        .chain(RESERVED_KEYWORDS.iter().map(|k| (*k, "reserved_keyword")));

    for (kw, kind) in all_keywords {
        let sym_id: i64 = tx.query_row(
            "INSERT INTO symbols (
                container_id, origin_container_id, name, qualified_name, symbol_kind, visibility, provenance, is_hidden
            )
            VALUES (?1, ?1, ?2, ?3, ?4, ?5, ?6, 0)
            ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
            RETURNING symbol_id;",
            params![
                ambient_container_id,
                kw,
                format!("<ambient>::{}", kw),
                kind,
                visibilities::PUBLIC,
                provenances::AMBIENT_KEYWORD,
            ],
            |row| row.get(0),
        )?;

        tx.execute(
            "INSERT INTO rust_symbol_facets (symbol_id, member_kind, visibility)
            VALUES (?1, ?2, 'pub')
            ON CONFLICT(symbol_id) DO NOTHING;",
            params![sym_id, kind],
        )?;

        keyword_count += 1;
    }

    // 3. Primitive Types
    let mut primitive_count = 0;
    for (prim, target_mod) in PRIMITIVE_TYPES {
        let sym_id: i64 = tx.query_row(
            "INSERT INTO symbols (
                container_id, origin_container_id, name, qualified_name, symbol_kind, visibility, provenance, is_hidden
            )
            VALUES (?1, ?1, ?2, ?3, 'type_alias', ?4, ?5, 0)
            ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
            RETURNING symbol_id;",
            params![
                ambient_container_id,
                format!("type:{}", prim),
                format!("<ambient>::{}", prim),
                visibilities::PUBLIC,
                provenances::AMBIENT_PRELUDE,
            ],
            |row| row.get(0),
        )?;

        tx.execute(
            "INSERT INTO rust_symbol_facets (symbol_id, member_kind, visibility)
            VALUES (?1, 'type_alias', 'pub')
            ON CONFLICT(symbol_id) DO NOTHING;",
            params![sym_id],
        )?;

        tx.execute(
            "INSERT INTO symbol_aliases (source_container_id, exposed_name, target_module_name, target_symbol_name, alias_kind, is_in_dunder_all)
            VALUES (?1, ?2, ?3, ?2, 'primitive_type', 0)
            ON CONFLICT(source_container_id, exposed_name) DO UPDATE SET target_module_name = excluded.target_module_name;",
            params![ambient_container_id, prim, target_mod],
        )?;

        primitive_count += 1;
    }

    // 4. Prelude Types, Traits, and Macros
    let mut prelude_count = 0;

    for (name, kind, target_mod) in PRELUDE_TYPES {
        let sym_id: i64 = tx.query_row(
            "INSERT INTO symbols (
                container_id, origin_container_id, name, qualified_name, symbol_kind, visibility, provenance, is_hidden
            )
            VALUES (?1, ?1, ?2, ?3, ?4, ?5, ?6, 0)
            ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
            RETURNING symbol_id;",
            params![
                ambient_container_id,
                name,
                format!("<ambient>::{}", name),
                kind,
                visibilities::PUBLIC,
                provenances::AMBIENT_PRELUDE,
            ],
            |row| row.get(0),
        )?;

        tx.execute(
            "INSERT INTO rust_symbol_facets (symbol_id, member_kind, visibility)
            VALUES (?1, ?2, 'pub')
            ON CONFLICT(symbol_id) DO NOTHING;",
            params![sym_id, kind],
        )?;

        tx.execute(
            "INSERT INTO symbol_aliases (source_container_id, exposed_name, target_module_name, target_symbol_name, alias_kind, is_in_dunder_all)
            VALUES (?1, ?2, ?3, ?2, 'prelude_import', 0)
            ON CONFLICT(source_container_id, exposed_name) DO UPDATE SET target_module_name = excluded.target_module_name;",
            params![ambient_container_id, name, target_mod],
        )?;

        prelude_count += 1;
    }

    for (name, target_mod) in PRELUDE_TRAITS {
        let sym_id: i64 = tx.query_row(
            "INSERT INTO symbols (
                container_id, origin_container_id, name, qualified_name, symbol_kind, visibility, provenance, is_hidden
            )
            VALUES (?1, ?1, ?2, ?3, 'trait', ?4, ?5, 0)
            ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
            RETURNING symbol_id;",
            params![
                ambient_container_id,
                format!("trait:{}", name),
                format!("<ambient>::{}", name),
                visibilities::PUBLIC,
                provenances::AMBIENT_PRELUDE,
            ],
            |row| row.get(0),
        )?;

        tx.execute(
            "INSERT INTO rust_symbol_facets (symbol_id, member_kind, visibility)
            VALUES (?1, 'trait', 'pub')
            ON CONFLICT(symbol_id) DO NOTHING;",
            params![sym_id],
        )?;

        tx.execute(
            "INSERT INTO symbol_aliases (source_container_id, exposed_name, target_module_name, target_symbol_name, alias_kind, is_in_dunder_all)
            VALUES (?1, ?2, ?3, ?2, 'prelude_trait', 0)
            ON CONFLICT(source_container_id, exposed_name) DO UPDATE SET target_module_name = excluded.target_module_name;",
            params![ambient_container_id, name, target_mod],
        )?;

        prelude_count += 1;
    }

    for m in PRELUDE_MACROS {
        let sym_id: i64 = tx.query_row(
            "INSERT INTO symbols (
                container_id, origin_container_id, name, qualified_name, symbol_kind, visibility, provenance, is_hidden
            )
            VALUES (?1, ?1, ?2, ?3, 'macro', ?4, ?5, 0)
            ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
            RETURNING symbol_id;",
            params![
                ambient_container_id,
                m,
                format!("<ambient>::{}", m),
                visibilities::PUBLIC,
                provenances::AMBIENT_PRELUDE,
            ],
            |row| row.get(0),
        )?;

        tx.execute(
            "INSERT INTO rust_symbol_facets (symbol_id, member_kind, visibility)
            VALUES (?1, 'macro', 'pub')
            ON CONFLICT(symbol_id) DO NOTHING;",
            params![sym_id],
        )?;

        prelude_count += 1;
    }

    tx.commit()?;
    Ok((keyword_count, primitive_count, prelude_count))
}
