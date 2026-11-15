/*---
id: py_06_dunder_lifecycle_and_methods
title: "The Python Data Model: Dunder Protocols & Special Methods"
target_language: "python"
variant_compatibility: ["*"]
suite: "tutoring"
level: "Intermediate"
sequence: 6
category: "Data Model & Protocols"
pedagogical_rationale: >
  Python's object orientation is fundamentally protocol-driven through 'dunder' (double-underscore) methods:
  - 'lifecycle': Object instantiation, allocation, and finalization (__init__, __new__, __del__).
  - 'comparison': Rich comparisons (__eq__, __ne__, __lt__, __gt__, __hash__).
  - 'numeric': Operator overloading (__add__, __mul__, __pow__, in-place __iadd__).
  - 'container': Sequence and mapping emulation (__len__, __getitem__, __setitem__, __contains__).
  - 'context_manager': Resource management protocols (__enter__, __exit__).
  - 'async': Coroutine and asynchronous iteration (__aenter__, __aexit__, __aiter__, __anext__).
  - 'attribute_access': Dynamic dispatch and attribute interception (__getattr__, __getattribute__, __setattr__).
  
  This query maps special methods by protocol category across core Python types.
guided_experiments:
  - "Filter by dunder_category = 'context_manager' to find every class that implements the 'with' protocol."
  - "Filter by dunder_category = 'async' to see asynchronous primitives."
  - "Group by dunder_category and count(*) to see which protocol is most heavily implemented across the standard library."
---*/
SELECT
    f.dunder_category,
    s.name AS special_method,
    c.qualified_name AS implementing_class,
    f.py_runtime_type,
    f.descriptor_kind,
    s.docstring
FROM py_symbol_facets f
JOIN symbols s ON s.symbol_id = f.symbol_id
JOIN containers c ON c.container_id = s.container_id
WHERE f.dunder_category IS NOT NULL
ORDER BY f.dunder_category ASC, c.qualified_name ASC, s.name ASC
LIMIT 100;
