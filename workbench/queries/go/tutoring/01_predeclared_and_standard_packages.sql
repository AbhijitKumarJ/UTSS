/*---
id: go_01_predeclared_and_standard_packages
title: "The Go Architecture: Predeclared Scope & Standard Packages"
target_language: go
variant_compatibility:
  - "*"
suite: tutoring
level: Basic
sequence: 1
category: "Strata & Standard Library"
pedagogical_rationale: |
  The Go compiler and runtime organize code cleanly into strata:
  - Stratum 0 (Ambient Scope): Go specification predeclared keywords, fundamental primitive types (int, string, bool), and built-in functions (len, make, append).
  - Stratum 1 (Standard Library / std): Curated tier-1 packages (fmt, io, os, strings, strconv, time, sync, context).
  - Stratum 3 (Workspace Code): User application and domain packages (e.g. commerce_engine).
  This query inspects the distributions that constitute the Go environment and tallies the container count per stratum.
guided_experiments:
  - "Filter for standard library packages only: `WHERE d.stratum = 1`."
  - "Count symbols in each stratum by joining with `containers c` and `symbols s`."
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
