/*---
id: go_03_struct_composition_and_embedding
title: "Struct Composition: Embedded Fields over Inheritance"
target_language: go
variant_compatibility:
  - "*"
suite: tutoring
level: Intermediate
sequence: 3
category: "Data Structures & Composition"
pedagogical_rationale: |
  Go famously rejects class inheritance in favor of composition.
  A struct can embed another struct or interface without specifying a field name, promoting the inner type's fields
  and methods directly onto the outer struct (embedded/anonymous fields).
  This query lists struct definitions, highlighting embedded fields and counting declared struct fields.
guided_experiments:
  - "Find structs that embed inner types: `WHERE gf.embedded_fields_json != '[]'`."
  - "Check which package declares each struct by filtering on `gf.package_name`."
---*/
SELECT 
    c.short_name AS struct_name,
    gf.package_name,
    gf.embedded_fields_json AS embedded_fields,
    gf.is_exported,
    COUNT(s.symbol_id) AS field_count
FROM containers c
JOIN go_container_facets gf ON c.container_id = gf.container_id
LEFT JOIN symbols s ON c.container_id = s.container_id
WHERE c.container_kind = 'struct'
GROUP BY c.container_id
ORDER BY (gf.embedded_fields_json != '[]') DESC, field_count DESC, c.short_name ASC
LIMIT 30;
