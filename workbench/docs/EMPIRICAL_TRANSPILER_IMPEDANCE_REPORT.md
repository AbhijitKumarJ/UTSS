# Empirical Transpiler Impedance & Cross-Language Parity Report

**Database Catalog Variant:** `recommended`  
**Federated Engines Profiled:** Python (CPython), C# (.NET Core), C++ (Clang/GCC), Go (gc), Rust (rustc), TypeScript (tsc).

---

## Executive Summary

This empirical report synthesizes relational AST and symbol catalog data extracted across 6 major programming languages.
It provides quantitative measurements for semantic distance, compiler representation divergence, and transpilation impedance.

---

## 1. Multi-Language Symbol Census

| Language | Total Symbols | Containers | Callables | Callable Density |
| :--- | :---: | :---: | :---: | :---: |
| **Python** | 4,756 | 312 | 3,257 | 68.5% |
| **Csharp** | 2,153 | 107 | 1,618 | 75.2% |
| **Typescript** | 246 | 25 | 117 | 47.6% |
| **Rust** | 173 | 32 | 37 | 21.4% |
| **Cpp** | 172 | 33 | 35 | 20.3% |
| **Go** | 146 | 44 | 48 | 32.9% |

---

## 2. Mutability & State Safety

| Language | Total State Members | Constants | Immutable Members | Immutability % | Mutability Stance |
| :--- | :---: | :---: | :---: | :---: | :--- |
| **Csharp** | 395 | 70 | 344 | 87.1% | Default Immutable |
| **Typescript** | 24 | 16 | 16 | 66.7% | Defensive/Mixed |
| **Cpp** | 25 | 16 | 16 | 64.0% | Defensive/Mixed |
| **Python** | 1,456 | 273 | 842 | 57.8% | Defensive/Mixed |
| **Go** | 19 | 10 | 10 | 52.6% | Defensive/Mixed |

---

## 3. Parameter Passing Conventions

| Language | Primary Parameter Passing Modes | Key Modifiers / Semantics |
| :--- | :--- | :--- |
| **Python** | `positional_only` (2,477), `positional_or_keyword` (2,202), `var_positional` (397), `var_keyword` (383) | Call-by-object-reference; dynamic positional/keyword |
| **Csharp** | `value` (5,721), `optional` (306), `out` (268), `params` (42) | Value default; explicit `in`, `out`, `ref`, `params` |
| **Cpp** | `val` (16), `const_ref` (7), `pointer` (4), `rvalue_ref` (3) | Value default; explicit `const&`, `&`, `&&` (rvalue) |
| **Go** | `val` (41), `variadic` (10), `slice` (5), `pointer` (2) | Pass-by-value; explicit `*T` pointers |
| **Rust** | `val` (12), `self_ref` (11), `self_mut_ref` (10), `ref` (5) | Strict ownership; `&T` shared borrow, `&mut T` exclusive borrow |
| **Typescript** | `val` (61), `optional` (38), `rest` (5) | Pass-by-sharing; optional/rest parameters |

---

## 4. Function Overloading & Multiplicity

| Language | Total Callables | Overloaded Callables | Overload Ratio | Max Overloads (Single Name) |
| :--- | :---: | :---: | :---: | :---: |
| **Csharp** | 1,618 | 585 | 36.2% | 40 |
| **Python** | 3,257 | 4 | 0.1% | 3 |
| **Typescript** | 117 | 0 | 0.0% | 1 |
| **Rust** | 37 | 0 | 0.0% | 1 |
| **Go** | 48 | 0 | 0.0% | 1 |
| **Cpp** | 35 | 0 | 0.0% | 1 |

---

## 5. Error Handling Paradigms

| Language | Declared Exception Types | Callables Returning Result/Error | Dominant Paradigm |
| :--- | :---: | :---: | :--- |
| **Python** | 81 | 62 | Stack Unwinding Exceptions |
| **Csharp** | 9 | 32 | Explicit Algebraic Result / Error |
| **Rust** | 2 | 7 | Explicit Algebraic Result / Error |
| **Go** | 1 | 10 | Explicit Algebraic Result / Error |
| **Cpp** | 0 | 0 | Explicit Algebraic Result / Error |
| **Typescript** | 0 | 8 | Explicit Algebraic Result / Error |

---

## 6. Pairwise Transpiler Impedance Matrix

The **Transpiler Impedance Distance** $D(S, T) \in [0.0, 1.0]$ scores semantic friction when converting code from Source $S$ to Target $T$.
- **0.0 - 0.2**: Low friction (direct isomorphic mapping)
- **0.3 - 0.5**: Moderate friction (requires AST rewriting / polyfills)
- **0.6 - 0.8**: High friction (semantic impedance: borrow checking, exception inversion)
- **0.9 - 1.0**: Extreme friction (paradigm gap: dynamic to manual/strict lifetimes)

| Source \ Target | Python | Csharp | Cpp | Go | Rust | Typescript |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Python** | `0.00` | `0.54` | `0.83` | `0.74` | `0.95` | `0.17` |
| **Csharp** | `0.37` | `0.00` | `0.29` | `0.58` | `0.74` | `0.29` |
| **Cpp** | `0.59` | `0.22` | `0.00` | `0.59` | `0.55` | `0.47` |
| **Go** | `0.58` | `0.50` | `0.57` | `0.00` | `0.48` | `0.49` |
| **Rust** | `0.66` | `0.52` | `0.41` | `0.35` | `0.00` | `0.57` |
| **Typescript** | `0.11` | `0.41` | `0.66` | `0.59` | `0.80` | `0.00` |

---

## 7. Actionable Architectural Takeaways for Transpiler Synthesis

1. **Python $\to$ Rust (Score: `0.78` - Extreme Friction):**
   - Python's pervasive interior mutability and dynamic references require the transpiler to synthesize `Rc<RefCell<T>>` or `Arc<Mutex<T>>` wrappers unless alias-freedom can be proven via escape analysis.
2. **C# $\to$ Go (Score: `0.58` - Overload Lowering):**
   - C#'s dense method overloading clusters (up to 40 overloads per name) must be lowered into distinct function suffixes (`NewBuffer`, `NewBufferString`).
3. **Exceptions $\to$ Result (Python/C# $\to$ Rust/Go):**
   - Exception-throwing callables must be wrapped into control-flow branching constructs (`match` or `if err != nil`).
4. **Rosetta Crosswalk Collections:**
   - Sequence appending (`append`, `push`, `push_back`, `Add`) and queries (`len`, `Count`, `size`) can be synthesized through the Universal Bridge IR.
