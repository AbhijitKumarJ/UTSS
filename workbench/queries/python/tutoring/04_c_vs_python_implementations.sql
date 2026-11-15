/*---
id: py_04_c_vs_python_implementations
title: "CPython Under the Hood: Compiled C Functions vs Pure Python Bytecode"
target_language: "python"
variant_compatibility: ["*"]
suite: "tutoring"
level: "Intermediate"
sequence: 4
category: "Execution & Runtime"
pedagogical_rationale: >
  CPython is a hybrid runtime written in C. Many standard library and built-in functions
  are not interpreted Python bytecode at all—they are direct C function pointers (PyCFunction)
  compiled into shared libraries or the binary itself:
  - Compiled C Functions (is_c_implemented = 1): Zero bytecode overhead, implemented in C,
    often missing Python-level inspectable co_flags or local variable tables.
  - Pure Python Functions (is_c_implemented = 0): Compiled to PyCodeObject bytecode, carrying
    co_flags (e.g. CO_OPTIMIZED, CO_NEWLOCALS, CO_VARARGS, CO_COROUTINE).
  
  This query inspects symbol facets to contrast C-implemented routines against interpreted Python code.
guided_experiments:
  - "Add 'WHERE f.is_c_implemented = 1' to see all native C routines shipped with the environment."
  - "Notice py_runtime_type: native C routines are 'builtin_function_or_method', while pure Python functions are 'function'."
  - "Check co_flags: native functions have co_flags = NULL, whereas pure Python functions carry integer bitmasks."
---*/
SELECT
    s.name AS symbol_name,
    c.qualified_name AS container_path,
    f.py_runtime_type,
    CASE f.is_c_implemented
        WHEN 1 THEN 'Native C Implementation (PyCFunction / Fastcall)'
        ELSE 'Pure Python Bytecode (PyCodeObject)'
    END AS implementation_layer,
    f.co_flags,
    s.provenance,
    s.visibility
FROM symbols s
JOIN containers c ON c.container_id = s.container_id
JOIN py_symbol_facets f ON f.symbol_id = s.symbol_id
WHERE s.symbol_kind IN ('function', 'method')
ORDER BY f.is_c_implemented DESC, s.name ASC
LIMIT 100;
