use std::collections::HashMap;
use std::path::Path;
use rusqlite::{params, Connection, Result};
use syn::spanned::Spanned;
use syn::{
    parse_file, Attribute, Fields, FnArg, ImplItem, Item, ItemEnum, ItemFn, ItemImpl, ItemStruct,
    ItemTrait, ItemUse, UseTree, Visibility,
};
use walkdir::WalkDir;
use crate::models::*;
use crate::stratum0_ambient::{ensure_distribution, ensure_environment};

pub const EMBEDDED_DEMO_WORKSPACE: &[(&str, &str)] = &[
    (
        "Cargo.toml",
        r#"[package]
name = "commerce_engine"
version = "0.1.0"
edition = "2021"

[dependencies]
"#,
    ),
    (
        "src/lib.rs",
        r#"pub mod models;
pub mod errors;
pub mod services;

pub use models::{Order, OrderStatus, Customer};
pub use services::OrderService;
"#,
    ),
    (
        "src/models.rs",
        r#"#[derive(Debug, Clone, PartialEq, Eq)]
pub enum OrderStatus {
    Pending,
    Processing,
    Shipped,
    Delivered,
    Cancelled,
}

#[derive(Debug, Clone)]
pub struct Order {
    pub order_id: String,
    pub customer_id: String,
    pub subtotal: f64,
    pub tax_rate: f64,
    pub status: OrderStatus,
}

impl Order {
    pub fn new(order_id: String, customer_id: String, subtotal: f64) -> Self {
        Self {
            order_id,
            customer_id,
            subtotal,
            tax_rate: 0.08,
            status: OrderStatus::Pending,
        }
    }

    pub fn calculate_total(&self) -> f64 {
        self.subtotal * (1.0 + self.tax_rate)
    }
}

pub struct Customer {
    pub customer_id: String,
    pub name: String,
    pub email: String,
    secret_token: String,
}

impl Customer {
    pub fn new(customer_id: String, name: String, email: String, secret_token: String) -> Self {
        Self {
            customer_id,
            name,
            email,
            secret_token,
        }
    }

    pub fn validate_token(&self, token: &str) -> bool {
        self.secret_token == token
    }
}
"#,
    ),
    (
        "src/errors.rs",
        r#"use std::fmt;

#[derive(Debug, Clone)]
pub enum CommerceError {
    OrderNotFound(String),
    InvalidToken,
    DatabaseError(String),
}

impl fmt::Display for CommerceError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CommerceError::OrderNotFound(id) => write!(f, "Order {} not found", id),
            CommerceError::InvalidToken => write!(f, "Invalid authentication token"),
            CommerceError::DatabaseError(msg) => write!(f, "Database error: {}", msg),
        }
    }
}

impl std::error::Error for CommerceError {}
"#,
    ),
    (
        "src/services.rs",
        r#"use crate::errors::CommerceError;
use crate::models::{Order, OrderStatus};

pub trait OrderService {
    fn process_order(&mut self, order_id: &str) -> Result<Order, CommerceError>;
    fn cancel_order(&mut self, order_id: &str) -> bool;
}

pub struct LocalOrderService {
    orders: Vec<Order>,
}

impl LocalOrderService {
    pub fn new() -> Self {
        Self { orders: Vec::new() }
    }

    pub fn add_order(&mut self, order: Order) {
        self.orders.push(order);
    }
}

impl OrderService for LocalOrderService {
    fn process_order(&mut self, order_id: &str) -> Result<Order, CommerceError> {
        let order = self
            .orders
            .iter_mut()
            .find(|o| o.order_id == order_id)
            .ok_or_else(|| CommerceError::OrderNotFound(order_id.to_string()))?;

        order.status = OrderStatus::Processing;
        Ok(order.clone())
    }

    fn cancel_order(&mut self, order_id: &str) -> bool {
        if let Some(order) = self.orders.iter_mut().find(|o| o.order_id == order_id) {
            order.status = OrderStatus::Cancelled;
            true
        } else {
            false
        }
    }
}

pub fn filter_pending<'a>(orders: &'a [Order]) -> impl Iterator<Item = &'a Order> {
    orders.iter().filter(|o| o.status == OrderStatus::Pending)
}
"#,
    ),
];

