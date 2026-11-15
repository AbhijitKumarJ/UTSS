/*---
id: cs_03_readonly_and_ref_structs
title: "High-Performance Memory: Readonly Structs & Stack-Only Ref Structs"
target_language: csharp
variant_compatibility:
  - "*"
suite: tutoring
level: Intermediate
sequence: 3
category: "Memory & Performance"
pedagogical_rationale: |
  To achieve zero-allocation performance without garbage collection pauses, modern C# introduced:
  - `readonly struct`: Guarantees immutability so the C# compiler avoids making defensive copies when passed via `in`.
  - `ref struct`: Stack-only value types (e.g. `Span<T>`, `ReadOnlySpan<T>`) that cannot be boxed, cannot escape to the heap, and cannot be captured in async state machines.
  This query identifies all struct types in the codebase, highlighting their readonly and ref modifiers alongside their member density.
guided_experiments:
  - "Filter for strictly stack-only structs: `WHERE f.is_ref_struct = 1`."
  - "Inspect the members of Span or ReadOnlySpan if present in your database."
---*/
SELECT 
    c.short_name AS struct_name,
    c.qualified_name,
    f.is_readonly_struct,
    f.is_ref_struct,
    f.is_sealed,
    COUNT(s.symbol_id) AS total_members
FROM containers c
JOIN cs_container_facets f ON c.container_id = f.container_id
LEFT JOIN symbols s ON c.container_id = s.container_id
WHERE c.container_kind = 'struct'
GROUP BY c.container_id
ORDER BY f.is_ref_struct DESC, f.is_readonly_struct DESC, c.short_name ASC
LIMIT 30;
