# In-UI Empirical Data Science & Impedance Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an interactive, in-UI empirical data science and 6×6 transpiler impedance matrix dashboard inside UTSS Comparative Analytics.

**Architecture:** Expose backend REST endpoints (`/api/analysis/comparative`, `/api/analysis/report`) powered by the federated engine and `tools/utss_comparative_analysis.py`. Build a React dashboard with sub-mode switching between SQL Curriculum and Visual Dashboard, including interactive SVG heatmaps, parameter spectrums, mutability charts, and drill-down impedance penalty inspectors.

**Tech Stack:** FastAPI, SQLite (Federated multi-attach views), React 18, TypeScript, SVG Data Visualizations, CSS Variables.

**Spec:** `docs/Ideas/cross lang and analysis plans.md`

## Global Constraints

- Backend queries must run in read-only mode against federated databases (`federated_recommended` or `federated_full`).
- All interactive charts must be rendered in pure React + SVG/HTML with zero external chart library bloat (offline self-contained).
- All 4 themes (UTSS Slate Dark, VS Code Dark+, VS Code Light+, Monokai) must be supported via CSS variables.
- Sub-mode switching in `Comparative Analytics` must seamlessly toggle between the existing 10-lesson SQL Curriculum and the Empirical Visual Dashboard.
- All backend endpoints must have comprehensive pytest coverage.

## Review Focus

- **Variant selection**: Supports switching between `recommended` and `full` catalogs with dynamic recalculation/caching.
- **Pairwise impedance symmetry vs asymmetry**: Source $\to$ Target impedance is directional (e.g. Python $\to$ Rust impedance $\neq$ Rust $\to$ Python impedance) and must display accurately.
- **Empty / partial database handling**: Gracefully renders when a language catalog has 0 entries in a category without dividing by zero.
- **Interactive drill-down**: Clicking a cell in the 6×6 heatmap exposes the detailed metric breakdown for that language pair.
- **Theme contrast**: Color-graded heatmap cells and spectrum bars maintain legible text contrast in both light and dark themes.

---

### Task 1: Backend Analysis API Endpoints & Caching

**Files:**
- Modify: `server/routes.py`
- Test: `tests/test_analysis_api.py`

**Steps:**
- [x] Write failing test `tests/test_analysis_api.py` validating:
  - `GET /api/analysis/comparative?variant=recommended` returns 200 with `languages`, `symbol_census`, `mutability_matrix`, `parameter_passing`, `overloading_metrics`, `error_handling`, `pairwise_impedance`.
  - `GET /api/analysis/comparative?variant=full` returns 200.
  - `GET /api/analysis/report?variant=recommended` returns 200 with markdown text and download headers.
  - Invalid variant parameter handles fallback or validation cleanly.
- [x] Run `pytest tests/test_analysis_api.py` and verify failure.
- [x] Implement backend routes in `server/routes.py`:
  - Import `run_comparative_analysis`, `generate_markdown_report` from `tools.utss_comparative_analysis`.
  - Implement caching dictionary `_analysis_cache` keyed by variant to prevent re-querying SQLite on every tab switch.
  - Expose `GET /api/analysis/comparative` returning JSON metrics.
  - Expose `GET /api/analysis/report` returning Markdown string or file download.
- [x] Run `pytest tests/test_analysis_api.py` and ensure tests pass.
- [x] Commit: `feat(api): expose comparative analysis metrics and report endpoints`

---

### Task 2: TypeScript Types & API Client for Analysis

**Files:**
- Modify: `React_UI/src/types.ts`
- Modify: `React_UI/src/services/api.ts`

**Steps:**
- [x] Update `React_UI/src/types.ts` to define:
  - `SymbolCensusItem`
  - `MutabilityItem`
  - `ParameterPassingItem`
  - `OverloadingItem`
  - `ErrorHandlingItem`
  - `PairwiseImpedanceMatrix`
  - `ComparativeAnalysisData`
- [x] Update `React_UI/src/services/api.ts` to add:
  - `fetchComparativeAnalysis(variant?: string): Promise<ComparativeAnalysisData>`
  - `fetchAnalysisReport(variant?: string): Promise<string>`
- [x] Verify build with `tsc --noEmit` in `React_UI`.
- [x] Commit: `feat(ui): add TypeScript types and API client functions for comparative analysis`

---

### Task 3: Interactive 6×6 Transpiler Impedance Heatmap & Penalty Inspector

