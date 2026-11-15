/*---
id: ts_06_modules_and_export_patterns
title: "Module Architecture: Named Exports, Default Exports & Ambient Declarations"
target_language: typescript
variant_compatibility:
  - "*"
suite: tutoring
level: Advanced
sequence: 6
category: "Modules & Bundling"
pedagogical_rationale: |
  Modern TypeScript utilizes standard ECMAScript Modules (ESM):
  - `export`: Named exports that consumers import via `{ Name }`.
  - `export default`: Single default export per module (`import Name from ...`).
  - Ambient Declarations (`declare module`, `declare class`): Type declarations without runtime implementation (e.g. .d.ts files).
  This query catalogs module containers and evaluates their export styles and symbol capacities.
guided_experiments:
  - "Filter for default export modules: `WHERE tf.is_default_export = 1`."
  - "Filter for ambient .d.ts containers: `WHERE tf.is_ambient = 1`."
---*/
SELECT 
    c.short_name AS module_name,
    c.container_kind,
    tf.is_export,
    tf.is_default_export,
    tf.is_ambient,
    COUNT(s.symbol_id) AS declared_symbols
FROM containers c
JOIN ts_container_facets tf ON c.container_id = tf.container_id
LEFT JOIN symbols s ON c.container_id = s.container_id
GROUP BY c.container_id
ORDER BY tf.is_ambient DESC, tf.is_default_export DESC, declared_symbols DESC
LIMIT 30;
