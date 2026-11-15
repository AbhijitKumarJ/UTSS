/*---
id: rust_05_ownership_and_self_kinds
title: "Ownership & Borrowing in Methods: Receiver Kinds (&self, &mut self, self)"
target_language: rust
variant_compatibility:
  - "*"
suite: tutoring
level: Advanced
sequence: 5
category: "Ownership & Borrowing"
pedagogical_rationale: |
  Rust's borrow checker enforces ownership semantics directly on method receivers:
  - `&self`: Shared immutable borrow (read-only access; can be called concurrently).
  - `&mut self`: Exclusive mutable borrow (allows in-place mutation; enforces single-writer guarantee).
  - `self`: Consumes ownership (moves the value into the method, typically used in builder patterns or `into_*` conversions).
  - Associated functions (no self): Static constructors like `new()`.
  This query inspects methods and associated functions grouped by their self receiver kinds.
guided_experiments:
  - "Filter for mutating methods: `WHERE rf.self_kind = '&mut self'`."
  - "Filter for consuming methods that take ownership: `WHERE rf.self_kind = 'self'`."
---*/
SELECT 
    s.name AS method_name,
    c.short_name AS target_type,
    rf.self_kind,
    rf.visibility,
    cal.return_type_expr,
    cal.raw_signature
FROM symbols s
JOIN rust_symbol_facets rf ON s.symbol_id = rf.symbol_id
LEFT JOIN callables cal ON s.symbol_id = cal.symbol_id
JOIN containers c ON s.container_id = c.container_id
WHERE rf.self_kind IS NOT NULL
ORDER BY rf.self_kind ASC, c.short_name ASC, s.name ASC
LIMIT 30;
