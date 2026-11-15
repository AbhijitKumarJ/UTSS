/*---
id: go_02_package_boundaries_and_exportability
title: "Package Boundaries & Exportability: The Capitalization Rule"
target_language: go
variant_compatibility:
  - "*"
suite: tutoring
level: Basic
sequence: 2
category: "Packages & Visibility"
pedagogical_rationale: |
  Unlike languages with `public` and `private` keywords, Go enforces visibility strictly through lexical casing:
  - Capitalized identifiers (`Printf`, `Reader`, `Open`) are exported and accessible across package boundaries.
  - Lowercase identifiers (`parse`, `readByte`) are unexported and internal to their declaring package.
  This query catalogs Go packages and aggregates the count of exported vs unexported symbols per package.
guided_experiments:
  - "Filter for packages with the highest proportion of exported API surface."
  - "Inspect internal unexported helper functions by setting `WHERE sf.is_exported = 0`."
---*/
SELECT 
    c.short_name AS package_name,
    COUNT(s.symbol_id) AS total_symbols,
    SUM(CASE WHEN sf.is_exported = 1 THEN 1 ELSE 0 END) AS exported_symbols,
    SUM(CASE WHEN sf.is_exported = 0 THEN 1 ELSE 0 END) AS unexported_symbols
FROM containers c
JOIN symbols s ON c.container_id = s.container_id
JOIN go_symbol_facets sf ON s.symbol_id = sf.symbol_id
WHERE c.container_kind = 'package'
GROUP BY c.container_id
ORDER BY total_symbols DESC;
