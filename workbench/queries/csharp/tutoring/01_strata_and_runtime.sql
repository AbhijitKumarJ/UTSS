/*---
id: cs_01_strata_and_runtime
title: "The .NET 10 Runtime: Strata, Assemblies & Environments"
target_language: csharp
variant_compatibility:
  - "*"
suite: tutoring
level: Basic
sequence: 1
category: "Runtime & Assemblies"
pedagogical_rationale: |
  In modern .NET (CoreCLR / .NET 10), code execution is structured around assemblies and runtime strata.
  - Stratum 0 (Ambient Scope): Fundamental C# keywords, primitive type aliases (int, string, bool), and implicit global usings.
  - Stratum 1 (Base Class Library / BCL): System.Runtime, System.Collections, and CoreCLR core assemblies.
  - Stratum 3 (Workspace Code): User application and business domain code (e.g. CommerceEngine).
  This query inspects how the UTSS indexer partitions .NET assemblies into architectural strata and counts the types in each layer.
guided_experiments:
  - "Filter for only Base Class Library types by modifying the WHERE clause to `WHERE d.stratum = 1`."
  - "Check the runtime environment version by joining with the `environments` table: `CROSS JOIN environments e`."
lab_challenge:
  objective: "Inspect the .NET distributions in Stratum 1 (BCL) and return the assembly_name, version, and the count of containers in each assembly, sorted by container count descending."
  starter_sql: |
    -- Lab Challenge: Filter for Stratum 1 BCL assemblies and aggregate their containers
    SELECT
        d.dist_name AS assembly_name,
        d.dist_version AS version,
        COUNT(c.container_id) AS total_containers
    FROM distributions d
    LEFT JOIN containers c ON d.dist_id = c.dist_id
    WHERE d.stratum = 1
    GROUP BY d.dist_id
    ORDER BY total_containers DESC;
  solution_sql: |
    SELECT
        d.dist_name AS assembly_name,
        d.dist_version AS version,
        COUNT(c.container_id) AS total_containers
    FROM distributions d
    LEFT JOIN containers c ON d.dist_id = c.dist_id
    WHERE d.stratum = 1
    GROUP BY d.dist_id
    ORDER BY total_containers DESC;
  expected_columns:
    - assembly_name
    - version
    - total_containers
  min_rows: 1
  xp_reward: 75
  hint: "Filter with WHERE d.stratum = 1 and group by d.dist_id."
---*/
SELECT 
    d.stratum,
    d.dist_name AS assembly_name,
    d.dist_version AS version,
    d.summary,
    COUNT(c.container_id) AS total_containers
FROM distributions d
LEFT JOIN containers c ON d.dist_id = c.dist_id
GROUP BY d.dist_id
ORDER BY d.stratum ASC;