pub fn harvest_demo_workspace(conn: &mut Connection) -> Result<(usize, usize, usize)> {
    let files: HashMap<String, String> = EMBEDDED_DEMO_WORKSPACE
        .iter()
        .filter(|(path, _)| path.ends_with(".rs"))
        .map(|(path, content)| (path.to_string(), content.to_string()))
        .collect();

    harvest_virtual_files(conn, "commerce_engine", &files)
}

pub fn harvest_workspace_dir(
    conn: &mut Connection,
    workspace_root: &Path,
    crate_name: &str,
) -> Result<(usize, usize, usize)> {
    let mut files = HashMap::new();
    for entry in WalkDir::new(workspace_root).into_iter().filter_map(|e| e.ok()) {
        let p = entry.path();
        if p.is_file() && p.extension().map_or(false, |ext| ext == "rs") {
            let rel = p
                .strip_prefix(workspace_root)
                .unwrap_or(p)
                .to_string_lossy()
                .to_string();
            if let Ok(content) = std::fs::read_to_string(p) {
                files.insert(rel, content);
            }
        }
    }
    harvest_virtual_files(conn, crate_name, &files)
}

pub fn harvest_virtual_files(
    conn: &mut Connection,
    crate_name: &str,
    files: &HashMap<String, String>,
) -> Result<(usize, usize, usize)> {
    let env_id = ensure_environment(conn)?;
    let dist_id = ensure_distribution(
        conn,
        env_id,
        strata::WORKSPACE,
        crate_name,
        "0.1.0",
        Some("Workspace source code harvested via syn pure AST"),
    )?;

    let mut total_containers = 0;
    let mut total_symbols = 0;
    let mut total_callables = 0;

    // 1. Root Crate Container
    let crate_container_id: i64 = conn.query_row(
        "INSERT INTO containers (
            dist_id, parent_container_id, container_kind, qualified_name, short_name, requires_import, visibility, is_hidden
        )
        VALUES (?1, NULL, ?2, ?3, ?3, 1, ?4, 0)
        ON CONFLICT(dist_id, qualified_name) DO UPDATE SET container_kind = excluded.container_kind
        RETURNING container_id;",
        params![dist_id, container_kinds::CRATE, crate_name, visibilities::PUBLIC],
        |row| row.get(0),
    )?;

    conn.execute(
        "INSERT INTO rust_container_facets (container_id, item_kind, is_pub)
        VALUES (?1, 'crate', 1)
        ON CONFLICT(container_id) DO NOTHING;",
        params![crate_container_id],
    )?;
    total_containers += 1;

    let tx = conn.transaction()?;

    for (rel_path, content) in files {
        let file_ast = match parse_file(content) {
            Ok(ast) => ast,
            Err(_) => continue,
        };

        let mod_short_name = Path::new(rel_path)
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("module");

        let mod_qname = if mod_short_name == "lib" || mod_short_name == "main" {
            crate_name.to_string()
        } else {
            format!("{}::{}", crate_name, mod_short_name)
        };

        let current_mod_container_id: i64 = if mod_qname == crate_name {
            crate_container_id
        } else {
            let m_id: i64 = tx.query_row(
                "INSERT INTO containers (
                    dist_id, parent_container_id, container_kind, qualified_name, short_name,
                    requires_import, visibility, is_hidden, physical_path
                )
                VALUES (?1, ?2, ?3, ?4, ?5, 1, ?6, 0, ?7)
                ON CONFLICT(dist_id, qualified_name) DO UPDATE SET physical_path = excluded.physical_path
                RETURNING container_id;",
                params![
                    dist_id,
                    crate_container_id,
                    container_kinds::MODULE,
                    mod_qname,
                    mod_short_name,
                    visibilities::PUBLIC,
                    rel_path,
                ],
                |row| row.get(0),
            )?;

            tx.execute(
                "INSERT INTO rust_container_facets (container_id, item_kind, is_pub)
                VALUES (?1, 'module', 1)
                ON CONFLICT(container_id) DO NOTHING;",
                params![m_id],
            )?;
            total_containers += 1;
            m_id
        };

        for item in &file_ast.items {
            match item {
                Item::Struct(s) => {
                    let (c_inc, s_inc) = handle_struct(&tx, dist_id, current_mod_container_id, &mod_qname, rel_path, s)?;
                    total_containers += c_inc;
                    total_symbols += s_inc;
                }
                Item::Enum(e) => {
                    let (c_inc, s_inc) = handle_enum(&tx, dist_id, current_mod_container_id, &mod_qname, rel_path, e)?;
                    total_containers += c_inc;
                    total_symbols += s_inc;
                }
                Item::Trait(t) => {
                    let (c_inc, s_inc, call_inc) = handle_trait(&tx, dist_id, current_mod_container_id, &mod_qname, rel_path, t)?;
                    total_containers += c_inc;
                    total_symbols += s_inc;
                    total_callables += call_inc;
                }
                Item::Fn(f) => {
                    let (s_inc, call_inc) = handle_free_function(&tx, current_mod_container_id, &mod_qname, rel_path, f)?;
                    total_symbols += s_inc;
                    total_callables += call_inc;
                }
                Item::Impl(imp) => {
                    let (s_inc, call_inc) = handle_impl_block(&tx, dist_id, &mod_qname, rel_path, imp)?;
                    total_symbols += s_inc;
                    total_callables += call_inc;
                }
                Item::Use(u) => {
                    handle_use_directive(&tx, current_mod_container_id, u)?;
                }
                _ => {}
            }
        }
    }

    tx.commit()?;
    Ok((total_containers, total_symbols, total_callables))
}

