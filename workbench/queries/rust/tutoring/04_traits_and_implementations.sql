/*---
id: rust_04_traits_and_implementations
title: "The Trait System: Traits, Auto-Traits & Generics"
target_language: rust
variant_compatibility:
  - "*"
suite: tutoring
level: Intermediate
sequence: 4
category: "Traits & Generics"
pedagogical_rationale: |
  Traits are Rust's sole mechanism for defining shared behavior and generic constraints:
  - Traits specify method signatures that types can implement via `impl Trait for Type`.
  - Auto-Traits: Compiler-synthesized traits like `Send`, `Sync`, and `Unpin` that automatically apply when all fields satisfy them.
  - Where Clauses: Complex trait bounds for generic types.
  This query inspects declared traits, auto-trait status, generics, and method counts.
guided_experiments:
  - "Filter for auto-traits: `WHERE rf.is_auto_trait = 1`."
  - "Check traits with generic bounds: `WHERE rf.where_clause_json IS NOT NULL`."
lab_challenge:
  objective: "Write a SQL query that retrieves all declared Rust traits, showing the trait name, whether it is unsafe, and the count of declared methods, ordered by declared methods descending."
  starter_sql: |
    -- Lab Challenge: Inspect Rust traits and method counts
    SELECT 
        c.short_name AS trait_name,
        rf.is_unsafe,
        COUNT(s.symbol_id) AS declared_methods
    FROM containers c
    JOIN rust_container_facets rf ON c.container_id = rf.container_id
    LEFT JOIN symbols s ON c.container_id = s.container_id
    WHERE c.container_kind = 'trait'
    GROUP BY c.container_id
    ORDER BY declared_methods DESC, c.short_name ASC;
  solution_sql: |
    SELECT 
        c.short_name AS trait_name,
        rf.is_unsafe,
        COUNT(s.symbol_id) AS declared_methods
    FROM containers c
    JOIN rust_container_facets rf ON c.container_id = rf.container_id
    LEFT JOIN symbols s ON c.container_id = s.container_id
    WHERE c.container_kind = 'trait'
    GROUP BY c.container_id
    ORDER BY declared_methods DESC, c.short_name ASC;
  expected_columns:
    - trait_name
    - is_unsafe
    - declared_methods
  min_rows: 1
  xp_reward: 75
  hint: "Filter with WHERE c.container_kind = 'trait' and GROUP BY c.container_id."
---*/
SELECT 
    c.short_name AS trait_name,
    rf.is_pub,
    rf.is_auto_trait,
    rf.is_unsafe,
    rf.generics_json AS generics,
    rf.where_clause_json AS where_clause,
    COUNT(s.symbol_id) AS declared_methods
FROM containers c
JOIN rust_container_facets rf ON c.container_id = rf.container_id
LEFT JOIN symbols s ON c.container_id = s.container_id
WHERE c.container_kind = 'trait'
GROUP BY c.container_id
ORDER BY declared_methods DESC, c.short_name ASC;
