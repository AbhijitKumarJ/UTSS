/*---
id: py_01_strata_and_environments
title: "The Runtime Foundations: Environments & Strata"
target_language: "python"
variant_compatibility: ["*"]
suite: "tutoring"
level: "Basic"
sequence: 1
category: "Runtime & Scope"
pedagogical_rationale: >
  Python code never runs in a vacuum. Before executing a single user statement,
  CPython initializes distinct runtime strata:
  - Stratum 0 (Ambient Scope): Built-in functions (len, print), language keywords, and implicit dunders.
  - Stratum 1 (Standard Library): Pure Python and compiled C modules shipped directly with the CPython binary.
  - Stratum 2 (Third-Party / Site-Packages): Installed external distributions (e.g. packaging, pytest, Pygments).
  - Stratum 3 (Workspace Code): The user's active codebase.
  
  This query inspects the active runtime environment and displays how distributions
  are separated into architectural strata.
guided_experiments:
  - "Modify the WHERE clause to 'WHERE d.stratum = 1' to view only CPython Standard Library packages."
  - "Join with the 'containers' table: 'JOIN containers c ON c.dist_id = d.dist_id' and count containers per stratum."
lab_challenge:
  objective: "Write a SQL query that retrieves all distributions residing specifically in Stratum 1 (Standard Library), displaying the distribution name, version, and its summary description, ordered alphabetically by distribution name."
  starter_sql: |
    -- Lab Challenge: Filter for Stratum 1 Standard Library distributions
    SELECT
        d.dist_name,
        d.dist_version,
        d.summary
    FROM distributions d
    WHERE d.stratum = 1
    ORDER BY d.dist_name ASC;
  solution_sql: |
    SELECT
        d.dist_name,
        d.dist_version,
        d.summary
    FROM distributions d
    WHERE d.stratum = 1
    ORDER BY d.dist_name ASC;
  expected_columns:
    - dist_name
    - dist_version
    - summary
  min_rows: 1
  xp_reward: 50
  hint: "Filter with 'WHERE d.stratum = 1' and sort with 'ORDER BY d.dist_name ASC'."
---*/
SELECT
    d.stratum,
    CASE d.stratum
        WHEN 0 THEN 'Stratum 0: Ambient Scope'
        WHEN 1 THEN 'Stratum 1: Standard Library'
        WHEN 2 THEN 'Stratum 2: Third-Party Packages'
        WHEN 3 THEN 'Stratum 3: Workspace Code'
        ELSE 'Unknown Stratum'
    END AS stratum_name,
    d.dist_name,
    d.dist_version,
    e.language || ' ' || e.language_version AS runtime_engine,
    e.platform_triplet,
    d.summary
FROM distributions d
JOIN environments e ON e.env_id = d.env_id
ORDER BY d.stratum ASC, d.dist_name ASC;
