/*---
id: cross_03_parameter_passing
title: "Parameter Passing & Ownership Semantics Matrix"
target_language: "federated"
variant_compatibility: ["*"]
suite: "comparative"
level: "Intermediate"
sequence: 3
category: "Memory & Passing"
pedagogical_rationale: >
  Profiles parameter passing conventions and ownership semantics across language ecosystems.
  C++ exposes fine-grained value, const-ref, mutable-ref, and rvalue-ref (move) semantics.
  C# features explicit 'in', 'out', 'ref', and 'params' modifiers alongside standard value passing.
  Go distinguishes between copy-by-value and pointer passing.
  Python relies on call-by-object-reference with optional positional-only and keyword-only distinctions.
  Rust enforces strict borrow checking via immutable and mutable borrows (& and &mut).
  This query builds the cross-language parameter semantics distribution matrix.
guided_experiments:
  - "Inspect C# out parameters: Add 'WHERE p.language = 'csharp' AND p.pass_kind = 'out'' to see methods relying on multiple returns."
  - "Compare reference passing density: Calculate total reference/pointer parameters versus plain value parameters across languages."
lab_challenge:
  objective: "Write a SQL query profiling parameter passing conventions across all languages, returning the language name, parameter passing kind, and total count of parameters for that passing convention, ordered by language and total count descending."
  starter_sql: |
    -- Lab Challenge: Profile parameter passing conventions across ecosystems
    SELECT 
        p.language,
        p.pass_kind,
        COUNT(*) AS total_params
    FROM v_all_parameters p
    WHERE p.pass_kind IS NOT NULL
    GROUP BY p.language, p.pass_kind
    ORDER BY p.language ASC, total_params DESC;
  solution_sql: |
    SELECT 
        p.language,
        p.pass_kind,
        COUNT(*) AS total_params
    FROM v_all_parameters p
    WHERE p.pass_kind IS NOT NULL
    GROUP BY p.language, p.pass_kind
    ORDER BY p.language ASC, total_params DESC;
  expected_columns:
    - language
    - pass_kind
    - total_params
  min_rows: 5
  xp_reward: 75
  hint: "Filter with WHERE p.pass_kind IS NOT NULL and GROUP BY p.language, p.pass_kind."
---*/
SELECT 
    p.language,
    p.pass_kind,
    COUNT(*) AS total_params,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY p.language), 2) AS pct_of_language
FROM v_all_parameters p
WHERE p.pass_kind IS NOT NULL
GROUP BY p.language, p.pass_kind
ORDER BY p.language ASC, total_params DESC;
