/*---
id: cross_05_overload_multiplicity
title: "Static Overloading vs Dynamic Multiplicity"
target_language: "federated"
variant_compatibility: ["*"]
suite: "comparative"
level: "Intermediate"
sequence: 5
category: "Polymorphism & Contracts"
pedagogical_rationale: >
  Analyzes function signature polymorphism across static and dynamic language families.
  In C# and C++, compile-time method overloading is ubiquitous—single names like Console.WriteLine
  or std::basic_string::append possess dozens of distinct parameter signatures.
  In contrast, Go and Rust deliberately disallow function overloading; different variants must receive
  distinct descriptive names (e.g. NewReader vs NewReaderSize).
  Python natively uses single runtime method dispatch with dynamic arguments (*args, **kwargs),
  using @typing.overload purely for static type checker hints.
  This query quantifies overload prevalence and maximum multiplicity across stdlibs.
guided_experiments:
  - "Discover the most overloaded method: Query 'SELECT s.name, c.language, c.overload_count FROM v_all_callables c JOIN v_all_symbols s ON c.symbol_id = s.symbol_id AND c.language = s.language ORDER BY c.overload_count DESC LIMIT 5;'."
  - "Contrast C# overloads with Python default arguments to see two different solutions to API flexibility."
---*/
SELECT 
    c.language,
    COUNT(c.symbol_id) AS total_callables,
    SUM(CASE WHEN c.has_overloads = 1 THEN 1 ELSE 0 END) AS overloaded_callables,
    MAX(c.overload_count) AS max_overloads_for_single_name,
    ROUND(AVG(CASE WHEN c.has_overloads = 1 THEN c.overload_count ELSE 1 END), 2) AS avg_overload_multiplicity
FROM v_all_callables c
GROUP BY c.language
ORDER BY overloaded_callables DESC;
