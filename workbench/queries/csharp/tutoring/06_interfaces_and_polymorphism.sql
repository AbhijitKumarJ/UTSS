/*---
id: cs_06_interfaces_and_polymorphism
title: "Polymorphic Architecture: Interface Contracts & Virtual Dispatch"
target_language: csharp
variant_compatibility:
  - "*"
suite: tutoring
level: Advanced
sequence: 6
category: "Polymorphism & Contracts"
pedagogical_rationale: |
  .NET runtime polymorphism relies on Virtual Method Tables (v-tables) and Interface Method Tables (i-tables).
  When a class implements interfaces (such as `IDisposable`, `IEnumerable`, or custom abstractions) or derives from a base class,
  the runtime manages method slots that can be marked `virtual`, `override`, `abstract`, or `sealed`.
  This query inspects polymorphic types, listing their base types, interface contracts, and count of virtual vs overridden methods.
guided_experiments:
  - "Find types implementing `IDisposable` or `IAsyncDisposable` with `WHERE f.implemented_interfaces_json LIKE '%Disposable%'`."
  - "Filter for purely abstract base classes: `WHERE f.is_abstract = 1`."
---*/
SELECT 
    c.short_name AS type_name,
    c.container_kind,
    f.base_type_qname AS base_class,
    f.implemented_interfaces_json AS interfaces,
    COUNT(s.symbol_id) AS total_symbols,
    SUM(CASE WHEN sf.is_virtual = 1 THEN 1 ELSE 0 END) AS virtual_methods,
    SUM(CASE WHEN sf.is_override = 1 THEN 1 ELSE 0 END) AS override_methods
FROM containers c
JOIN cs_container_facets f ON c.container_id = f.container_id
LEFT JOIN symbols s ON c.container_id = s.container_id
LEFT JOIN cs_symbol_facets sf ON s.symbol_id = sf.symbol_id
WHERE f.implemented_interfaces_json != '[]' OR f.base_type_qname IS NOT NULL
GROUP BY c.container_id
HAVING virtual_methods > 0 OR override_methods > 0
ORDER BY (virtual_methods + override_methods) DESC, c.short_name ASC
LIMIT 30;
