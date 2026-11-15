/*---
id: cpp_02_headers_namespaces_and_containers
title: "Container Topology: Headers, Namespaces, Classes, and Structs"
target_language: cpp
variant_compatibility:
  - "*"
suite: tutoring
level: Basic
sequence: 2
category: "Container Hierarchy"
pedagogical_rationale: |
  In C++, containers model translation units and scopes:
  - Headers (<vector>, <memory>) & Source Files (.cpp).
  - Namespaces (`std`, `commerce_engine`) providing lexical isolation.
  - Structs (public default member access) and Classes (private default member access).
  This query categorizes containers across the translation unit and checks how many are generic templates.
guided_experiments:
  - "Filter for only class and struct types: `WHERE c.container_kind IN ('class', 'struct')`."
  - "Group by `c.visibility` to inspect symbol export boundaries."
lab_challenge:
  objective: "Write a SQL query aggregating C++ container topologies, returning container_kind, total_containers, and template_containers count, ordered by total_containers descending."
  starter_sql: |
    -- Lab Challenge: Analyze C++ container topology and generic templates
    SELECT 
        c.container_kind,
        COUNT(*) AS total_containers,
        SUM(CASE WHEN f.is_template = 1 THEN 1 ELSE 0 END) AS template_containers
    FROM containers c
    LEFT JOIN cpp_container_facets f ON c.container_id = f.container_id
    WHERE c.container_kind != 'ambient_scope'
    GROUP BY c.container_kind
    ORDER BY total_containers DESC;
  solution_sql: |
    SELECT 
        c.container_kind,
        COUNT(*) AS total_containers,
        SUM(CASE WHEN f.is_template = 1 THEN 1 ELSE 0 END) AS template_containers
    FROM containers c
    LEFT JOIN cpp_container_facets f ON c.container_id = f.container_id
    WHERE c.container_kind != 'ambient_scope'
    GROUP BY c.container_kind
    ORDER BY total_containers DESC;
  expected_columns:
    - container_kind
    - total_containers
    - template_containers
  min_rows: 2
  xp_reward: 60
  hint: "Group by container_kind and use SUM(CASE WHEN f.is_template = 1 THEN 1 ELSE 0 END)."
---*/
SELECT 
    c.container_kind,
    COUNT(*) AS total_containers,
    SUM(CASE WHEN f.is_template = 1 THEN 1 ELSE 0 END) AS template_containers,
    SUM(CASE WHEN f.is_abstract = 1 THEN 1 ELSE 0 END) AS abstract_containers
FROM containers c
LEFT JOIN cpp_container_facets f ON c.container_id = f.container_id
WHERE c.container_kind != 'ambient_scope'
GROUP BY c.container_kind
ORDER BY total_containers DESC;
