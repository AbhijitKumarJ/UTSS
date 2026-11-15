/*---
id: go_06_functions_and_variadic_signatures
title: "Calling Semantics: Package Functions, Multiple Returns & Variadics"
target_language: go
variant_compatibility:
  - "*"
suite: tutoring
level: Advanced
sequence: 6
category: "Callables & Signatures"
pedagogical_rationale: |
  Go package-level functions are first-class citizens:
  - Multiple Return Values: Idiomatically used throughout Go for returning results alongside `error`.
  - Variadic Parameters (`...T`): Accept an arbitrary number of trailing arguments, collected internally as a slice.
  This query inspects standalone package functions, their export status, variadic parameters, and return types.
guided_experiments:
  - "Filter for strictly variadic functions (`fmt.Printf`, `fmt.Println`): `WHERE sf.is_variadic = 1`."
  - "Check functions returning multiple values or error tuples by filtering `cal.return_type_expr LIKE '%error%'`."
---*/
SELECT 
    s.name AS function_name,
    c.short_name AS package_name,
    sf.is_exported,
    sf.is_variadic,
    cal.return_type_expr,
    cal.raw_signature
FROM symbols s
JOIN go_symbol_facets sf ON s.symbol_id = sf.symbol_id
JOIN callables cal ON s.symbol_id = cal.symbol_id
JOIN containers c ON s.container_id = c.container_id
WHERE s.symbol_kind = 'function'
ORDER BY sf.is_variadic DESC, sf.is_exported DESC, s.name ASC
LIMIT 30;
