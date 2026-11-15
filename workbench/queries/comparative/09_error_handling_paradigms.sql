/*---
id: cross_09_error_paradigms
title: "Error Handling Paradigms: Exceptions vs Algebraic Result Types"
target_language: "federated"
variant_compatibility: ["*"]
suite: "comparative"
level: "Advanced"
sequence: 9
category: "Execution & Safety"
pedagogical_rationale: >
  Contrasts two fundamental error handling paradigms in computer science:
  1. Exceptional Control Flow: Python, C#, and C++ rely heavily on class hierarchies subclassing Exception/BaseException,
     which unwind the call stack until caught by a try/catch block.
  2. Explicit Values & Algebraic Types: Go uses explicit multiple return values (T, error) checked with 'if err != nil'.
     Rust utilizes the algebraic Result<T, E> sum type, mandating exhaustive pattern matching or the '?' propagation operator.
  This comparative query maps the prevalence of declared exception types against callables returning explicit Result/error types.
guided_experiments:
  - "Inspect Go callables returning error: 'SELECT cal.raw_signature FROM v_all_callables cal WHERE cal.language = 'go' AND cal.return_type_expr LIKE '%error%' LIMIT 10;'."
  - "Look at Python exception hierarchy names: 'SELECT c.short_name FROM v_all_containers c WHERE c.language = 'python' AND (c.short_name LIKE '%Error' OR c.container_kind = 'exception_class') LIMIT 15;'."
lab_challenge:
  objective: "Write a federated query comparing error handling architectures, returning each language, its declared exception types count, and its explicit result/error returning callables count."
  starter_sql: |
    -- Lab Challenge: Exceptions vs Explicit Algebraic Error Types
    WITH exc AS (
        SELECT 
            c.language,
            COUNT(c.container_id) AS declared_exceptions
        FROM v_all_containers c
        WHERE c.container_kind = 'exception_class' 
           OR c.short_name LIKE '%Exception%' 
           OR c.short_name LIKE '%Error%'
        GROUP BY c.language
    ),
    err_cal AS (
        SELECT 
            cal.language,
            COUNT(cal.symbol_id) AS error_returning_callables
        FROM v_all_callables cal
        WHERE cal.return_type_expr LIKE '%Result%' 
           OR cal.return_type_expr LIKE '%error%'
        GROUP BY cal.language
    )
    SELECT 
        e.language,
        COALESCE(exc.declared_exceptions, 0) AS exception_types_count,
        COALESCE(err_cal.error_returning_callables, 0) AS result_error_callables_count
    FROM v_all_environments e
    LEFT JOIN exc ON e.language = exc.language
    LEFT JOIN err_cal ON e.language = err_cal.language
    ORDER BY exception_types_count DESC;
  solution_sql: |
    WITH exc AS (
        SELECT 
            c.language,
            COUNT(c.container_id) AS declared_exceptions
        FROM v_all_containers c
        WHERE c.container_kind = 'exception_class' 
           OR c.short_name LIKE '%Exception%' 
           OR c.short_name LIKE '%Error%'
        GROUP BY c.language
    ),
    err_cal AS (
        SELECT 
            cal.language,
            COUNT(cal.symbol_id) AS error_returning_callables
        FROM v_all_callables cal
        WHERE cal.return_type_expr LIKE '%Result%' 
           OR cal.return_type_expr LIKE '%error%'
        GROUP BY cal.language
    )
    SELECT 
        e.language,
        COALESCE(exc.declared_exceptions, 0) AS exception_types_count,
        COALESCE(err_cal.error_returning_callables, 0) AS result_error_callables_count
    FROM v_all_environments e
    LEFT JOIN exc ON e.language = exc.language
    LEFT JOIN err_cal ON e.language = err_cal.language
    ORDER BY exception_types_count DESC;
  expected_columns:
    - language
    - exception_types_count
    - result_error_callables_count
  min_rows: 5
  xp_reward: 100
  hint: "Join v_all_environments with CTEs counting exception classes vs callables with 'Result' or 'error' in signatures."
---*/
WITH exc AS (
    SELECT 
        c.language,
        COUNT(c.container_id) AS declared_exceptions
    FROM v_all_containers c
    WHERE c.container_kind = 'exception_class' 
       OR c.short_name LIKE '%Exception%' 
       OR c.short_name LIKE '%Error%'
    GROUP BY c.language
),
err_cal AS (
    SELECT 
        cal.language,
        COUNT(cal.symbol_id) AS error_returning_callables
    FROM v_all_callables cal
    WHERE cal.return_type_expr LIKE '%Result%' 
       OR cal.return_type_expr LIKE '%error%'
    GROUP BY cal.language
)
SELECT 
    e.language,
    COALESCE(exc.declared_exceptions, 0) AS exception_types_count,
    COALESCE(err_cal.error_returning_callables, 0) AS result_error_callables_count
FROM v_all_environments e
LEFT JOIN exc ON e.language = exc.language
LEFT JOIN err_cal ON e.language = err_cal.language
ORDER BY exception_types_count DESC, result_error_callables_count DESC;
