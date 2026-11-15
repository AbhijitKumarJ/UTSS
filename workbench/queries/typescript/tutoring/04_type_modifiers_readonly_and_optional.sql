/*---
id: ts_04_type_modifiers_readonly_and_optional
title: "Type Modifiers: Readonly, Optional Fields (?) and Access Modifiers"
target_language: typescript
variant_compatibility:
  - "*"
suite: tutoring
level: Intermediate
sequence: 4
category: "Modifiers & Encapsulation"
pedagogical_rationale: |
  TypeScript augments standard JavaScript properties with compile-time modifiers:
  - `readonly`: Prevents assignment to the property outside the constructor.
  - Optional (`?`): Permits the property to be omitted or assigned `undefined`.
  - Access Modifiers (`public`, `protected`, `private`): Checked at compile time (distinct from ECMAScript `#private` fields).
  This query catalogs properties and methods bearing these type-level modifiers.
guided_experiments:
  - "Filter for strictly readonly properties: `WHERE tf.is_readonly = 1`."
  - "Filter for optional properties (`prop?: Type`): `WHERE tf.is_optional = 1`."
---*/
SELECT 
    s.name AS member_name,
    s.symbol_kind,
    tf.access_modifier,
    tf.is_readonly,
    tf.is_optional,
    tf.is_abstract,
    c.short_name AS declaring_container
FROM symbols s
JOIN ts_symbol_facets tf ON s.symbol_id = tf.symbol_id
JOIN containers c ON s.container_id = c.container_id
WHERE tf.is_readonly = 1 OR tf.is_optional = 1 OR tf.access_modifier IS NOT NULL
ORDER BY tf.is_readonly DESC, tf.is_optional DESC, s.name ASC
LIMIT 30;
