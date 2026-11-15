use rusqlite::{params, Connection, Result};
use crate::models::*;
use crate::stratum0_ambient::{ensure_distribution, ensure_environment};

#[derive(Debug, Clone)]
pub struct StdItemDef {
    pub module: &'static str,
    pub name: &'static str,
    pub kind: &'static str, // "struct", "enum", "trait", "function"
    pub generics: Option<&'static str>,
    pub methods: &'static [StdMethodDef],
}

#[derive(Debug, Clone)]
pub struct StdMethodDef {
    pub name: &'static str,
    pub kind: &'static str, // "method", "associated_fn"
    pub self_kind: &'static str, // "none", "ref", "mut_ref", "val"
    pub signature: &'static str,
    pub return_type: &'static str,
    pub params: &'static [(&'static str, &'static str, &'static str)], // (name, type, pass_kind)
}

pub static RECOMMENDED_STD_ITEMS: &[StdItemDef] = &[
    // 1. std::collections::HashMap
    StdItemDef {
        module: "std::collections",
        name: "HashMap",
        kind: "struct",
        generics: Some(r#"[{"name": "K", "bounds": ["Eq", "Hash"]}, {"name": "V"}]"#),
        methods: &[
            StdMethodDef {
                name: "new",
                kind: "associated_fn",
                self_kind: "none",
                signature: "pub fn new() -> HashMap<K, V>",
                return_type: "HashMap<K, V>",
                params: &[],
            },
            StdMethodDef {
                name: "insert",
                kind: "method",
                self_kind: "mut_ref",
                signature: "pub fn insert(&mut self, k: K, v: V) -> Option<V>",
                return_type: "Option<V>",
                params: &[("&mut self", "&mut Self", "self_mut_ref"), ("k", "K", "val"), ("v", "V", "val")],
            },
            StdMethodDef {
                name: "get",
                kind: "method",
                self_kind: "ref",
                signature: "pub fn get<Q>(&self, k: &Q) -> Option<&V>",
                return_type: "Option<&V>",
                params: &[("&self", "&Self", "self_ref"), ("k", "&Q", "ref")],
            },
            StdMethodDef {
                name: "len",
                kind: "method",
                self_kind: "ref",
                signature: "pub fn len(&self) -> usize",
                return_type: "usize",
                params: &[("&self", "&Self", "self_ref")],
            },
            StdMethodDef {
                name: "is_empty",
                kind: "method",
                self_kind: "ref",
                signature: "pub fn is_empty(&self) -> bool",
                return_type: "bool",
                params: &[("&self", "&Self", "self_ref")],
            },
        ],
    },

    // 2. std::collections::HashSet
    StdItemDef {
        module: "std::collections",
        name: "HashSet",
        kind: "struct",
        generics: Some(r#"[{"name": "T", "bounds": ["Eq", "Hash"]}]"#),
        methods: &[
            StdMethodDef {
                name: "new",
                kind: "associated_fn",
                self_kind: "none",
                signature: "pub fn new() -> HashSet<T>",
                return_type: "HashSet<T>",
                params: &[],
            },
            StdMethodDef {
                name: "insert",
                kind: "method",
                self_kind: "mut_ref",
                signature: "pub fn insert(&mut self, value: T) -> bool",
                return_type: "bool",
                params: &[("&mut self", "&mut Self", "self_mut_ref"), ("value", "T", "val")],
            },
            StdMethodDef {
                name: "contains",
                kind: "method",
                self_kind: "ref",
                signature: "pub fn contains<Q>(&self, value: &Q) -> bool",
                return_type: "bool",
                params: &[("&self", "&Self", "self_ref"), ("value", "&Q", "ref")],
            },
        ],
    },

    // 3. std::vec::Vec
    StdItemDef {
        module: "std::vec",
        name: "Vec",
        kind: "struct",
        generics: Some(r#"[{"name": "T"}]"#),
        methods: &[
            StdMethodDef {
                name: "new",
                kind: "associated_fn",
                self_kind: "none",
                signature: "pub const fn new() -> Vec<T>",
                return_type: "Vec<T>",
                params: &[],
            },
            StdMethodDef {
                name: "push",
                kind: "method",
                self_kind: "mut_ref",
                signature: "pub fn push(&mut self, value: T)",
                return_type: "()",
                params: &[("&mut self", "&mut Self", "self_mut_ref"), ("value", "T", "val")],
            },
            StdMethodDef {
                name: "pop",
                kind: "method",
                self_kind: "mut_ref",
                signature: "pub fn pop(&mut self) -> Option<T>",
                return_type: "Option<T>",
                params: &[("&mut self", "&mut Self", "self_mut_ref")],
            },
            StdMethodDef {
                name: "len",
                kind: "method",
                self_kind: "ref",
                signature: "pub fn len(&self) -> usize",
                return_type: "usize",
                params: &[("&self", "&Self", "self_ref")],
            },
        ],
    },

    // 4. std::string::String
    StdItemDef {
        module: "std::string",
        name: "String",
        kind: "struct",
        generics: None,
        methods: &[
            StdMethodDef {
                name: "new",
                kind: "associated_fn",
                self_kind: "none",
                signature: "pub const fn new() -> String",
                return_type: "String",
                params: &[],
            },
            StdMethodDef {
                name: "from",
                kind: "associated_fn",
                self_kind: "none",
                signature: "pub fn from(s: &str) -> String",
                return_type: "String",
                params: &[("s", "&str", "ref")],
            },
            StdMethodDef {
                name: "push_str",
                kind: "method",
                self_kind: "mut_ref",
                signature: "pub fn push_str(&mut self, string: &str)",
                return_type: "()",
                params: &[("&mut self", "&mut Self", "self_mut_ref"), ("string", "&str", "ref")],
            },
            StdMethodDef {
                name: "as_str",
                kind: "method",
                self_kind: "ref",
                signature: "pub fn as_str(&self) -> &str",
                return_type: "&str",
                params: &[("&self", "&Self", "self_ref")],
            },
            StdMethodDef {
                name: "len",
                kind: "method",
                self_kind: "ref",
                signature: "pub fn len(&self) -> usize",
                return_type: "usize",
                params: &[("&self", "&Self", "self_ref")],
            },
        ],
    },

    // 5. std::fs::File
    StdItemDef {
        module: "std::fs",
        name: "File",
        kind: "struct",
        generics: None,
        methods: &[
            StdMethodDef {
                name: "open",
                kind: "associated_fn",
                self_kind: "none",
                signature: "pub fn open<P: AsRef<Path>>(path: P) -> std::io::Result<File>",
                return_type: "std::io::Result<File>",
                params: &[("path", "P", "val")],
            },
            StdMethodDef {
                name: "create",
                kind: "associated_fn",
                self_kind: "none",
                signature: "pub fn create<P: AsRef<Path>>(path: P) -> std::io::Result<File>",
                return_type: "std::io::Result<File>",
                params: &[("path", "P", "val")],
            },
        ],
    },

    // 6. std::sync::Arc
    StdItemDef {
        module: "std::sync",
        name: "Arc",
        kind: "struct",
        generics: Some(r#"[{"name": "T"}]"#),
        methods: &[
            StdMethodDef {
                name: "new",
                kind: "associated_fn",
                self_kind: "none",
                signature: "pub fn new(data: T) -> Arc<T>",
                return_type: "Arc<T>",
                params: &[("data", "T", "val")],
            },
            StdMethodDef {
                name: "clone",
                kind: "method",
                self_kind: "ref",
                signature: "pub fn clone(this: &Self) -> Arc<T>",
                return_type: "Arc<T>",
                params: &[("this", "&Self", "self_ref")],
            },
        ],
    },

    // 7. std::sync::Mutex
    StdItemDef {
        module: "std::sync",
        name: "Mutex",
        kind: "struct",
        generics: Some(r#"[{"name": "T"}]"#),
        methods: &[
            StdMethodDef {
                name: "new",
                kind: "associated_fn",
                self_kind: "none",
                signature: "pub const fn new(t: T) -> Mutex<T>",
                return_type: "Mutex<T>",
                params: &[("t", "T", "val")],
            },
            StdMethodDef {
                name: "lock",
                kind: "method",
                self_kind: "ref",
                signature: "pub fn lock(&self) -> std::sync::LockResult<MutexGuard<'_, T>>",
                return_type: "LockResult<MutexGuard<'_, T>>",
                params: &[("&self", "&Self", "self_ref")],
            },
        ],
    },

    // 8. std::path::PathBuf
    StdItemDef {
        module: "std::path",
        name: "PathBuf",
        kind: "struct",
        generics: None,
        methods: &[
            StdMethodDef {
                name: "new",
                kind: "associated_fn",
                self_kind: "none",
                signature: "pub const fn new() -> PathBuf",
                return_type: "PathBuf",
                params: &[],
            },
            StdMethodDef {
                name: "push",
                kind: "method",
                self_kind: "mut_ref",
                signature: "pub fn push<P: AsRef<Path>>(&mut self, path: P)",
                return_type: "()",
                params: &[("&mut self", "&mut Self", "self_mut_ref"), ("path", "P", "val")],
            },
            StdMethodDef {
                name: "as_path",
                kind: "method",
                self_kind: "ref",
                signature: "pub fn as_path(&self) -> &Path",
                return_type: "&Path",
                params: &[("&self", "&Self", "self_ref")],
            },
        ],
    },

    // 9. std::time::Duration
    StdItemDef {
        module: "std::time",
        name: "Duration",
        kind: "struct",
        generics: None,
        methods: &[
            StdMethodDef {
                name: "from_secs",
                kind: "associated_fn",
                self_kind: "none",
                signature: "pub const fn from_secs(secs: u64) -> Duration",
                return_type: "Duration",
                params: &[("secs", "u64", "val")],
            },
            StdMethodDef {
                name: "from_millis",
                kind: "associated_fn",
                self_kind: "none",
                signature: "pub const fn from_millis(millis: u64) -> Duration",
                return_type: "Duration",
                params: &[("millis", "u64", "val")],
            },
            StdMethodDef {
                name: "as_secs",
                kind: "method",
                self_kind: "ref",
                signature: "pub const fn as_secs(&self) -> u64",
                return_type: "u64",
                params: &[("&self", "&Self", "self_ref")],
            },
        ],
    },

    // 10. std::io::Read (Trait)
    StdItemDef {
        module: "std::io",
        name: "Read",
        kind: "trait",
        generics: None,
        methods: &[
            StdMethodDef {
                name: "read",
                kind: "method",
                self_kind: "mut_ref",
                signature: "fn read(&mut self, buf: &mut [u8]) -> std::io::Result<usize>",
                return_type: "std::io::Result<usize>",
                params: &[("&mut self", "&mut Self", "self_mut_ref"), ("buf", "&mut [u8]", "mut_ref")],
            },
            StdMethodDef {
                name: "read_to_end",
                kind: "method",
                self_kind: "mut_ref",
                signature: "fn read_to_end(&mut self, buf: &mut Vec<u8>) -> std::io::Result<usize>",
                return_type: "std::io::Result<usize>",
                params: &[("&mut self", "&mut Self", "self_mut_ref"), ("buf", "&mut Vec<u8>", "mut_ref")],
            },
        ],
    },

    // 11. std::io::Write (Trait)
    StdItemDef {
        module: "std::io",
        name: "Write",
        kind: "trait",
        generics: None,
        methods: &[
            StdMethodDef {
                name: "write",
                kind: "method",
                self_kind: "mut_ref",
                signature: "fn write(&mut self, buf: &[u8]) -> std::io::Result<usize>",
                return_type: "std::io::Result<usize>",
                params: &[("&mut self", "&mut Self", "self_mut_ref"), ("buf", "&[u8]", "ref")],
            },
            StdMethodDef {
                name: "flush",
                kind: "method",
                self_kind: "mut_ref",
                signature: "fn flush(&mut self) -> std::io::Result<()>",
                return_type: "std::io::Result<()>",
                params: &[("&mut self", "&mut Self", "self_mut_ref")],
            },
        ],
    },

    // 12. std::thread
    StdItemDef {
        module: "std::thread",
        name: "sleep",
        kind: "function",
        generics: None,
        methods: &[
            StdMethodDef {
                name: "sleep",
                kind: "associated_fn",
                self_kind: "none",
                signature: "pub fn sleep(dur: Duration)",
                return_type: "()",
                params: &[("dur", "Duration", "val")],
            },
        ],
    },
];

pub static FULL_STD_MODULES: &[&str] = &[
    "std::any", "std::array", "std::cell", "std::char", "std::clone", "std::cmp",
    "std::collections", "std::convert", "std::default", "std::env", "std::error",
    "std::f32", "std::f64", "std::ffi", "std::fmt", "std::fs", "std::future",
    "std::hash", "std::hint", "std::io", "std::iter", "std::marker", "std::mem",
    "std::net", "std::num", "std::ops", "std::option", "std::os", "std::panic",
    "std::path", "std::pin", "std::process", "std::ptr", "std::rc", "std::result",
    "std::slice", "std::str", "std::string", "std::sync", "std::task", "std::thread",
    "std::time", "std::vec"
];

pub fn harvest(conn: &mut Connection, full_bcl: bool) -> Result<(usize, usize, usize)> {
    let env_id = ensure_environment(conn)?;
    let dist_id = ensure_distribution(
        conn,
        env_id,
        strata::STDLIB,
        "std",
        "1.85.0",
        Some("Rust Standard Library (std / core / alloc)"),
    )?;

    let mut container_count = 0;
    let mut symbol_count = 0;
    let mut callable_count = 0;

    let mut module_ids = std::collections::HashMap::new();

    // 1. Ensure Standard Library Root Crate Container
    let std_crate_id: i64 = conn.query_row(
        "INSERT INTO containers (
            dist_id, parent_container_id, container_kind, qualified_name, short_name, requires_import, visibility, is_hidden
        )
        VALUES (?1, NULL, ?2, 'std', 'std', 1, ?3, 0)
        ON CONFLICT(dist_id, qualified_name) DO UPDATE SET container_kind = excluded.container_kind
        RETURNING container_id;",
        params![dist_id, container_kinds::CRATE, visibilities::PUBLIC],
        |row| row.get(0),
    )?;

    conn.execute(
        "INSERT INTO rust_container_facets (container_id, item_kind, is_pub)
        VALUES (?1, 'crate', 1)
        ON CONFLICT(container_id) DO NOTHING;",
        params![std_crate_id],
    )?;
    container_count += 1;

    let modules_to_ensure: Vec<&str> = if full_bcl {
        FULL_STD_MODULES.to_vec()
    } else {
        RECOMMENDED_STD_ITEMS.iter().map(|i| i.module).collect()
    };

    // Ensure modules
    for mod_name in &modules_to_ensure {
        if !module_ids.contains_key(*mod_name) {
            let short_name = mod_name.split("::").last().unwrap_or(mod_name);
            let mod_id: i64 = conn.query_row(
                "INSERT INTO containers (
                    dist_id, parent_container_id, container_kind, qualified_name, short_name, requires_import, visibility, is_hidden
                )
                VALUES (?1, ?2, ?3, ?4, ?5, 1, ?6, 0)
                ON CONFLICT(dist_id, qualified_name) DO UPDATE SET container_kind = excluded.container_kind
                RETURNING container_id;",
                params![
                    dist_id,
                    std_crate_id,
                    container_kinds::MODULE,
                    mod_name,
                    short_name,
                    visibilities::PUBLIC,
                ],
                |row| row.get(0),
            )?;

            conn.execute(
                "INSERT INTO rust_container_facets (container_id, item_kind, is_pub)
                VALUES (?1, 'module', 1)
                ON CONFLICT(container_id) DO NOTHING;",
                params![mod_id],
            )?;

            module_ids.insert(mod_name.to_string(), mod_id);
            container_count += 1;
        }
    }

    // 2. Harvest Items & Types
    let tx = conn.transaction()?;

    for item in RECOMMENDED_STD_ITEMS {
        let parent_mod_id = module_ids.get(item.module).copied().unwrap_or(std_crate_id);
        let qname = format!("{}::{}", item.module, item.name);

        if item.kind == "function" {
            // Standalone module function
            let sym_id: i64 = tx.query_row(
                "INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name, symbol_kind, visibility, provenance, is_hidden
                )
                VALUES (?1, ?1, ?2, ?3, 'function', ?4, ?5, 0)
                ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
                RETURNING symbol_id;",
                params![
                    parent_mod_id,
                    item.name,
                    qname,
                    visibilities::PUBLIC,
                    provenances::STD_ITEM,
                ],
                |row| row.get(0),
            )?;

            tx.execute(
                "INSERT INTO rust_symbol_facets (symbol_id, member_kind, visibility)
                VALUES (?1, 'fn', 'pub')
                ON CONFLICT(symbol_id) DO NOTHING;",
                params![sym_id],
            )?;
            symbol_count += 1;

            if let Some(m) = item.methods.first() {
                tx.execute(
                    "INSERT INTO callables (symbol_id, is_async, is_static, return_type_expr, raw_signature, signature_source)
                    VALUES (?1, 0, 1, ?2, ?3, 'rust_std_metadata')
                    ON CONFLICT(symbol_id) DO UPDATE SET raw_signature = excluded.raw_signature;",
                    params![sym_id, m.return_type, m.signature],
                )?;
                callable_count += 1;

                for (idx, (p_name, p_type, pass_kind)) in m.params.iter().enumerate() {
                    tx.execute(
                        "INSERT INTO parameters (callable_symbol_id, ordinal, name, pass_kind, type_expr, type_source)
                        VALUES (?1, ?2, ?3, ?4, ?5, 'rust_std_metadata');",
                        params![sym_id, idx as i64, p_name, pass_kind, p_type],
                    )?;
                }
            }
            continue;
        }

        // Struct, Enum, Trait Container
        let item_container_id: i64 = tx.query_row(
            "INSERT INTO containers (
                dist_id, parent_container_id, container_kind, qualified_name, short_name, requires_import, visibility, is_hidden
            )
            VALUES (?1, ?2, ?3, ?4, ?5, 1, ?6, 0)
            ON CONFLICT(dist_id, qualified_name) DO UPDATE SET container_kind = excluded.container_kind
            RETURNING container_id;",
            params![
                dist_id,
                parent_mod_id,
                item.kind,
                qname,
                item.name,
                visibilities::PUBLIC,
            ],
            |row| row.get(0),
        )?;

        tx.execute(
            "INSERT INTO rust_container_facets (container_id, item_kind, is_pub, generics_json)
            VALUES (?1, ?2, 1, ?3)
            ON CONFLICT(container_id) DO UPDATE SET generics_json = excluded.generics_json;",
            params![item_container_id, item.kind, item.generics],
        )?;
        container_count += 1;

        // Methods & Associated Functions
        for m in item.methods {
            let method_qname = format!("{}::{}", qname, m.name);
            let sym_id: i64 = tx.query_row(
                "INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name, symbol_kind, visibility, provenance, is_hidden
                )
                VALUES (?1, ?1, ?2, ?3, ?4, ?5, ?6, 0)
                ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
                RETURNING symbol_id;",
                params![
                    item_container_id,
                    m.name,
                    method_qname,
                    m.kind,
                    visibilities::PUBLIC,
                    provenances::STD_ITEM,
                ],
                |row| row.get(0),
            )?;

            tx.execute(
                "INSERT INTO rust_symbol_facets (symbol_id, member_kind, self_kind, visibility)
                VALUES (?1, ?2, ?3, 'pub')
                ON CONFLICT(symbol_id) DO NOTHING;",
                params![sym_id, m.kind, m.self_kind],
            )?;
            symbol_count += 1;

            tx.execute(
                "INSERT INTO callables (symbol_id, is_async, is_static, return_type_expr, raw_signature, signature_source)
                VALUES (?1, 0, ?2, ?3, ?4, 'rust_std_metadata')
                ON CONFLICT(symbol_id) DO UPDATE SET raw_signature = excluded.raw_signature;",
                params![
                    sym_id,
                    if m.self_kind == "none" { 1 } else { 0 },
                    m.return_type,
                    m.signature,
                ],
            )?;
            callable_count += 1;

            for (idx, (p_name, p_type, pass_kind)) in m.params.iter().enumerate() {
                tx.execute(
                    "INSERT INTO parameters (callable_symbol_id, ordinal, name, pass_kind, type_expr, type_source)
                    VALUES (?1, ?2, ?3, ?4, ?5, 'rust_std_metadata');",
                    params![sym_id, idx as i64, p_name, pass_kind, p_type],
                )?;
            }
        }
    }

    tx.commit()?;
    Ok((container_count, symbol_count, callable_count))
}
