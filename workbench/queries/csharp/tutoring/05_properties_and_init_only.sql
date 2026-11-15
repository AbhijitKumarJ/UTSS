/*---
id: cs_05_properties_and_init_only
title: "Property Evolution: Getters, Setters, and Init-Only Immutability"
target_language: csharp
variant_compatibility:
  - "*"
suite: tutoring
level: Advanced
sequence: 5
category: "Encapsulation & Mutability"
pedagogical_rationale: |
  Properties in C# are syntactic sugar over accessor methods (`get_Name`, `set_Name`).
  Starting in C# 9, the language introduced `init` accessors, allowing properties to be mutated during object initialization
  expressions (`new Person { Name = "Alice" }`) while enforcing strict read-only immutability once construction completes.
  This query catalogs properties across classes and structs, identifying read-only vs read-write vs init-only models.
guided_experiments:
  - "Filter for strictly init-only properties: `WHERE f.is_init_only = 1`."
  - "Find purely get-only properties (calculated or immutable) with `WHERE f.has_getter = 1 AND f.has_setter = 0`."
---*/
SELECT 
    s.name AS property_name,
    c.short_name AS declaring_type,
    c.container_kind,
    f.has_getter,
    f.has_setter,
    f.is_init_only,
    s.visibility
FROM symbols s
JOIN cs_symbol_facets f ON s.symbol_id = f.symbol_id
JOIN containers c ON s.container_id = c.container_id
WHERE s.symbol_kind = 'property'
ORDER BY f.is_init_only DESC, f.has_setter ASC, c.short_name ASC, s.name ASC
LIMIT 30;
