# Third-Party Notices & Attributions

The **Universal Type & Symbol System (UTSS)** ecosystem incorporates and interacts with the following third-party software and open-source ecosystems.

---

## 1. Bundled Third-Party Components

### Python Typeshed Stubs (Embedded Mini-Stubs)
- **Location:** `harvesters/utss-python/src/utss/overlay.py` (`EMBEDDED_DEMO_STUBS`)
- **License:** Apache License, Version 2.0
- **Copyright:** (c) 2015 - present Python Typeshed Contributors
- **Notice:** The embedded type stub signatures for standard library modules (`builtins`, `sys`, `os`, `json`) are derived from and modeled on type definitions provided by the [python/typeshed](https://github.com/python/typeshed) project under the Apache License, Version 2.0.

### SQLite3 Amalgamation
- **Location:** `harvesters/utss-cpp/third_party/sqlite3/`
- **License:** Public Domain
- **Notice:** SQLite is in the Public Domain. All of the code and documentation in SQLite has been dedicated to the public domain by the authors.

### Monaco Editor
- **Location:** `workbench/ui/`
- **License:** MIT License
- **Copyright:** (c) 2016 - present Microsoft Corporation
- **Permission:** Granted free of charge under standard MIT terms.

### React & React DOM
- **Location:** `workbench/ui/`
- **License:** MIT License
- **Copyright:** (c) Meta Platforms, Inc. and affiliates.

---

## 2. Third-Party Introspection & Docstring Harvesting Notice

UTSS tools harvest structural API signatures, AST coordinates, parameter metadata, and documentation strings from installed runtimes and third-party standard libraries.

### Structural API Signatures & Types
Extracting structural metadata (function names, parameter types, arity, class hierarchies, and AST coordinates) from installed compilers and libraries is standard bindgen / compiler introspection behavior (analogous to `bindgen`, `SWIG`, or TypeScript `.d.ts` generators) and does not transfer copyleft or proprietary restrictions to the caller.

### Upstream Documentation & Docstrings
Verbatim docstrings and type annotations harvested from external packages retain the copyright of their respective authors:
- **Python Standard Library:** Python Software Foundation (PSF) License Agreement.
- **Python Typeshed (`.pyi` Stubs):** Apache License, Version 2.0 (Copyright (c) 2015 - present Typeshed Contributors). Used during Pass 4 static stub overlay to resolve function parameter types, return annotations, and `@overload` signatures.
- **.NET CoreCLR / BCL Assemblies:** MIT License (Copyright (c) .NET Foundation and Contributors).
- **Rust Standard Library (`core`, `alloc`, `std`):** MIT License OR Apache License, Version 2.0 (Copyright (c) The Rust Project Developers).
- **TypeScript Standard Library Stubs (`lib.es*.d.ts`):** Apache License, Version 2.0 (Copyright (c) Microsoft Corporation).
- **Go Standard Library:** BSD 3-Clause "New" or "Revised" License (Copyright (c) 2009 The Go Authors).
- **C/C++ Standard Headers:** ISO/IEC 14882 standards & compiler implementation runtime library exceptions (GCC Runtime Library Exception / LLVM Exception).

### User-Installed & Domain-Specific Packages (AI/ML, Quantum, Scientific, etc.)
UTSS harvesters and Workbench query tools are designed to index any user-selected third-party or domain-specific library installed in the user's environment (e.g., PyTorch, TensorFlow, JAX, Hugging Face, Qiskit, Cirq, PennyLane, ROS, etc.):

1. **Tool Independence:** UTSS does not bundle, vendor, or distribute source code or binaries of external domain packages. UTSS functions strictly as a compiler introspection and static analysis harness.
2. **Local Analysis & Fair Use:** Running UTSS locally against user-installed packages to extract structural API schemas, function arities, parameter names, and type coordinates constitutes non-infringing functional interoperability introspection (*Google LLC v. Oracle America, Inc.*).
3. **Database Redistribution Notice:** If users or researchers generate SQLite catalogs containing verbatim docstrings, tutorials, or code examples from third-party packages and choose to publicly distribute those `.db` files, they must comply with the upstream licenses of the respective packages (e.g. Apache 2.0, BSD-3-Clause, MIT, or copyleft licenses like GPL/LGPL). Users wishing to distribute catalogs under completely permissive terms are encouraged to either:
   - Strip verbatim docstring fields (retaining only pure functional type signatures and symbol names), or
   - Provide the harvest script/command so downstream users generate the catalog locally from their own installed environment.

If you distribute pre-built databases containing verbatim third-party documentation strings or stub signatures, ensure that downstream recipients are made aware of the respective upstream documentation licenses.

---

## 3. License Texts & Disclaimers

### Apache License, Version 2.0
*Applicable to Python Typeshed stubs and TypeScript standard library stubs:*

```text
Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

### MIT License
*Applicable to Monaco Editor, React, and .NET CoreCLR components:*

```text
Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 4. Trademarks & Nominative Fair Use

All product names, trademarks, registered trademarks, service marks, and brand names referenced in this repository, documentation, or workbench comparative tracks—including but not limited to:
- **Microsoft, .NET, Microsoft.ML, Microsoft.Data.Analysis, System.Numerics.Tensors, Microsoft.ML.Tokenizers, C#** (Microsoft Corporation)
- **Python, PyTorch** (Python Software Foundation, Linux Foundation / PyTorch Foundation)
- **NumPy, Pandas, Matplotlib, SciPy, scikit-learn** (NumFOCUS and respective open-source project steering councils)
- **Plotly** (Plotly, Inc.)
- **Rust, Cargo** (Rust Foundation)
- **Go** (Google LLC)

are the property of their respective owners. Their mention in UTSS and the Workbench is strictly for **identification, nominative comparative analysis, interoperability mapping, and educational study** under nominative fair use principles. Reference to these names does not imply any affiliation with, sponsorship by, or endorsement from the respective trademark holders.
