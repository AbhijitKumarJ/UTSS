/*---
id: cross_04_mutability_guarantees
title: "Mutability Guarantees: Default Immutability vs Explicit Modifiers"
target_language: "federated"
variant_compatibility: ["*"]
suite: "comparative"
level: "Intermediate"
sequence: 4
category: "Memory & Passing"
pedagogical_rationale: >
  Measures state member mutability guarantees and constness enforcement across language paradigms.
  Modern systems languages (Rust) make variables and fields immutable by default, requiring explicit 'mut'.
  C# provides 'readonly' fields and init-only properties for defensive programming.
  TypeScript offers compile-time 'readonly' type modifiers.
  Python relies on naming conventions (_private) and property getter-only facades to simulate immutability.
  This query computes immutability percentages and constant member ratios across all state members.
guided_experiments:
  - "Look at constant definitions: Add 'WHERE m.is_constant = 1' and examine member names and types across languages."
  - "Join with containers: 'JOIN v_all_containers c ON m.container_id = c.container_id AND m.language = c.language' to see which structs/classes are most immutable."
lab_challenge:
  objective: "Write a federated query calculating mutability guarantees across languages, displaying language, total state members, constant members, and immutable members, ordered by total members descending."
  starter_sql: |
    -- Lab Challenge: Analyze mutability and constant guarantees across ecosystems
    SELECT
        m.language,
        COUNT(*) AS total_state_members,
        SUM(CASE WHEN m.is_constant = 1 THEN 1 ELSE 0 END) AS constant_members,
        SUM(CASE WHEN m.is_mutable = 0 THEN 1 ELSE 0 END) AS immutable_members
    FROM v_all_state_members m
    GROUP BY m.language
    ORDER BY total_state_members DESC;
  solution_sql: |
    SELECT
        m.language,
        COUNT(*) AS total_state_members,
        SUM(CASE WHEN m.is_constant = 1 THEN 1 ELSE 0 END) AS constant_members,
        SUM(CASE WHEN m.is_mutable = 0 THEN 1 ELSE 0 END) AS immutable_members
    FROM v_all_state_members m
    GROUP BY m.language
    ORDER BY total_state_members DESC;
  expected_columns:
    - language
    - total_state_members
    - constant_members
    - immutable_members
  min_rows: 3
  xp_reward: 80
  hint: "Use SUM(CASE WHEN m.is_constant = 1 THEN 1 ELSE 0 END) and GROUP BY m.language."
---*/
SELECT 
    m.language,
    COUNT(*) AS total_state_members,
    SUM(CASE WHEN m.is_constant = 1 THEN 1 ELSE 0 END) AS constant_members,
    SUM(CASE WHEN m.is_mutable = 0 THEN 1 ELSE 0 END) AS immutable_members,
    ROUND(100.0 * SUM(CASE WHEN m.is_mutable = 0 THEN 1 ELSE 0 END) / COUNT(*), 1) AS immutability_pct
FROM v_all_state_members m
GROUP BY m.language
ORDER BY immutability_pct DESC;