fn extract_attributes(attrs: &[Attribute]) -> Option<String> {
    let list: Vec<String> = attrs
        .iter()
        .map(|a| {
            let path = a
                .path()
                .segments
                .iter()
                .map(|s| s.ident.to_string())
                .collect::<Vec<_>>()
                .join("::");
            path
        })
        .collect();
    if list.is_empty() {
        None
    } else {
        Some(serde_json::to_string(&list).unwrap_or_default())
    }
}

fn vis_to_str(vis: &Visibility) -> &'static str {
    match vis {
        Visibility::Public(_) => visibilities::PUBLIC,
        Visibility::Restricted(r) => {
            if r.path.is_ident("crate") {
                visibilities::PUB_CRATE
            } else if r.path.is_ident("super") {
                visibilities::PUB_SUPER
            } else {
                visibilities::PRIVATE
            }
        }
        Visibility::Inherited => visibilities::PRIVATE,
    }
}

fn handle_struct(
    tx: &rusqlite::Transaction,
    dist_id: i64,
    parent_container_id: i64,
    parent_qname: &str,
    file_path: &str,
    s: &ItemStruct,
) -> Result<(usize, usize)> {
    let name = s.ident.to_string();
    let qname = format!("{}::{}", parent_qname, name);
    let vis = vis_to_str(&s.vis);
    let span = s.span();
    let attrs = extract_attributes(&s.attrs);

    let container_id: i64 = tx.query_row(
        "INSERT INTO containers (
            dist_id, parent_container_id, container_kind, qualified_name, short_name,
            requires_import, visibility, is_hidden, physical_path,
            start_line, start_col, end_line, end_col
        )
        VALUES (?1, ?2, ?3, ?4, ?5, 1, ?6, ?7, ?8, ?9, ?10, ?11, ?12)
        ON CONFLICT(dist_id, qualified_name) DO UPDATE SET start_line = excluded.start_line
        RETURNING container_id;",
        params![
            dist_id,
            parent_container_id,
            container_kinds::STRUCT,
            qname,
            name,
            vis,
            if vis == visibilities::PRIVATE { 1 } else { 0 },
            file_path,
            span.start().line as i64,
            span.start().column as i64,
            span.end().line as i64,
            span.end().column as i64,
        ],
        |row| row.get(0),
    )?;

    tx.execute(
        "INSERT INTO rust_container_facets (container_id, item_kind, is_pub, attributes_json)
        VALUES (?1, 'struct', ?2, ?3)
        ON CONFLICT(container_id) DO UPDATE SET attributes_json = excluded.attributes_json;",
        params![container_id, if vis == visibilities::PUBLIC { 1 } else { 0 }, attrs],
    )?;

    let mut symbol_count = 0;
    if let Fields::Named(named) = &s.fields {
        for f in &named.named {
            if let Some(f_ident) = &f.ident {
                let f_name = f_ident.to_string();
                let f_vis = vis_to_str(&f.vis);
                let f_span = f.span();
                let f_sym_id: i64 = tx.query_row(
                    "INSERT INTO symbols (
                        container_id, origin_container_id, name, qualified_name,
                        symbol_kind, visibility, provenance, is_hidden,
                        start_line, start_col, end_line, end_col
                    )
                    VALUES (?1, ?1, ?2, ?3, 'struct_field', ?4, 'ast_defined', ?5, ?6, ?7, ?8, ?9)
                    ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
                    RETURNING symbol_id;",
                    params![
                        container_id,
                        f_name,
                        format!("{}::{}", qname, f_name),
                        f_vis,
                        if f_vis == visibilities::PRIVATE { 1 } else { 0 },
                        f_span.start().line as i64,
                        f_span.start().column as i64,
                        f_span.end().line as i64,
                        f_span.end().column as i64,
                    ],
                    |row| row.get(0),
                )?;

                tx.execute(
                    "INSERT INTO rust_symbol_facets (symbol_id, member_kind, visibility)
                    VALUES (?1, 'field', ?2)
                    ON CONFLICT(symbol_id) DO NOTHING;",
                    params![f_sym_id, f_vis],
                )?;
                symbol_count += 1;
            }
        }
    }

    Ok((1, symbol_count))
}

