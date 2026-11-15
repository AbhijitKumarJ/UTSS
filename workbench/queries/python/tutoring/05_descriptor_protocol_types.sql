/*---
id: py_05_descriptor_protocol_types
title: "The Secret Life of Descriptors: Methods, Slots, and Attributes"
target_language: "python"
variant_compatibility: ["*"]
suite: "tutoring"
level: "Advanced"
sequence: 5
category: "Object Model & Descriptors"
pedagogical_rationale: >
  In Python, almost all attribute access relies on the Descriptor Protocol (__get__, __set__).
  When you access an attribute on an instance (obj.attr), Python invokes attr.__get__(obj, type(obj)).
  CPython defines several distinct descriptor kinds:
  - 'method_descriptor': C-implemented methods on built-in types (e.g. str.split, dict.keys).
  - 'wrapper_descriptor': Slot wrappers binding C-level type slots (e.g. object.__repr__, int.__add__).
  - 'getset_descriptor': C-level struct getters/setters exposed to Python (e.g. function.__name__, code.co_argcount).
  - 'member_descriptor': Direct offset pointers to C struct members (used in __slots__).
  - 'property', 'classmethod', 'staticmethod': High-level Python descriptor wrappers.
  
  This query catalogs all descriptor mechanisms used across Python's core type hierarchy.
guided_experiments:
  - "Filter for 'getset_descriptor': see how CPython manages internal object attributes."
  - "Filter by container_path = 'builtins.dict' or 'builtins.str' to observe how primitive type methods are represented."
  - "Notice that pure Python functions in class definitions become bound methods at runtime via the descriptor protocol."
---*/
SELECT
    f.descriptor_kind,
    s.name AS attribute_name,
    c.qualified_name AS container_type,
    s.symbol_kind,
    f.py_runtime_type,
    s.visibility
FROM py_symbol_facets f
JOIN symbols s ON s.symbol_id = f.symbol_id
JOIN containers c ON c.container_id = s.container_id
WHERE f.descriptor_kind IS NOT NULL
ORDER BY f.descriptor_kind ASC, c.qualified_name ASC, s.name ASC
LIMIT 100;
