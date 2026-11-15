# UTSS Next Phase Plan: Domain-Specific Ecosystem Expansion & On-Demand Harvesting

**Status:** Planned (Post-Publishing Roadmap)  
**Target Scope:** AI/ML, DataFrames, Tensors, NLP Tokenizers, Scientific Visualization, and Quantum Computing  
**Ecosystems:** Python, C# (.NET), Rust, TypeScript, C++, Go  

---

## 1. Executive Summary & Vision

The initial release of **Universal Type & Symbol System (UTSS)** focused on standard libraries across all six core languages (CPython stdlib, .NET BCL, Rust `core`/`alloc`/`std`, TypeScript `lib.es*.d.ts`, C++20 `std`, and Go standard library).

This **Next Phase Plan** specifies how UTSS will scale into specialized scientific and engineering domains without compromising repository size, license purity, or build simplicity. Users and researchers will be able to harvest domain packages on demand based on their specific research focus, while the Workbench provides dedicated comparative studios, cross-language concept mappings, and transpilation bridge prototypes.

```
+---------------------------------------------------------------------------------------+
|                                    WORKBENCH UI                                        |
|  [Standard Library] | [DataFrames Hub] | [Tensors Hub] | [ML Hub] | [NLP] | [Quantum] |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                             UNIVERSAL BRIDGE LAYER                                    |
|   Standard Bridge (CC0-1.0)  <--->  Domain Conceptual Taxonomy (schemas/domains/*.sql)  |
+---------------------------------------------------------------------------------------+
                                           |
                                           v
+---------------------------------------------------------------------------------------+
|                         ON-DEMAND LOCAL HARVESTING LAYER                              |
|   Standard Catalogs (Default)  +  Optional Domain Overlays (--pkg pandas,torch,...)   |
+---------------------------------------------------------------------------------------+
```

---

## 2. On-Demand Clean Harvesting Architecture

To prevent catalog bloat and eliminate legal entanglement with third-party ecosystems, domain packages will be harvested **on demand** directly from the user's installed environment.

### 2.1 Core Architectural Principles
1. **Pristine Base Isolation:** The baseline standard-library catalogs (`catalog_python.db`, `catalog_cs.db`, etc.) remain clean and untouched.
2. **Layered Domain Catalogs or Tagged Namespaces:**
   - Either stored as modular overlay databases (e.g. `catalog_domain_data_science.db`) or registered within the catalog with `package_kind = 'domain'` and an explicit `distribution_name` tag.
3. **Zero Third-Party Bundling:** No external packages (PyTorch wheels, NuGet assemblies, or Rust crates) are vendored in the UTSS repository.
4. **Resilient Introspection:** If a package is not installed in the user's environment, the harvester reports what was skipped without failing the overall process.

### 2.2 Unified CLI Ergonomics

Users will be able to trigger targeted domain harvesting via intuitive CLI commands:

#### Unified Root Runner:
```bash
# Harvest a specific domain across all installed toolchains:
./harvest_all.sh --domain data-science
./harvest_all.sh --domain ai-ml
./harvest_all.sh --domain quantum

# Or specify packages explicitly:
./harvest_all.sh --pkg pandas,numpy,Microsoft.Data.Analysis,polars
```

#### Language-Specific Harvesters:
```bash
# Python harvester:
python -m utss harvest --pkg pandas,torch,scikit-learn,tokenizers

# C# .NET harvester:
dotnet run --project harvesters/utss-csharp -- harvest \
    --pkg Microsoft.Data.Analysis,System.Numerics.Tensors,Microsoft.ML,Microsoft.ML.Tokenizers

# Rust harvester:
cargo run --manifest-path harvesters/utss-rust/Cargo.toml -- harvest \
    --crates polars,candle-core,linfa,tokenizers
```

---

## 3. The Six Domain Tracks & Comparative Mappings

### Track 1: Tabular Data & DataFrames
*Bridging the leading tabular and columnar memory structures across data engineering and backend services.*