fn handle_enum(
    tx: &rusqlite::Transaction,
    dist_id: i64,
    parent_container_id: i64,
    parent_qname: &str,
    file_path: &str,
    e: &ItemEnum,
) -> Result<(usize, usize)> {
    let name = e.ident.to_string();
    let qname = format!("{}::{}", parent_qname, name);
    let vis = vis_to_str(&e.vis);
    let span = e.span();
    let attrs = extract_attributes(&e.attrs);

    let container_id: i64 = tx.query_row(
        "INSERT INTO containers (
            dist_id, parent_container_id, container_kind, qualified_name, short_name,
            requires_import, visibility, is_hidden, physical_path,
            start_line, start_col, end_line, end_col
        )
        VALUES (?1, ?2, ?3, ?4, ?5, 1, ?6, ?7, ?8, ?9, ?10, ?11, ?12)
        ON CONFLICT(dist_id, qualified_name) DO UPDATE SET start_line = excluded.start_line
        RETURNING container_id;",
        params![
            dist_id,
            parent_container_id,
            container_kinds::ENUM,
            qname,
            name,
            vis,
            if vis == visibilities::PRIVATE { 1 } else { 0 },
            file_path,
            span.start().line as i64,
            span.start().column as i64,
            span.end().line as i64,
            span.end().column as i64,
        ],
        |row| row.get(0),
    )?;

    tx.execute(
        "INSERT INTO rust_container_facets (container_id, item_kind, is_pub, attributes_json)
        VALUES (?1, 'enum', ?2, ?3)
        ON CONFLICT(container_id) DO UPDATE SET attributes_json = excluded.attributes_json;",
        params![container_id, if vis == visibilities::PUBLIC { 1 } else { 0 }, attrs],
    )?;

    let mut symbol_count = 0;
    for v in &e.variants {
        let v_name = v.ident.to_string();
        let v_span = v.span();
        let sym_id: i64 = tx.query_row(
            "INSERT INTO symbols (
                container_id, origin_container_id, name, qualified_name,
                symbol_kind, visibility, provenance, is_hidden,
                start_line, start_col, end_line, end_col
            )
            VALUES (?1, ?1, ?2, ?3, 'enum_variant', 'public', 'ast_defined', 0, ?4, ?5, ?6, ?7)
            ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
            RETURNING symbol_id;",
            params![
                container_id,
                v_name,
                format!("{}::{}", qname, v_name),
                v_span.start().line as i64,
                v_span.start().column as i64,
                v_span.end().line as i64,
                v_span.end().column as i64,
            ],
            |row| row.get(0),
        )?;

        tx.execute(
            "INSERT INTO rust_symbol_facets (symbol_id, member_kind, visibility)
            VALUES (?1, 'variant', 'pub')
            ON CONFLICT(symbol_id) DO NOTHING;",
            params![sym_id],
        )?;
        symbol_count += 1;
    }

    Ok((1, symbol_count))
}

