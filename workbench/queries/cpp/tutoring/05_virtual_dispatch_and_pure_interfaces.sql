/*---
id: cpp_05_virtual_dispatch_and_pure_interfaces
title: "Object-Oriented Architecture: Virtual Dispatch & Pure Interfaces"
target_language: cpp
variant_compatibility:
  - "*"
suite: tutoring
level: Advanced
sequence: 5
category: "Polymorphism & V-Tables"
pedagogical_rationale: |
  In C++, runtime dynamic dispatch is realized through virtual method tables (vtables):
  - `virtual`: Enables dynamic dispatch at runtime via pointer/reference indirection.
  - `= 0` (`pure_virtual`): Turns a class into an abstract base interface that cannot be instantiated on its own.
  - `override`: Compile-time check ensuring the method signature matches a base class virtual method.
  This query inspects all virtual, pure virtual, and overriding methods across classes.
guided_experiments:
  - "Filter for strictly pure virtual methods defining abstract interfaces: `WHERE sf.is_pure_virtual = 1`."
  - "Filter for overriding implementation methods: `WHERE sf.is_override = 1`."
---*/
SELECT 
    s.name AS method_name,
    s.qualified_name,
    sf.access_specifier,
    sf.is_virtual,
    sf.is_pure_virtual,
    sf.is_override,
    c.short_name AS enclosing_class
FROM symbols s
JOIN cpp_symbol_facets sf ON s.symbol_id = sf.symbol_id
JOIN containers c ON s.container_id = c.container_id
WHERE sf.is_virtual = 1 OR sf.is_pure_virtual = 1 OR sf.is_override = 1
ORDER BY sf.is_pure_virtual DESC, sf.is_virtual DESC, s.name ASC
LIMIT 30;