**Files:**
- Create: `React_UI/src/components/analysis/ImpedanceHeatmap.tsx`
- Create: `React_UI/src/components/analysis/ImpedanceDetailModal.tsx`
- Modify: `React_UI/src/App.css`

**Steps:**
- [x] Implement `ImpedanceHeatmap.tsx`:
  - 6×6 grid representing Source (rows) $\to$ Target (columns) for `python`, `csharp`, `cpp`, `go`, `rust`, `typescript`.
  - Dynamic color-coding from low impedance (greenish hue $\le 0.25$), moderate ($0.25 - 0.55$), high ($0.55 - 0.80$), to severe ($\ge 0.80$).
  - Interactive hover state showing source $\to$ target score.
  - Click handler selecting a cell and opening `ImpedanceDetailModal`.
- [x] Implement `ImpedanceDetailModal.tsx`:
  - Displays source $\to$ target pair name and total impedance score.
  - Breakdown of impedance contributors: Mutability mismatch, Overload gap, Parameter passing disparity, Error handling paradigm clash.
  - Architectural transpiler guidance (e.g. "Python $\to$ Rust requires synthesizing Builder structs for default parameters and mapping exceptions to Result<T, E>").
- [x] Add CSS styling in `App.css` for grid, cells, badges, and modal.
- [x] Commit: `feat(ui): implement interactive 6x6 transpiler impedance heatmap and detail inspector`

---

### Task 4: Multi-Language Empirical Metric Visualizers (Census, Spectrum, Mutability, Overload)

**Files:**
- Create: `React_UI/src/components/analysis/SymbolCensusChart.tsx`
- Create: `React_UI/src/components/analysis/ParameterSpectrumChart.tsx`
- Create: `React_UI/src/components/analysis/MutabilityChart.tsx`
- Create: `React_UI/src/components/analysis/OverloadErrorChart.tsx`
- Modify: `React_UI/src/App.css`

**Steps:**
- [x] Implement `SymbolCensusChart.tsx`:
  - Grouped responsive horizontal/vertical bars comparing total symbols, containers, and callables across all 6 languages.
- [x] Implement `ParameterSpectrumChart.tsx`:
  - Stacked horizontal distribution bar per language showing percentages of `val`, `ref`, `mut_ref`, `pointer`, `out`, `positional_or_keyword`, `variadic`.
  - Interactive legend with filter toggles and tooltips explaining calling semantics.
- [x] Implement `MutabilityChart.tsx`:
  - Visual gauge/bar comparing state member immutability ratios (Rust ~100% vs C# vs Python/TS).
- [x] Implement `OverloadErrorChart.tsx`:
  - Side-by-side comparison of overload multiplicity (C#/C++/TS high vs Rust/Go 0) and error paradigm distribution (exceptions vs Result/Option vs return tuple).
- [x] Add clean CSS styling for charts, tooltips, bars, and legends.
- [x] Commit: `feat(ui): add empirical visualization charts for census, parameters, mutability, and error handling`

---

### Task 5: Comparative Dashboard Orchestration & Sub-Mode Integration in Comparative Analytics

**Files:**
- Create: `React_UI/src/components/analysis/ComparativeDashboard.tsx`
- Modify: `React_UI/src/App.tsx`
- Modify: `React_UI/src/App.css`

**Steps:**
- [x] Implement `ComparativeDashboard.tsx`:
  - Header toolbar with catalog variant toggle (`Recommended` vs `Full`), Refresh button, and "Download Markdown Report" button.
  - High-level metric summary cards (Total Languages: 6, Total Analyzed Symbols, Max Impedance Pair, Min Impedance Pair).
  - Visual dimension tabs:
    - `⚡ Transpiler Impedance Matrix (6×6)`
    - `📊 Symbol & Container Census`
    - `🧬 Parameter Passing Spectrum`
    - `🔒 Mutability & State Safety`
    - `⚙️ Overloading & Error Handling`
- [x] In `App.tsx`:
  - When `activeSuite === "comparative"`, provide a view mode toggle in the UI:
    - `[ 📖 Curriculum SQL Runner ]` (the 10-lesson interactive SQL track)
    - `[ 📈 Empirical Metrics & Impedance ]` (the visual comparative dashboard)
  - Ensure state persists smoothly and theme propagates across all views.
- [x] Build React frontend (`npm --prefix React_UI run build`).
- [x] Run all automated backend and frontend tests (`pytest -v`).
- [x] Commit: `feat(ui): integrate empirical comparative dashboard with sub-mode switcher in comparative analytics`