fn handle_trait(
    tx: &rusqlite::Transaction,
    dist_id: i64,
    parent_container_id: i64,
    parent_qname: &str,
    file_path: &str,
    t: &ItemTrait,
) -> Result<(usize, usize, usize)> {
    let name = t.ident.to_string();
    let qname = format!("{}::{}", parent_qname, name);
    let vis = vis_to_str(&t.vis);
    let span = t.span();
    let is_unsafe = t.unsafety.is_some();

    let container_id: i64 = tx.query_row(
        "INSERT INTO containers (
            dist_id, parent_container_id, container_kind, qualified_name, short_name,
            requires_import, visibility, is_hidden, physical_path,
            start_line, start_col, end_line, end_col
        )
        VALUES (?1, ?2, ?3, ?4, ?5, 1, ?6, ?7, ?8, ?9, ?10, ?11, ?12)
        ON CONFLICT(dist_id, qualified_name) DO UPDATE SET start_line = excluded.start_line
        RETURNING container_id;",
        params![
            dist_id,
            parent_container_id,
            container_kinds::TRAIT,
            qname,
            name,
            vis,
            if vis == visibilities::PRIVATE { 1 } else { 0 },
            file_path,
            span.start().line as i64,
            span.start().column as i64,
            span.end().line as i64,
            span.end().column as i64,
        ],
        |row| row.get(0),
    )?;

    tx.execute(
        "INSERT INTO rust_container_facets (container_id, item_kind, is_pub, is_unsafe)
        VALUES (?1, 'trait', ?2, ?3)
        ON CONFLICT(container_id) DO NOTHING;",
        params![container_id, if vis == visibilities::PUBLIC { 1 } else { 0 }, if is_unsafe { 1 } else { 0 }],
    )?;

    let mut symbol_count = 0;
    let mut callable_count = 0;

    for item in &t.items {
        if let syn::TraitItem::Fn(m) = item {
            let m_name = m.sig.ident.to_string();
            let m_span = m.span();
            let raw_sig = quote::quote!(#m).to_string();

            let (self_kind, kind) = analyze_fn_sig(&m.sig);

            let sym_id: i64 = tx.query_row(
                "INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name,
                    symbol_kind, visibility, provenance, is_hidden,
                    start_line, start_col, end_line, end_col
                )
                VALUES (?1, ?1, ?2, ?3, ?4, 'public', 'ast_defined', 0, ?5, ?6, ?7, ?8)
                ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
                RETURNING symbol_id;",
                params![
                    container_id,
                    m_name,
                    format!("{}::{}", qname, m_name),
                    kind,
                    m_span.start().line as i64,
                    m_span.start().column as i64,
                    m_span.end().line as i64,
                    m_span.end().column as i64,
                ],
                |row| row.get(0),
            )?;

            tx.execute(
                "INSERT INTO rust_symbol_facets (symbol_id, member_kind, self_kind, visibility)
                VALUES (?1, ?2, ?3, 'pub')
                ON CONFLICT(symbol_id) DO NOTHING;",
                params![sym_id, kind, self_kind],
            )?;
            symbol_count += 1;

            tx.execute(
                "INSERT INTO callables (symbol_id, is_async, is_static, raw_signature, signature_source)
                VALUES (?1, ?2, ?3, ?4, 'syn_ast')
                ON CONFLICT(symbol_id) DO UPDATE SET raw_signature = excluded.raw_signature;",
                params![
                    sym_id,
                    if m.sig.asyncness.is_some() { 1 } else { 0 },
                    if self_kind == "none" { 1 } else { 0 },
                    raw_sig,
                ],
            )?;
            callable_count += 1;
        }
    }

    Ok((1, symbol_count, callable_count))
}

