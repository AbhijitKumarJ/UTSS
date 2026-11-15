/*---
id: ts_03_interfaces_classes_and_containers
title: "Container Taxonomy: Interfaces, Classes, Enums & Modules"
target_language: typescript
variant_compatibility:
  - "*"
suite: tutoring
level: Intermediate
sequence: 3
category: "Container Hierarchy"
pedagogical_rationale: |
  TypeScript differentiates between purely compile-time constructs and runtime objects:
  - `interface`: Erased completely during transpilation; carries zero runtime cost.
  - `class`: Emits JavaScript constructor functions/prototypes and exists at runtime.
  - `enum`: Emits bidirectional object maps at runtime.
  - `module`: Source files acting as ES modules.
  This query groups containers by kind and computes how many are exported or ambient (`declare`).
guided_experiments:
  - "Filter for purely compile-time interfaces: `WHERE c.container_kind = 'interface'`."
  - "Filter for ambient declarations (`declare module`, `declare class`): `WHERE tf.is_ambient = 1`."
---*/
SELECT 
    c.container_kind,
    COUNT(*) AS total_containers,
    SUM(CASE WHEN tf.is_export = 1 THEN 1 ELSE 0 END) AS exported_containers,
    SUM(CASE WHEN tf.is_ambient = 1 THEN 1 ELSE 0 END) AS ambient_containers
FROM containers c
JOIN ts_container_facets tf ON c.container_id = tf.container_id
WHERE c.container_kind != 'ambient_scope'
GROUP BY c.container_kind
ORDER BY total_containers DESC;
