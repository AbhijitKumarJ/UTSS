/*---
id: ts_02_builtin_utility_types
title: "TypeScript's Built-in Utility Types: Type-Level Transformations"
target_language: typescript
variant_compatibility:
  - "*"
suite: tutoring
level: Basic
sequence: 2
category: "Utility Types"
pedagogical_rationale: |
  TypeScript provides global utility types that perform type-level transformations:
  - `Partial<T>`: Makes all properties in T optional.
  - `Required<T>`: Makes all properties in T mandatory.
  - `Readonly<T>`: Marks all properties in T as readonly.
  - `Record<K, T>`: Constructs an object type whose keys are K and values are T.
  - `Pick<T, K>` & `Omit<T, K>`: Constructs a type by picking or omitting specified keys.
  This query catalogs the built-in utility types provided by TypeScript's ambient standard library.
guided_experiments:
  - "Filter for utility types dealing with immutability or optionality: `WHERE s.name IN ('Partial', 'Required', 'Readonly')`."
  - "Filter for function transformation types: `WHERE s.name IN ('ReturnType', 'Parameters', 'Awaited')`."
---*/
SELECT 
    s.name AS utility_type,
    s.symbol_kind,
    s.docstring AS documentation
FROM symbols s
WHERE s.symbol_kind = 'utility_type'
ORDER BY s.name ASC
LIMIT 30;
