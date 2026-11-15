/*---
id: rust_01_prelude_and_crate_strata
title: "The Rust 1.85 Environment: Preludes, Crates & Strata"
target_language: rust
variant_compatibility:
  - "*"
suite: tutoring
level: Basic
sequence: 1
category: "Strata & Preludes"
pedagogical_rationale: |
  The Rust compilation model partitions code into crate and runtime layers:
  - Stratum 0 (Ambient Scope): Primitive types (i32, f64, bool, str), standard prelude items, and built-in compiler macros (println!, vec!).
  - Stratum 1 (Standard Library / std): Rust standard library crates (core, alloc, std).
  - Stratum 3 (Workspace Code): Workspace packages compiled via syn and rustc.
  This query inspects the distribution layers of the Rust index and measures container densities across strata.
guided_experiments:
  - "Filter for standard prelude types only: `WHERE d.stratum = 0`."
  - "Check the rustc compiler version: `CROSS JOIN environments e`."
lab_challenge:
  objective: "Write a SQL query to list all crate distributions that belong to Stratum 0 (Ambient Scope) or Stratum 1 (Standard Library), displaying the crate_name, stratum, and total containers."
  starter_sql: |
    -- Lab Challenge: Find crates in Stratum 0 and 1
    SELECT
        d.dist_name AS crate_name,
        d.stratum,
        COUNT(c.container_id) AS total_containers
    FROM distributions d
    LEFT JOIN containers c ON d.dist_id = c.dist_id
    WHERE d.stratum IN (0, 1)
    GROUP BY d.dist_id
    ORDER BY d.stratum ASC;
  solution_sql: |
    SELECT
        d.dist_name AS crate_name,
        d.stratum,
        COUNT(c.container_id) AS total_containers
    FROM distributions d
    LEFT JOIN containers c ON d.dist_id = c.dist_id
    WHERE d.stratum IN (0, 1)
    GROUP BY d.dist_id
    ORDER BY d.stratum ASC;
  expected_columns:
    - crate_name
    - stratum
    - total_containers
  min_rows: 1
  xp_reward: 75
  hint: "Filter with WHERE d.stratum IN (0, 1) and group by d.dist_id."
---*/
SELECT 
    d.stratum,
    d.dist_name AS crate_name,
    d.dist_version AS version,
    d.summary,
    COUNT(c.container_id) AS total_containers
FROM distributions d
LEFT JOIN containers c ON d.dist_id = c.dist_id
GROUP BY d.dist_id
ORDER BY d.stratum ASC;