fn handle_free_function(
    tx: &rusqlite::Transaction,
    parent_container_id: i64,
    parent_qname: &str,
    _file_path: &str,
    f: &ItemFn,
) -> Result<(usize, usize)> {
    let name = f.sig.ident.to_string();
    let qname = format!("{}::{}", parent_qname, name);
    let vis = vis_to_str(&f.vis);
    let span = f.span();
    let raw_sig = quote::quote!(#f).to_string();

    let sym_id: i64 = tx.query_row(
        "INSERT INTO symbols (
            container_id, origin_container_id, name, qualified_name,
            symbol_kind, visibility, provenance, is_hidden,
            start_line, start_col, end_line, end_col
        )
        VALUES (?1, ?1, ?2, ?3, 'function', ?4, 'ast_defined', ?5, ?6, ?7, ?8, ?9)
        ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
        RETURNING symbol_id;",
        params![
            parent_container_id,
            name,
            qname,
            vis,
            if vis == visibilities::PRIVATE { 1 } else { 0 },
            span.start().line as i64,
            span.start().column as i64,
            span.end().line as i64,
            span.end().column as i64,
        ],
        |row| row.get(0),
    )?;

    tx.execute(
        "INSERT INTO rust_symbol_facets (symbol_id, member_kind, self_kind, visibility, is_async, is_const)
        VALUES (?1, 'fn', 'none', ?2, ?3, ?4)
        ON CONFLICT(symbol_id) DO NOTHING;",
        params![
            sym_id,
            vis,
            if f.sig.asyncness.is_some() { 1 } else { 0 },
            if f.sig.constness.is_some() { 1 } else { 0 },
        ],
    )?;

    tx.execute(
        "INSERT INTO callables (symbol_id, is_async, is_static, raw_signature, signature_source)
        VALUES (?1, ?2, 1, ?3, 'syn_ast')
        ON CONFLICT(symbol_id) DO UPDATE SET raw_signature = excluded.raw_signature;",
        params![sym_id, if f.sig.asyncness.is_some() { 1 } else { 0 }, raw_sig],
    )?;

    Ok((1, 1))
}

