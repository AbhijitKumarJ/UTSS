/*---
id: ts_05_class_heritage_and_generics
title: "Object-Oriented Structure: Heritage Clauses (extends, implements) & Generics"
target_language: typescript
variant_compatibility:
  - "*"
suite: tutoring
level: Advanced
sequence: 5
category: "Heritage & Generics"
pedagogical_rationale: |
  TypeScript classes and interfaces express contracts through heritage clauses:
  - `extends`: Class inheritance (single inheritance) or interface extension (multiple extension).
  - `implements`: Enforces that a class satisfies an interface structure.
  - `is_abstract`: Abstract classes that require derived implementations.
  - Type Parameters (`<T>`): Formal generic parameters.
  This query identifies classes and interfaces, their heritage clauses, generic parameters, and member counts.
guided_experiments:
  - "Filter for abstract classes: `WHERE tf.is_abstract = 1`."
  - "Filter for types with inheritance clauses: `WHERE tf.heritage_clauses_json != '[]'`."
---*/
SELECT 
    c.short_name AS class_name,
    c.container_kind,
    tf.is_abstract,
    tf.heritage_clauses_json AS heritage_clauses,
    tf.type_params_json AS type_parameters,
    COUNT(s.symbol_id) AS total_members
FROM containers c
JOIN ts_container_facets tf ON c.container_id = tf.container_id
LEFT JOIN symbols s ON c.container_id = s.container_id
WHERE c.container_kind IN ('class', 'interface')
GROUP BY c.container_id
ORDER BY tf.is_abstract DESC, total_members DESC, c.short_name ASC
LIMIT 30;
