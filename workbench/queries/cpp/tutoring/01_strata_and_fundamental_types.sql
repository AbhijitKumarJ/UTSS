/*---
id: cpp_01_strata_and_fundamental_types
title: "The C++20 Environment: Fundamental Types & Header Strata"
target_language: cpp
variant_compatibility:
  - "*"
suite: tutoring
level: Basic
sequence: 1
category: "Strata & Standard Library"
pedagogical_rationale: |
  ISO C++20 organizes language symbols into clean strata:
  - Stratum 0 (Ambient Scope): Fundamental built-in types (int, double, char8_t), ISO keywords, and macros.
  - Stratum 1 (Standard Library / libstdc++): Standard library headers (<iostream>, <vector>, <string>, <memory>).
  - Stratum 3 (Workspace Code): User classes, business domains, and application logic.
  This query inspects the distribution layers of the compiled C++ translation units and counts their containers.
guided_experiments:
  - "Filter for only the Standard Library stratum: `WHERE d.stratum = 1`."
  - "Join with `environments` to see the compiler and platform details (`CROSS JOIN environments e`)."
---*/
SELECT 
    d.stratum,
    d.dist_name AS distribution,
    d.dist_version AS version,
    d.summary,
    COUNT(c.container_id) AS total_containers
FROM distributions d
LEFT JOIN containers c ON d.dist_id = c.dist_id
GROUP BY d.dist_id
ORDER BY d.stratum ASC;
