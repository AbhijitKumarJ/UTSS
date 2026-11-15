/*---
id: cross_10_rosetta_crosswalk
title: "The Rosetta Crosswalk: Canonical Collection & Stream Operations"
target_language: "federated"
variant_compatibility: ["*"]
suite: "comparative"
level: "Advanced"
sequence: 10
category: "Execution & Safety"
pedagogical_rationale: >
  Demonstrates cross-language method mapping for canonical collection operations.
  Every general-purpose language defines core dynamic sequences (List, vector, slice, Vec, Array)
  and hash maps (Dictionary, dict, map, HashMap), yet uses different naming conventions:
  - Adding elements: Python 'append', JavaScript 'push', C++ 'push_back', C# 'Add', Rust 'push'.
  - Size/Count: Python 'len()', C# 'Count', C++ 'size()', JavaScript '.length', Go 'len()'.
  - Resetting: Python 'clear()', C# 'Clear()', C++ 'clear()', Rust 'clear()'.
  This query maps live method symbols across containers in all 6 standard libraries, providing the
  concrete lookup table used by source-to-source transpilers during code generation.
guided_experiments:
  - "Query map operations: Change names to 'WHERE s.name IN ('keys', 'values', 'ContainsKey', 'contains_key', 'has')'."
  - "Filter by container: Add 'AND c.short_name IN ('List', 'Dictionary', 'Vec', 'vector')' to inspect exact collection methods."
---*/
SELECT 
    s.language,
    s.name AS method_name,
    c.short_name AS container_name,
    cal.return_type_expr,
    cal.raw_signature
FROM v_all_symbols s
JOIN v_all_containers c ON s.container_id = c.container_id AND s.language = c.language
JOIN v_all_callables cal ON s.symbol_id = cal.symbol_id AND s.language = cal.language
WHERE s.name IN ('append', 'push', 'push_back', 'Add', 'len', 'Count', 'size', 'length', 'clear', 'Clear')
ORDER BY s.name ASC, s.language ASC
LIMIT 50;
