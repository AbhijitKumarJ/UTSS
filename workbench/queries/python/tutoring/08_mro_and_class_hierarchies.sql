/*---
id: py_08_mro_and_class_hierarchies
title: "Type Mechanics: Method Resolution Order (MRO) & Metaclasses"
target_language: "python"
variant_compatibility: ["*"]
suite: "tutoring"
level: "Advanced"
sequence: 8
category: "Metaclasses & Inheritance"
pedagogical_rationale: >
  Python classes are instances of metaclasses (default: 'type'). When a class inherits from
  multiple bases, CPython computes its Method Resolution Order (MRO) using the C3 Linearization
  algorithm. This guarantees monotonicity and preserves local precedence ordering during super() lookups.
  
  This query inspects class facet metadata—including direct base classes (base_classes_json),
  linearized inheritance chains (mro_json), and custom metaclasses.
guided_experiments:
  - "Filter where metaclass_name IS NOT NULL to uncover custom metaclasses in the environment."
  - "Look for classes where mro_json contains more than 3 ancestors to observe multi-inheritance hierarchies."
  - "Examine base_classes_json vs mro_json: base_classes are direct parents, while MRO represents the full lookup resolution order."
---*/
SELECT
    c.qualified_name AS class_name,
    d.dist_name AS distribution,
    f.metaclass_name,
    f.base_classes_json AS direct_bases,
    f.mro_json AS method_resolution_order,
    f.has_lazy_getattr,
    f.has_dunder_all
FROM py_container_facets f
JOIN containers c ON c.container_id = f.container_id
JOIN distributions d ON d.dist_id = c.dist_id
WHERE c.container_kind IN ('class', 'exception_class')
  AND (f.base_classes_json IS NOT NULL OR f.metaclass_name IS NOT NULL)
ORDER BY f.metaclass_name DESC, c.qualified_name ASC
LIMIT 100;
