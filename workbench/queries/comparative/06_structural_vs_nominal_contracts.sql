/*---
id: cross_06_structural_vs_nominal
title: "Structural vs Nominal Contracts: Interfaces, Traits, and Concepts"
target_language: "federated"
variant_compatibility: ["*"]
suite: "comparative"
level: "Advanced"
sequence: 6
category: "Polymorphism & Contracts"
pedagogical_rationale: >
  Maps behavioral contracts across language type systems:
  - C# utilizes nominal interfaces (IDisposable, IEnumerable) requiring explicit class implementation declarations.
  - Go relies on implicit structural interfaces (io.Reader, fmt.Stringer) satisfied by any type implementing matching methods.
  - Rust employs traits (Read, Write, Clone) implemented via decoupled 'impl Trait for Type' blocks.
  - TypeScript supports structural interface typing where shape determines assignability.
  - C++20 introduces concepts for compile-time template constraints.
  This query catalogs all interface, trait, and concept contracts defined in each language's catalogs.
guided_experiments:
  - "Inspect contract methods: Join with symbols to see method definitions inside interfaces: 'JOIN v_all_symbols s ON s.container_id = c.container_id AND s.language = c.language'."
  - "Examine C# IDisposable vs Python context managers (__enter__/__exit__) as structural contract equivalents."
---*/
SELECT 
    c.language,
    c.container_kind,
    COUNT(*) AS contract_count,
    SUBSTR(GROUP_CONCAT(c.short_name, ', '), 1, 80) AS sample_contracts
FROM v_all_containers c
WHERE c.container_kind IN ('interface', 'trait', 'concept')
GROUP BY c.language, c.container_kind
ORDER BY contract_count DESC;
