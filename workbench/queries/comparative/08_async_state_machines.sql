/*---
id: cross_08_async_state_machines
title: "Async Coroutines, Generators, and Concurrency Primitives"
target_language: "federated"
variant_compatibility: ["*"]
suite: "comparative"
level: "Advanced"
sequence: 8
category: "Execution & Safety"
pedagogical_rationale: >
  Evaluates asynchronous coroutine and generator state-machine prevalence across standard libraries.
  In Python, C#, and TypeScript, asynchronous execution is explicitly colored: functions marked 'async'
  transform into compiler-synthesized state machines returning Tasks, Promises, or Coroutines.
  In Rust, async fn returns anonymous Futures driven cooperatively by external runtimes (like Tokio).
  In contrast, Go rejects function-coloring entirely: goroutines provide synchronous, blocking I/O
  multiplexed onto an M:N green-thread runtime without any 'async' keywords.
  This query quantifies is_async and is_generator callables across all 6 language catalogs.
guided_experiments:
  - "Inspect async callable signatures: Add 'WHERE c.is_async = 1' to view the return types (Task, Promise, Coroutine) across languages."
  - "Examine Python generators: Add 'WHERE c.language = 'python' AND c.is_generator = 1' to find yield-based iterators."
---*/
SELECT 
    c.language,
    COUNT(c.symbol_id) AS total_callables,
    SUM(CASE WHEN c.is_async = 1 THEN 1 ELSE 0 END) AS async_callables,
    SUM(CASE WHEN c.is_generator = 1 THEN 1 ELSE 0 END) AS generator_callables
FROM v_all_callables c
GROUP BY c.language
ORDER BY async_callables DESC;
