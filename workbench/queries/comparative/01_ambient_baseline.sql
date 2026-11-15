/*---
id: cross_01_ambient_baseline
title: "The Ambient Baseline: Stratum 0 Globals Across Ecosystems"
target_language: "federated"
variant_compatibility: ["*"]
suite: "comparative"
level: "Basic"
sequence: 1
category: "Scope & Packaging"
pedagogical_rationale: >
  Evaluates the symbol budget granted automatically by each language runtime with zero explicit imports.
  In Python, built-in functions (len, range, print) and dunders are ambiently available in globals().
  In Rust, the core prelude injects Result, Option, and macros like println!.
  In Go, primitive types and universe functions (append, len, make) exist with no package qualification.
  In C# and C++, keywords, soft keywords, and primitive aliases form the initial lexical grammar.
  This comparative query inspects Stratum 0 across all 6 language catalogs.
guided_experiments:
  - "Filter by symbol_kind: Add 'AND s.symbol_kind IN ('function', 'primitive_type')' to compare available functions vs types."
  - "Compare Recommended vs Full databases to see if the ambient universe expands with language revisions."
---*/
SELECT 
    e.language,
    s.symbol_kind,
    COUNT(s.symbol_id) AS symbol_count,
    SUBSTR(GROUP_CONCAT(s.name, ', '), 1, 80) AS sample_symbols
FROM v_all_symbols s
JOIN v_all_containers c ON s.container_id = c.container_id AND s.language = c.language
JOIN v_all_distributions d ON c.dist_id = d.dist_id AND s.language = d.language
JOIN v_all_environments e ON s.language = e.language
WHERE d.stratum = 0
GROUP BY e.language, s.symbol_kind
ORDER BY e.language ASC, symbol_count DESC;
