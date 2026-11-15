/*---
id: cs_04_extension_methods_and_async
title: "Method Mechanics: Extension Methods, Async State Machines & Unsafe"
target_language: csharp
variant_compatibility:
  - "*"
suite: tutoring
level: Intermediate
sequence: 4
category: "Method Mechanics"
pedagogical_rationale: |
  C# methods possess unique compiler capabilities:
  - Extension Methods: Static methods in static classes marked with `this` on the first parameter, allowing fluent syntax without modifying the target type.
  - Async Methods: Transformed by Roslyn into state machine structs implementing `IAsyncStateMachine`.
  - Unsafe Methods: Pointers and direct memory manipulation requiring `/unsafe` compilation.
  This query inspects methods equipped with these specialized compiler features.
guided_experiments:
  - "Filter for strictly extension methods: `WHERE f.is_extension_method = 1`."
  - "Check methods returning Task or ValueTask by adding `WHERE cal.return_type_expr LIKE '%Task%'`."
---*/
SELECT 
    s.name AS method_name,
    s.qualified_name,
    f.is_extension_method,
    f.is_async,
    f.is_unsafe,
    cal.return_type_expr,
    cal.raw_signature
FROM symbols s
JOIN cs_symbol_facets f ON s.symbol_id = f.symbol_id
JOIN callables cal ON s.symbol_id = cal.symbol_id
WHERE f.is_extension_method = 1 OR f.is_async = 1 OR f.is_unsafe = 1
ORDER BY f.is_extension_method DESC, f.is_async DESC, s.name ASC
LIMIT 30;
