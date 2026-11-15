/*---
id: py_07_callable_signatures_and_params
title: "Calling Conventions: Positional-Only, Keyword-Only, and Signatures"
target_language: "python"
variant_compatibility: ["*"]
suite: "tutoring"
level: "Intermediate"
sequence: 7
category: "Callables & Signatures"
pedagogical_rationale: >
  Python supports five distinct parameter passing modes (defined in inspect.Parameter):
  1. 'positional_only': Passed by position only, never by keyword (enforced before '/' syntax).
  2. 'positional_or_keyword': Standard Python argument mode.
  3. 'var_positional': Collects excess positional arguments (*args).
  4. 'keyword_only': Arguments appearing after '*' that MUST be passed by name.
  5. 'var_keyword': Collects excess keyword arguments (**kwargs).
  
  This query inspects callable signatures and parameter definitions, illustrating how
  modern Python enforces strict API contracts and positional-only arguments in core modules.
guided_experiments:
  - "Filter for 'positional_only': 'WHERE p.pass_kind = ''positional_only''' to see which stdlib functions require positional calls."
  - "Filter for 'keyword_only' to inspect modern APIs that prevent ambiguous positional ordering."
  - "Inspect 'cal.is_async': find coroutines and examine how their return types differ from sync callables."
---*/
SELECT
    s.qualified_name AS callable_name,
    p.ordinal AS param_index,
    p.name AS param_name,
    p.pass_kind,
    p.type_expr AS type_annotation,
    p.default_expr AS default_value,
    cal.return_type_expr,
    cal.raw_signature,
    cal.signature_source
FROM parameters p
JOIN callables cal ON cal.symbol_id = p.callable_symbol_id
JOIN symbols s ON s.symbol_id = cal.symbol_id
WHERE p.pass_kind IN ('positional_only', 'keyword_only', 'var_positional', 'var_keyword')
ORDER BY p.pass_kind ASC, s.qualified_name ASC, p.ordinal ASC
LIMIT 100;
