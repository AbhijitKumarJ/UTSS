/*---
id: rust_03_algebraic_data_types_and_variants
title: "Algebraic Data Types: Structs, Enums & Variant Payloads"
target_language: rust
variant_compatibility:
  - "*"
suite: tutoring
level: Intermediate
sequence: 3
category: "Data Types & Modeling"
pedagogical_rationale: |
  Rust data modeling is grounded in Algebraic Data Types (ADTs):
  - Product Types: Structs with named fields or tuple structs (`struct Point(i32, i32)`).
  - Sum Types: Enums where each variant can carry distinct payload types (e.g. `Option<T>`, `Result<T, E>`).
  This query inspects enum variants and struct fields, revealing how types and data are laid out.
guided_experiments:
  - "Filter for only enum variants: `WHERE s.symbol_kind = 'enum_variant'`."
  - "Filter for struct fields across models: `WHERE s.symbol_kind = 'struct_field'`."
---*/
SELECT 
    s.name AS member_name,
    s.symbol_kind,
    s.visibility,
    c.short_name AS enclosing_type,
    c.container_kind
FROM symbols s
JOIN containers c ON s.container_id = c.container_id
WHERE s.symbol_kind IN ('enum_variant', 'struct_field')
ORDER BY s.symbol_kind ASC, c.short_name ASC, s.name ASC
LIMIT 30;
