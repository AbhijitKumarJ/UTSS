/*---
id: py_03_keywords_and_soft_keywords
title: "Grammar Boundaries: Hard Keywords vs Soft Keywords"
target_language: "python"
variant_compatibility: ["*"]
suite: "tutoring"
level: "Basic"
sequence: 3
category: "Grammar & Lexical"
pedagogical_rationale: >
  Python's lexical grammar has evolved from rigid keywords to contextual tokens:
  1. Hard Keywords (e.g. 'def', 'class', 'import', 'yield'): Reserved unconditionally.
     Using them as variable or function names produces an immediate SyntaxError.
  2. Soft Keywords (e.g. 'match', 'case', '_', and Python 3.12's 'type'): Contextual tokens.
     They act as keywords only within specific syntactic productions (e.g. pattern matching
     statements or type alias declarations), but remain completely valid variable names,
     function names, or attribute names elsewhere!
  
  This query queries the ambient scope to contrast hard keywords against contextual soft keywords.
guided_experiments:
  - "Filter for 'soft_keyword' only: 'WHERE s.symbol_kind = ''soft_keyword''' to observe Python's contextual tokens."
  - "Notice the start_line and docstring fields: keywords in Python have language-level documentation."
  - "Test what happens in pure Python: try typing 'match = 42' vs 'def = 42' in an interactive interpreter."
---*/
SELECT
    s.symbol_id,
    s.name AS token_name,
    s.symbol_kind,
    CASE s.symbol_kind
        WHEN 'keyword' THEN 'Rigid: Forbidden as variable or attribute name'
        WHEN 'soft_keyword' THEN 'Contextual: Legal identifier outside pattern/type syntax'
        ELSE 'Other'
    END AS lexical_status,
    s.provenance,
    s.docstring
FROM symbols s
JOIN containers c ON c.container_id = s.container_id
WHERE s.symbol_kind IN ('keyword', 'soft_keyword')
ORDER BY s.symbol_kind ASC, s.name ASC;
