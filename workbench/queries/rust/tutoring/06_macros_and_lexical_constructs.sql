/*---
id: rust_06_macros_and_lexical_constructs
title: "Metaprogramming & Lexical Boundaries: Macros, Reserved Words & Aliases"
target_language: rust
variant_compatibility:
  - "*"
suite: tutoring
level: Advanced
sequence: 6
category: "Metaprogramming & Lexical"
pedagogical_rationale: |
  Rust features macro metaprogramming and a strict lexical grammar:
  - Built-in Macros (`macro`): Compile-time AST-expanding constructs (e.g. `assert!`, `cfg!`, `println!`).
  - Strict Keywords: Core language constructs like `fn`, `match`, `impl`, `let`.
  - Reserved Keywords (`reserved_keyword`): Tokens reserved for future language editions (e.g. `abstract`, `pure`, `yield`, `override`).
  - Type Aliases (`type_alias`): Named shortcuts for complex types (`type Result<T> = std::result::Result<T, Error>`).
  This query catalogs macros, reserved keywords, and type aliases across the index.
guided_experiments:
  - "Filter for strictly macro symbols: `WHERE s.symbol_kind = 'macro'`."
  - "Filter for reserved keywords to see features reserved for future Rust editions: `WHERE s.symbol_kind = 'reserved_keyword'`."
---*/
SELECT 
    s.name AS symbol_name,
    s.symbol_kind,
    s.visibility,
    c.short_name AS declaring_container
FROM symbols s
JOIN containers c ON s.container_id = c.container_id
WHERE s.symbol_kind IN ('macro', 'reserved_keyword', 'type_alias')
ORDER BY s.symbol_kind ASC, s.name ASC
LIMIT 30;
