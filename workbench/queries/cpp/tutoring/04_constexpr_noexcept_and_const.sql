/*---
id: cpp_04_constexpr_noexcept_and_const
title: "Compile-Time & Optimization Guarantees: constexpr, noexcept & const"
target_language: cpp
variant_compatibility:
  - "*"
suite: tutoring
level: Intermediate
sequence: 4
category: "Modern C++ Specifiers"
pedagogical_rationale: |
  Modern C++ relies on three vital function and member specifiers:
  - `constexpr`: Evaluated at compile-time when constant arguments are supplied, embedding values straight into the binary.
  - `noexcept`: Guarantees no exceptions are thrown, allowing `std::vector` to move elements instead of copying during reallocations.
  - `const`: Member functions that do not mutate the object's observable state, enabling invocation on const references.
  This query catalogs methods and functions bearing these modern contract qualifiers.
guided_experiments:
  - "Filter for functions that are strictly compile-time evaluable: `WHERE sf.is_constexpr = 1`."
  - "Check how many methods are marked both const and noexcept: `WHERE sf.is_const = 1 AND sf.is_noexcept = 1`."
---*/
SELECT 
    s.name AS symbol_name,
    s.qualified_name,
    sf.access_specifier,
    sf.is_constexpr,
    sf.is_noexcept,
    sf.is_const,
    sf.is_inline,
    cal.return_type_expr
FROM symbols s
JOIN cpp_symbol_facets sf ON s.symbol_id = sf.symbol_id
LEFT JOIN callables cal ON s.symbol_id = cal.symbol_id
WHERE sf.is_constexpr = 1 OR sf.is_noexcept = 1 OR sf.is_const = 1
ORDER BY sf.is_constexpr DESC, sf.is_noexcept DESC, sf.is_const DESC, s.name ASC
LIMIT 30;
