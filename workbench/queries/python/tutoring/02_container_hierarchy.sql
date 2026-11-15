/*---
id: py_02_container_hierarchy
title: "Container Taxonomy: Modules, Packages, and Classes"
target_language: "python"
variant_compatibility: ["*"]
suite: "tutoring"
level: "Basic"
sequence: 2
category: "Namespaces & Containers"
pedagogical_rationale: >
  In Python, every symbol exists within a hierarchical container.
  - 'ambient_scope': The global pre-imported built-in environment (requires_import = 0).
  - 'package': A directory namespace containing a __path__ attribute and submodules.
  - 'module': A single imported Python or compiled C translation unit.
  - 'class' and 'exception_class': Type objects that act as attribute namespaces for methods and descriptors.
  
  This query counts and lists the major container categories across distributions,
  showing how CPython organizes code from root packages down to internal classes.
guided_experiments:
  - "Filter by container_kind = 'class' AND requires_import = 1 to examine non-ambient classes."
  - "Filter by short_name = 'int' or 'dict' to see where core types are anchored in the container hierarchy."
  - "Order by container_id DESC to inspect recently indexed packages."
lab_challenge:
  objective: "Write an aggregate query that groups containers by their 'container_kind' and calculates the total count of containers per kind, ordered from highest count to lowest count."
  starter_sql: |
    -- Lab Challenge: Group containers by kind and count them
    SELECT
        container_kind,
        COUNT(*) AS container_count
    FROM containers
    GROUP BY container_kind
    ORDER BY container_count DESC;
  solution_sql: |
    SELECT
        container_kind,
        COUNT(*) AS container_count
    FROM containers
    GROUP BY container_kind
    ORDER BY container_count DESC;
  expected_columns:
    - container_kind
    - container_count
  min_rows: 3
  xp_reward: 100
  hint: "Use GROUP BY container_kind and COUNT(*) AS container_count, then sort with ORDER BY container_count DESC."
---*/
SELECT
    c.container_id,
    d.dist_name,
    c.container_kind,
    c.qualified_name,
    c.short_name,
    CASE c.requires_import
        WHEN 0 THEN 'Implicit (No Import Needed)'
        ELSE 'Explicit Import Required'
    END AS import_requirement,
    c.visibility,
    c.physical_path
FROM containers c
JOIN distributions d ON d.dist_id = c.dist_id
WHERE c.container_kind IN ('ambient_scope', 'package', 'module', 'class')
ORDER BY c.requires_import ASC, c.container_kind ASC, c.qualified_name ASC
LIMIT 100;
