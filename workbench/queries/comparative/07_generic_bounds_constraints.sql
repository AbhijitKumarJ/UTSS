/*---
id: cross_07_generic_bounds
title: "Generic Signatures and Parametric Polymorphism"
target_language: "federated"
variant_compatibility: ["*"]
suite: "comparative"
level: "Advanced"
sequence: 7
category: "Polymorphism & Contracts"
pedagogical_rationale: >
  Profiles parametric polymorphism, generic type parameter usage, and constraint markers across callables.
  Modern languages adopt different syntactic conventions and runtimes for generics:
  - C# reifies generics in the CLR runtime (List<T>, Dictionary<TKey, TValue> maintain exact types at runtime).
  - TypeScript and Python rely on compile-time type erasure (TypeScript interfaces and Python typing.List[T] vanish in JS/runtime).
  - Rust monomorphizes generics into specialized machine code with zero runtime dispatch cost.
  - Go uses compile-time type parameters ([T any]) introduced in Go 1.18.
  - C++ relies on template specialization and concepts.
  This query computes the density of generic return types and parameter signatures across all standard libraries.
guided_experiments:
  - "Look at sample generic signatures in Rust: 'WHERE c.language = 'rust' AND c.raw_signature LIKE '%<%''."
  - "Compare generic density between Recommended and Full catalogs to observe how generics scale across large standard libraries."
---*/
SELECT 
    c.language,
    COUNT(c.symbol_id) AS total_callables,
    SUM(CASE WHEN c.return_type_expr LIKE '%<%' OR c.return_type_expr LIKE '%[%]%' THEN 1 ELSE 0 END) AS generic_return_callables,
    SUM(CASE WHEN c.raw_signature LIKE '%<%' OR c.raw_signature LIKE '%[%]%' THEN 1 ELSE 0 END) AS generic_signature_callables,
    ROUND(100.0 * SUM(CASE WHEN c.raw_signature LIKE '%<%' OR c.raw_signature LIKE '%[%]%' THEN 1 ELSE 0 END) / COUNT(c.symbol_id), 2) AS generic_signature_pct
FROM v_all_callables c
GROUP BY c.language
ORDER BY generic_signature_pct DESC;
