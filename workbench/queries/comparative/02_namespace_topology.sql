/*---
id: cross_02_namespace_topology
title: "Namespace Topology and Container Hierarchy Across Stdlibs"
target_language: "federated"
variant_compatibility: ["*"]
suite: "comparative"
level: "Basic"
sequence: 2
category: "Scope & Packaging"
pedagogical_rationale: >
  Compares how standard libraries architect modularity and encapsulation.
  Go enforces a flat package architecture where subpackages are independent namespaces with minimal dot depth.
  C# and C++ construct deep namespace trees (e.g. System.Collections.Generic.Dictionary).
  Python packages use filesystem directory nesting with dot notation.
  This query computes container kind distributions and average qualification dot depths across all standard libraries.
guided_experiments:
  - "Inspect maximum qualification depth: Change 'AVG(...)' to 'MAX(...) AS max_dot_depth' to find the deepest nested modules."
  - "Filter for class containers: Add 'WHERE c.container_kind = 'class'' to compare class naming depths across languages."
---*/
SELECT 
    c.language,
    c.container_kind,
    COUNT(c.container_id) AS container_count,
    ROUND(AVG(LENGTH(c.qualified_name) - LENGTH(REPLACE(c.qualified_name, '.', '')) + 1), 2) AS avg_dot_depth
FROM v_all_containers c
JOIN v_all_distributions d ON c.dist_id = d.dist_id AND c.language = d.language
WHERE d.stratum = 1
GROUP BY c.language, c.container_kind
ORDER BY c.language ASC, container_count DESC;