- **Python:** `pandas`, `polars`
- **C# (.NET):** `Microsoft.Data.Analysis` (`DataFrame`, `DataFrameColumn`, `PrimitiveDataFrameColumn<T>`)
- **Rust:** `polars-core`, `polars-lazy`, `arrow-rs`
- **Universal Bridge Concepts:**
  - Columnar data representations & Apache Arrow memory integration.
  - Eager vs. Lazy execution graphs (`df.lazy().filter().collect()` vs. LINQ / query plans).
  - GroupBy aggregations and split-apply-combine semantics.
  - Multi-index, hierarchical indexes, and relational joins (`inner`, `left`, `cross`, `asof`).

### Track 2: Tensors & N-Dimensional Arrays
*Bridging deep learning computational primitives, memory strides, and hardware acceleration.*

- **Python:** `numpy`, `torch.Tensor`, `jax.Array`
- **C# (.NET):** `System.Numerics.Tensors` (.NET 8/9), `TorchSharp`, `NumSharp`
- **Rust:** `candle-core`, `burn::tensor::Tensor`, `ndarray`
- **C++:** `at::Tensor` (LibTorch), `Eigen::Matrix`, `xtensor`
- **Universal Bridge Concepts:**
  - Contiguous vs. non-contiguous memory layouts, strides, and memory offsets.
  - Dynamic broadcasting rules and dimension expansion.
  - Autograd calculation graphs, backward passes, and gradient tracking (`requires_grad`).
  - Device placement abstractions (Host CPU, CUDA, ROCm, Apple Metal, WebGPU).

### Track 3: Machine Learning Pipelines & Estimators
*Bridging classic ML, feature transformers, and model inference pipelines.*

- **Python:** `scikit-learn` (`Pipeline`, `BaseEstimator`, `TransformerMixin`)
- **C# (.NET):** `Microsoft.ML` (`MLContext`, `IEstimator<T>`, `ITransformer`, `DataView`)
- **Rust:** `linfa` (Algorithms, Dataset, Preprocessing)
- **Universal Bridge Concepts:**
  - Estimator vs. Transformer lifecycle (`fit()` -> `transform()` / `predict()`).
  - Column transformers, categorical encoding, and feature scaling.
  - Cross-validation splits, grid search, and pipeline composition.
  - Model serialization (ONNX export/import alignment across runtimes).

### Track 4: NLP & High-Performance Tokenization
*Bridging subword tokenizers, vocabularies, and tensor ingestion for LLMs and transformers.*

- **Python:** `tokenizers` (Hugging Face)
- **C# (.NET):** `Microsoft.ML.Tokenizers` (Official .NET high-performance BPE/WordPiece engine)
- **Rust:** `tokenizers` (Rust upstream core)
- **Universal Bridge Concepts:**
  - Byte-Pair Encoding (BPE), WordPiece, and Unigram tokenization algorithms.
  - Offset mapping, attention masks, and special token padding.
  - Thread-safe parallel batch encoding and zero-copy string slicing.

### Track 5: Scientific Visualization & Plotting
*Bridging declarative and imperative charting, canvases, and figure hierarchies.*

- **Python:** `matplotlib.pyplot`, `seaborn`
- **C# (.NET):** `Plotly.NET`, `ScottPlot`
- **Rust:** `plotters`
- **TypeScript:** `plotly.js`, `echarts`
- **Universal Bridge Concepts:**
  - Figure / Canvas / Subplot hierarchy and coordinate projections.
  - Continuous line/scatter vs. categorical bar/histogram pipelines.
  - Interactive render backends (DOM/SVG vs. headless raster PNG/Skia).

### Track 6: Quantum Computing & Circuit Synthesis
*Bridging qubits, state preparation, quantum gates, and circuit execution.*

- **Python:** `qiskit`, `cirq`, `pennylane`
- **C# (.NET):** `Microsoft.Quantum.Simulation` / QDK (.NET / Q# interop)
- **Rust:** `qip`, `qualang`
- **Universal Bridge Concepts:**
  - Qubit allocation and register sizing.
  - Unitary gate operations: Single-qubit (Pauli-X/Y/Z, Hadamard, Phase), Two-qubit (CNOT, CZ, SWAP).
  - Statevector representations vs. Shot-based measurement sampling.
  - Quantum simulator vs. Hardware QPU execution backends.

