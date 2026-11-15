/*---
id: cs_02_type_taxonomy_and_containers
title: "Type Taxonomy: Classes, Structs, Records, and Interfaces"
target_language: csharp
variant_compatibility:
  - "*"
suite: tutoring
level: Basic
sequence: 2
category: "Type Taxonomy"
pedagogical_rationale: |
  C# features a rich type system combining reference types (class, record, interface) and value types (struct, enum).
  Furthermore, the C# compiler applies modifiers like `sealed` to prevent derivation and enable JIT devirtualization optimizations,
  and `abstract` to enforce interface contracts.
  This query groups containers by their high-level kind and computes how many types enforce sealed or abstract guarantees.
guided_experiments:
  - "Filter for only value types: `WHERE c.container_kind IN ('struct', 'enum')`."
  - "Look for classes that are neither abstract nor sealed to see open inheritance hierarchies."
---*/
SELECT 
    c.container_kind,
    COUNT(*) AS total_types,
    SUM(CASE WHEN f.is_sealed = 1 THEN 1 ELSE 0 END) AS sealed_types,
    SUM(CASE WHEN f.is_abstract = 1 THEN 1 ELSE 0 END) AS abstract_types,
    SUM(CASE WHEN f.is_static = 1 THEN 1 ELSE 0 END) AS static_types
FROM containers c
LEFT JOIN cs_container_facets f ON c.container_id = f.container_id
WHERE c.container_kind != 'ambient_scope'
GROUP BY c.container_kind
ORDER BY total_types DESC;
