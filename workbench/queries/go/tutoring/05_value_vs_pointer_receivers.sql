/*---
id: go_05_value_vs_pointer_receivers
title: "Method Receivers: Value Semantics vs Pointer Mutability (*T)"
target_language: go
variant_compatibility:
  - "*"
suite: tutoring
level: Advanced
sequence: 5
category: "Methods & Memory"
pedagogical_rationale: |
  In Go, methods are simply functions with an explicit receiver parameter:
  - Value Receiver (`(t T)`): Operates on a full copy of the struct; mutations do not alter the caller's instance.
  - Pointer Receiver (`(t *T)`): Operates directly on the caller's memory address; allows mutating struct state and prevents copying large structures.
  This query inspects method definitions, contrasting value receivers vs pointer receivers (*T) across packages.
guided_experiments:
  - "Filter for only pointer receiver methods: `WHERE sf.receiver_kind LIKE '%pointer%' OR sf.receiver_type LIKE '*%'`."
  - "Check whether exported types prefer pointer or value receivers."
---*/
SELECT 
    s.name AS method_name,
    sf.receiver_type,
    sf.receiver_kind,
    sf.is_exported,
    cal.return_type_expr,
    cal.raw_signature
FROM symbols s
JOIN go_symbol_facets sf ON s.symbol_id = sf.symbol_id
JOIN callables cal ON s.symbol_id = cal.symbol_id
WHERE sf.receiver_type IS NOT NULL
ORDER BY sf.receiver_kind ASC, s.name ASC
LIMIT 30;