---

## 4. Workbench Dedicated Studios & User Experience

Each domain will receive a dedicated studio view in the Workbench React/Monaco UI:

```
+-------------------------------------------------------------------------------------+
| WORKBENCH: TENSORS & N-D ARRAYS STUDIO                                              |
| Track: [ PyTorch / NumPy ]  <===>  [ System.Numerics.Tensors ]  <===>  [ Candle ]   |
+-------------------------------------------------------------------------------------+
| 1. CONCEPTUAL ROSETTA STONE                                                         |
| - Concept: Tensor Stride & Contiguity Check                                         |
| - Python:  `t.is_contiguous()`, `t.stride()`                                        |
| - C# 9:    `Tensor<T>.IsContiguous`, `Tensor<T>.Strides`                             |
| - Rust:    `tensor.is_contiguous()`, `tensor.stride()`                              |
+-------------------------------------------------------------------------------------+
| 2. LIVE INTROSPECTION & OVERLOAD INSPECTOR                                          |
| [Status: Locally Harvested (342 symbols)]                                           |
| - Select Method: Tensor.matmul                                                      |
|   * Python Signature: matmul(other: Tensor) -> Tensor                               |
|   * C# Signature:     Tensor.MatMul(Tensor<T> left, Tensor<T> right)                |
|   * Rust Signature:   pub fn matmul(&self, rhs: &Tensor) -> Result<Tensor>          |
+-------------------------------------------------------------------------------------+
| 3. TRANSPILER IMPEDANCE & BRIDGE GENERATOR                                          |
| [Emit Cross-Language Invoker Wrapper (.g.cs / .rs)]                                 |
+-------------------------------------------------------------------------------------+
```

### Dynamic Graceful Degradation:
If a user loads a studio without having harvested that package locally:
- The **Conceptual Rosetta Stone** is fully available (based on static curriculum tables).
- The **Live Introspection Panel** displays an informative, 1-click terminal setup command:
  ```bash
  # Click to copy:
  pip install torch && python -m utss harvest --pkg torch
  ```

---

## 5. Phased Implementation Roadmap

| Milestone | Target Deliverable | Scope & Verification |
| :--- | :--- | :--- |
| **Phase 1: CLI On-Demand Harvesters** | Add `--pkg` & `--domain` flags to all 6 harvesters | Allow introspecting any installed library into modular `.db` layers. |
| **Phase 2: Domain Schema Taxonomies** | Create `schemas/domains/*.sql` | DDL definitions for DataFrames, Tensors, ML, NLP, Visualization, Quantum. |
| **Phase 3: Tabular & Tensors Hubs** | Workbench DataFrames & Tensors Studios | Live side-by-side analysis for Pandas, PyTorch, ML.NET, Candle, Polars. |
| **Phase 4: ML & Tokenizers Hubs** | Workbench Scikit-Learn & Tokenizers Studios | Feature pipelines and HuggingFace vs. Microsoft.ML.Tokenizers mapping. |
| **Phase 5: Quantum & Plotting Hubs** | Workbench Quantum & Visualization Studios | Qiskit/Cirq vs. QDK and Matplotlib vs. Plotly.NET/ScottPlot. |

---

## 6. Licensing, Trademark, and Legal Safety

1. **Toolmaker Protection:** UTSS functions strictly as a compiler introspection harness. Local scanning of user-installed libraries is non-infringing fair use (*Google v. Oracle*, US 17 U.S.C. § 107/117, EU Software Directive Art. 5(3)).
2. **Nominative Fair Use:** All brand names (PyTorch, Pandas, Microsoft.ML, Plotly, etc.) are used solely to identify the technology for comparative analysis, fully documented in `THIRD_PARTY_NOTICES.md` Section 4.
3. **Generated Output Exception:** Any generated interop wrappers, bridges, or bindings emitted by these studios are free of UTSS copyleft restrictions under `LICENSE-GENERATED-OUTPUT.md`.
