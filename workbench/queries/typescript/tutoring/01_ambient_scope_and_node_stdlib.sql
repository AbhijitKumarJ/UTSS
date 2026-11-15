/*---
id: ts_01_ambient_scope_and_node_stdlib
title: "The TypeScript & Node.js Environment: Ambient Scope & Modules"
target_language: typescript
variant_compatibility:
  - "*"
suite: tutoring
level: Basic
sequence: 1
category: "Strata & Standard Modules"
pedagogical_rationale: |
  TypeScript projects run on JavaScript engines (Node.js 24) and structure symbols across strata:
  - Stratum 0 (Ambient Scope): Standard ECMAScript globals (Object, Array, Promise), primitive types (string, number, boolean), and TypeScript keywords.
  - Stratum 1 (Node.js Standard Modules): Tier-1 built-in modules (fs, path, http, events).
  - Stratum 3 (Workspace Code): User TypeScript source files and domain models (e.g. commerce_engine).
  This query inspects the distribution layers of the TypeScript compilation project and measures their container density.
guided_experiments:
  - "Filter for Node.js standard modules: `WHERE d.stratum = 1`."
  - "Check the TypeScript compiler and Node runtime version with `CROSS JOIN environments e`."
lab_challenge:
  objective: "Write a SQL query to inspect TypeScript/Node.js distributions in Stratum 1, selecting distribution name and total containers count."
  starter_sql: |
    -- Lab Challenge: Filter for Stratum 1 Node standard libraries
    SELECT
        d.dist_name AS distribution,
        COUNT(c.container_id) AS total_containers
    FROM distributions d
    LEFT JOIN containers c ON d.dist_id = c.dist_id
    WHERE d.stratum = 1
    GROUP BY d.dist_id
    ORDER BY total_containers DESC;
  solution_sql: |
    SELECT
        d.dist_name AS distribution,
        COUNT(c.container_id) AS total_containers
    FROM distributions d
    LEFT JOIN containers c ON d.dist_id = c.dist_id
    WHERE d.stratum = 1
    GROUP BY d.dist_id
    ORDER BY total_containers DESC;
  expected_columns:
    - distribution
    - total_containers
  min_rows: 1
  xp_reward: 75
  hint: "Filter with WHERE d.stratum = 1 and group by d.dist_id."
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
