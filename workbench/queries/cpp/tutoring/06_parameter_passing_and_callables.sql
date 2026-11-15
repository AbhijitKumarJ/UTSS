/*---
id: cpp_06_parameter_passing_and_callables
title: "Calling Conventions: Parameter Passing Semantics & Signatures"
target_language: cpp
variant_compatibility:
  - "*"
suite: tutoring
level: Advanced
sequence: 6
category: "Callables & ABI"
pedagogical_rationale: |
  C++ callable signatures express precise memory semantics:
  - `pass_by`: Pass by value (copies or moves), pass by reference (`&`), or pass by rvalue reference (`&&`) for move semantics.
  - Return types and overload counts: C++ allows function overloading based on argument types, which the compiler mangles into unique linker symbols.
  This query inspects callable signatures, return types, and static member qualifiers across the translation units.
guided_experiments:
  - "Filter for static member functions: `WHERE sf.is_static = 1`."
  - "Examine functions returning smart pointers (`std::unique_ptr` or `std::shared_ptr`) by adding `WHERE cal.return_type_expr LIKE '%ptr%'`."
---*/
SELECT 
    s.name AS function_name,
    s.qualified_name,
    sf.access_specifier,
    sf.is_static,
    sf.pass_by,
    cal.return_type_expr,
    cal.raw_signature
FROM symbols s
JOIN cpp_symbol_facets sf ON s.symbol_id = sf.symbol_id
JOIN callables cal ON s.symbol_id = cal.symbol_id
ORDER BY sf.is_static DESC, s.name ASC
LIMIT 30;
