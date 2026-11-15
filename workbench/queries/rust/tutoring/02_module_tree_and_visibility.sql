/*---
id: rust_02_module_tree_and_visibility
title: "Module Trees & Visibility Boundaries: pub, pub(crate) & Private"
target_language: rust
variant_compatibility:
  - "*"
suite: tutoring
level: Basic
sequence: 2
category: "Modules & Visibility"
pedagogical_rationale: |
  Rust code is organized in a hierarchical tree of modules starting at the crate root (`lib.rs` / `main.rs`):
  - Items are private to their enclosing module by default.
  - `pub`: Exported to the public API surface.
  - `pub(crate)`: Visible within the entire crate, but hidden from external consumers.
  This query inspects containers across the crate hierarchy, checking visibility flags and symbol populations.
guided_experiments:
  - "Filter for strictly crate-internal types: `WHERE rf.is_pub_crate = 1`."
  - "Look for modules and their child symbol counts by filtering `WHERE c.container_kind = 'module'`."
---*/
SELECT 
    c.container_kind,
    c.short_name AS item_name,
    rf.is_pub,
    rf.is_pub_crate,
    rf.is_unsafe,
    COUNT(s.symbol_id) AS symbol_count
FROM containers c
JOIN rust_container_facets rf ON c.container_id = rf.container_id
LEFT JOIN symbols s ON c.container_id = s.container_id
WHERE c.container_kind != 'ambient_scope'
GROUP BY c.container_id
ORDER BY c.container_kind ASC, symbol_count DESC
LIMIT 30;
