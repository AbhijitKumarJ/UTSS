/*---
id: cpp_03_template_metaprogramming
title: "Template Metaprogramming: Type Parameters & Generic Blueprints"
target_language: cpp
variant_compatibility:
  - "*"
suite: tutoring
level: Intermediate
sequence: 3
category: "Generics & Templates"
pedagogical_rationale: |
  Templates are the cornerstone of high-performance modern C++, enabling compile-time monomorphization and zero-cost abstractions.
  When a container or function is a template, the compiler generates specialized machine code for each concrete type combination.
  This query identifies template containers in the C++ translation unit along with their formal type parameter signatures.
guided_experiments:
  - "Find templates from `std` by adding `WHERE c.qualified_name LIKE 'std::%'`."
  - "Check how many members are declared inside each template blueprint."
---*/
SELECT 
    c.short_name AS template_name,
    c.qualified_name,
    f.template_params_json AS type_parameters,
    f.is_final,
    COUNT(s.symbol_id) AS declared_members
FROM containers c
JOIN cpp_container_facets f ON c.container_id = f.container_id
LEFT JOIN symbols s ON c.container_id = s.container_id
WHERE f.is_template = 1 OR f.template_params_json IS NOT NULL
GROUP BY c.container_id
ORDER BY c.short_name ASC
LIMIT 30;
