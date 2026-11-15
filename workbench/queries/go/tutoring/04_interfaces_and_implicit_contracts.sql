/*---
id: go_04_interfaces_and_implicit_contracts
title: "Interface Contracts: Structural Duck Typing & Method Sets"
target_language: go
variant_compatibility:
  - "*"
suite: tutoring
level: Intermediate
sequence: 4
category: "Interfaces & Contracts"
pedagogical_rationale: |
  Interfaces in Go are satisfied implicitly: a concrete type never writes `implements Reader`.
  If a type's method set contains all the signatures declared by an interface, it automatically implements that interface.
  This decoupling enables clean standard library composability (such as `io.Reader`, `io.Writer`).
  This query inspects interface definitions and custom type containers alongside their method signatures.
guided_experiments:
  - "Filter specifically for interface containers: `WHERE c.container_kind = 'interface'`."
  - "Look for single-method interfaces (idiomatic Go interfaces like Reader, Writer, Stringer)."
lab_challenge:
  objective: "Write a SQL query that retrieves all interface and type methods declared across Go packages, showing type name, package name, method name, and visibility, ordered alphabetically by type name and method name."
  starter_sql: |
    -- Lab Challenge: Inspect Go interfaces and method sets
    SELECT 
        c.short_name AS type_name,
        gf.package_name,
        s.name AS method_or_field,
        s.visibility
    FROM containers c
    JOIN go_container_facets gf ON c.container_id = gf.container_id
    JOIN symbols s ON c.container_id = s.container_id
    WHERE c.container_kind IN ('interface', 'type')
    ORDER BY c.short_name ASC, s.name ASC
    LIMIT 30;
  solution_sql: |
    SELECT 
        c.short_name AS type_name,
        gf.package_name,
        s.name AS method_or_field,
        s.visibility
    FROM containers c
    JOIN go_container_facets gf ON c.container_id = gf.container_id
    JOIN symbols s ON c.container_id = s.container_id
    WHERE c.container_kind IN ('interface', 'type')
    ORDER BY c.short_name ASC, s.name ASC
    LIMIT 30;
  expected_columns:
    - type_name
    - package_name
    - method_or_field
    - visibility
  min_rows: 5
  xp_reward: 70
  hint: "Join containers with go_container_facets and symbols WHERE c.container_kind IN ('interface', 'type')."
---*/
SELECT 
    c.short_name AS type_name,
    c.container_kind,
    gf.package_name,
    s.name AS method_or_field,
    s.symbol_kind,
    s.visibility
FROM containers c
JOIN go_container_facets gf ON c.container_id = gf.container_id
JOIN symbols s ON c.container_id = s.container_id
WHERE c.container_kind IN ('interface', 'type')
ORDER BY c.short_name ASC, s.name ASC
LIMIT 30;