fn handle_impl_block(
    tx: &rusqlite::Transaction,
    dist_id: i64,
    parent_qname: &str,
    _file_path: &str,
    imp: &ItemImpl,
) -> Result<(usize, usize)> {
    let self_type_name = quote::quote!(#imp.self_ty).to_string();
    let clean_type_name = self_type_name.split('<').next().unwrap_or(&self_type_name).trim().to_string();
    let qname = format!("{}::{}", parent_qname, clean_type_name);

    // Look up target container for this struct/enum
    let container_id_opt: Option<i64> = tx
        .query_row(
            "SELECT container_id FROM containers WHERE dist_id = ?1 AND qualified_name = ?2;",
            params![dist_id, qname],
            |row| row.get(0),
        )
        .ok();

    let target_cid = match container_id_opt {
        Some(cid) => cid,
        None => return Ok((0, 0)),
    };

    let mut symbol_count = 0;
    let mut callable_count = 0;

    for item in &imp.items {
        if let ImplItem::Fn(m) = item {
            let m_name = m.sig.ident.to_string();
            let m_span = m.span();
            let m_vis = vis_to_str(&m.vis);
            let (self_kind, kind) = analyze_fn_sig(&m.sig);
            let raw_sig = quote::quote!(#m).to_string();

            let sym_id: i64 = tx.query_row(
                "INSERT INTO symbols (
                    container_id, origin_container_id, name, qualified_name,
                    symbol_kind, visibility, provenance, is_hidden,
                    start_line, start_col, end_line, end_col
                )
                VALUES (?1, ?1, ?2, ?3, ?4, ?5, 'ast_defined', ?6, ?7, ?8, ?9, ?10)
                ON CONFLICT(container_id, name) DO UPDATE SET symbol_kind = excluded.symbol_kind
                RETURNING symbol_id;",
                params![
                    target_cid,
                    m_name,
                    format!("{}::{}", qname, m_name),
                    kind,
                    m_vis,
                    if m_vis == visibilities::PRIVATE { 1 } else { 0 },
                    m_span.start().line as i64,
                    m_span.start().column as i64,
                    m_span.end().line as i64,
                    m_span.end().column as i64,
                ],
                |row| row.get(0),
            )?;

            tx.execute(
                "INSERT INTO rust_symbol_facets (symbol_id, member_kind, self_kind, visibility, is_async, is_const)
                VALUES (?1, ?2, ?3, ?4, ?5, ?6)
                ON CONFLICT(symbol_id) DO NOTHING;",
                params![
                    sym_id,
                    kind,
                    self_kind,
                    m_vis,
                    if m.sig.asyncness.is_some() { 1 } else { 0 },
                    if m.sig.constness.is_some() { 1 } else { 0 },
                ],
            )?;
            symbol_count += 1;

            tx.execute(
                "INSERT INTO callables (symbol_id, is_async, is_static, raw_signature, signature_source)
                VALUES (?1, ?2, ?3, ?4, 'syn_ast')
                ON CONFLICT(symbol_id) DO UPDATE SET raw_signature = excluded.raw_signature;",
                params![
                    sym_id,
                    if m.sig.asyncness.is_some() { 1 } else { 0 },
                    if self_kind == "none" { 1 } else { 0 },
                    raw_sig,
                ],
            )?;
            callable_count += 1;
        }
    }

    Ok((symbol_count, callable_count))
}

fn handle_use_directive(
    tx: &rusqlite::Transaction,
    container_id: i64,
    u: &ItemUse,
) -> Result<()> {
    fn walk_tree(tx: &rusqlite::Transaction, container_id: i64, prefix: &str, tree: &UseTree) -> Result<()> {
        match tree {
            UseTree::Path(p) => {
                let next_prefix = if prefix.is_empty() {
                    p.ident.to_string()
                } else {
                    format!("{}::{}", prefix, p.ident)
                };
                walk_tree(tx, container_id, &next_prefix, &p.tree)?;
            }
            UseTree::Name(n) => {
                let target_sym = n.ident.to_string();
                let exp_name = target_sym.clone();
                let target_mod = prefix.to_string();

                tx.execute(
                    "INSERT INTO symbol_aliases (source_container_id, exposed_name, target_module_name, target_symbol_name, alias_kind, is_in_dunder_all)
                    VALUES (?1, ?2, ?3, ?4, 'use_import', 0)
                    ON CONFLICT(source_container_id, exposed_name) DO UPDATE SET target_module_name = excluded.target_module_name;",
                    params![container_id, exp_name, target_mod, target_sym],
                )?;
            }
            UseTree::Rename(r) => {
                let target_sym = r.ident.to_string();
                let exp_name = r.rename.to_string();
                let target_mod = prefix.to_string();

                tx.execute(
                    "INSERT INTO symbol_aliases (source_container_id, exposed_name, target_module_name, target_symbol_name, alias_kind, is_in_dunder_all)
                    VALUES (?1, ?2, ?3, ?4, 'use_rename', 0)
                    ON CONFLICT(source_container_id, exposed_name) DO UPDATE SET target_module_name = excluded.target_module_name;",
                    params![container_id, exp_name, target_mod, target_sym],
                )?;
            }
            UseTree::Group(g) => {
                for item in &g.items {
                    walk_tree(tx, container_id, prefix, item)?;
                }
            }
            UseTree::Glob(_) => {
                tx.execute(
                    "INSERT INTO symbol_aliases (source_container_id, exposed_name, target_module_name, target_symbol_name, alias_kind, is_in_dunder_all)
                    VALUES (?1, ?2, ?3, '*', 'use_glob', 0)
                    ON CONFLICT(source_container_id, exposed_name) DO UPDATE SET target_module_name = excluded.target_module_name;",
                    params![container_id, format!("{}::*", prefix), prefix],
                )?;
            }
        }
        Ok(())
    }

    walk_tree(tx, container_id, "", &u.tree)
}

fn analyze_fn_sig(sig: &syn::Signature) -> (&'static str, &'static str) {
    let mut self_kind = "none";
    let mut kind = "associated_fn";

    if let Some(first_arg) = sig.inputs.first() {
        if let FnArg::Receiver(r) = first_arg {
            kind = "method";
            if r.reference.is_some() {
                if r.mutability.is_some() {
                    self_kind = "mut_ref";
                } else {
                    self_kind = "ref";
                }
            } else {
                self_kind = "val";
            }
        }
    }

    (self_kind, kind)
}
