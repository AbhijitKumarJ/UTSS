# React UI with Monaco Editor & Multi-Theme Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a client-only React + TypeScript application in `React_UI/` integrating Monaco Editor (`@monaco-editor/react`) and a multi-theme system (VS Code Dark, VS Code Light, Monokai, UTSS Dark), configured to compile directly into `../static` for seamless FastAPI serving.

**Architecture:** A Vite-powered React 19 application in `React_UI/` coordinates state (active database, active query, current SQL, query results, active theme) using React context and custom hooks. The editor utilizes `@monaco-editor/react` with theme-synced syntax highlighting and `Ctrl+Enter` execution. The build pipeline outputs HTML, CSS, and JS bundles directly to `../static/` where FastAPI serves it at `http://localhost:8000/`.

**Tech Stack:** React 19, TypeScript, Vite, `@monaco-editor/react`, CSS Custom Properties (Theme tokens).

**Spec:** `docs/superpowers/specs/2026-11-13-react-ui-monaco-themes-design.md`

## Global Constraints

- Output must build directly into `../static/` so FastAPI serves it at `/` with no backend changes.
- In dev mode, Vite must proxy `/api` calls to `http://localhost:8000`.
- Themes must support: `utss-dark`, `vscode-dark`, `vscode-light`, and `monokai`.
- Switching databases in the UI must preserve user-modified SQL in the Monaco editor.
- Monaco Editor must bind `Ctrl+Enter` (and `Cmd+Enter`) to trigger query execution.

## Review Focus

1. **Monaco Editor Theme Synchronization**: Changing the UI theme in the top bar must instantly update Monaco's editor theme (`vs-dark`, `vs`, `monokai`) without requiring an editor re-mount or losing cursor position.
2. **Editor Value Preservation across DB Switches**: Switching the database dropdown must not overwrite any modified SQL text in the editor.
3. **Table Responsiveness & NULL Rendering**: Table must properly scroll horizontally for wide schemas and vertically for up to 500 rows, cleanly distinguishing SQL NULLs from empty strings.
4. **Vite Relative Path Resolution**: Assets in `../static/` must be referenced using root-relative paths (`/assets/...`) so FastAPI serves them correctly without 404s.
5. **Client-side CSV Download**: Exporting query results to CSV must cleanly escape double quotes, commas, and newlines.

---

### Task 1: Scaffolding `React_UI` with Vite, TypeScript & Build Config

**Files:**
- Create: `React_UI/package.json`
- Create: `React_UI/tsconfig.json`
- Create: `React_UI/vite.config.ts`
- Create: `React_UI/index.html`
- Create: `React_UI/src/main.tsx`

**Interfaces:**
- Produces: Working Vite build setup targeting `../static` with `/api` proxy to `http://localhost:8000`.

- [ ] **Step 1: Create package.json and install dependencies in `React_UI`**

Dependencies: `react`, `react-dom`, `@monaco-editor/react`. DevDependencies: `typescript`, `@types/react`, `@types/react-dom`, `@vitejs/plugin-react`, `vite`.

- [ ] **Step 2: Create `tsconfig.json` and `vite.config.ts`**

Configure `build.outDir: "../static"`, `build.emptyOutDir: false`, `server.proxy: { "/api": "http://localhost:8000" }`.

- [ ] **Step 3: Create minimal entry files (`index.html`, `src/main.tsx`) and verify build**

Run: `npm run build` or `pnpm run build` inside `React_UI`.
Expected: Successful compile to `../static`.

- [ ] **Step 4: Commit**

```bash
git add React_UI/
git commit -m "feat(react-ui): scaffold React_UI project with Vite, TypeScript, and Monaco"
```

---

### Task 2: Types, API Client & Multi-Theme System

**Files:**
- Create: `React_UI/src/types.ts`
- Create: `React_UI/src/api.ts`
- Create: `React_UI/src/styles/themes.css`
- Create: `React_UI/src/context/ThemeContext.tsx`

**Interfaces:**
- Produces:
  - `fetchDatabases()`, `fetchQueries()`, `executeQuery()`, `exportCsv()`
  - `ThemeContext` providing `theme`, `setTheme`, and mapping to Monaco theme (`vs-dark`, `vs`, `monokai`).

- [ ] **Step 1: Define TypeScript interfaces in `src/types.ts`**

Define `DatabaseInfo`, `QueryInfo`, `ExecuteResponse`, `ThemeName`.

- [ ] **Step 2: Implement REST API client in `src/api.ts`**

Wrap `/api/dbs`, `/api/queries`, `/api/execute`, and `/api/export`.

- [ ] **Step 3: Implement CSS theme definitions in `src/styles/themes.css`**

Define CSS variables for `utss-dark`, `vscode-dark`, `vscode-light`, and `monokai`.

- [ ] **Step 4: Implement `ThemeContext.tsx` with localStorage persistence**

Expose `useTheme()` hook managing `data-theme` on `document.documentElement` and returning corresponding Monaco editor theme.

- [ ] **Step 5: Commit**

```bash
git add React_UI/src/
git commit -m "feat(react-ui): implement API client, data types, and multi-theme provider"
```

---

### Task 3: Top Navigation Bar & Theme Switcher Component

**Files:**
- Create: `React_UI/src/components/TopNav.tsx`

**Interfaces:**
- Consumes: `ThemeContext`, `DatabaseInfo`
- Produces: Header bar with brand logo, mode tabs (`tutoring` vs `comparative`), database dropdown with live symbol badges, and theme switcher dropdown.

- [ ] **Step 1: Implement `TopNav.tsx`**

Include database dropdown, mode tab buttons, and theme select (`UTSS Slate Dark`, `VS Code Dark+`, `VS Code Light+`, `Monokai`).

- [ ] **Step 2: Verify theme switching changes root `data-theme` attribute**

- [ ] **Step 3: Commit**

```bash
git add React_UI/src/components/TopNav.tsx
git commit -m "feat(react-ui): implement TopNav with database switcher and theme picker"
```

---

### Task 4: Curriculum Sidebar & Collapsible Tutor Card

**Files:**
- Create: `React_UI/src/components/Sidebar.tsx`
- Create: `React_UI/src/components/TutorCard.tsx`

**Interfaces:**
- Consumes: `QueryInfo`, `activeQueryId`, callbacks `onSelectQuery`
- Produces:
  - Searchable, level-filtered curriculum query list with sequence numbers.
  - Collapsible Tutor Card with lesson title, level badges, pedagogical rationale, and guided experiments list.

- [ ] **Step 1: Implement `Sidebar.tsx`**

Include search input, difficulty filter pills (`All`, `Basic`, `Intermediate`, `Advanced`), and lesson card list.

- [ ] **Step 2: Implement `TutorCard.tsx`**

Include toggle button (`[− Collapse Notes]` / `[+ Expand Notes]`), rationale callout, and guided experiments.

- [ ] **Step 3: Commit**

```bash
git add React_UI/src/components/
git commit -m "feat(react-ui): implement Sidebar and collapsible TutorCard components"
```

---

### Task 5: Monaco SQL Editor Component

**Files:**
- Create: `React_UI/src/components/SqlEditor.tsx`

**Interfaces:**
- Consumes: `sql`, `onSqlChange`, `onRunQuery`, `onResetQuery`, `theme`
- Produces: Full Monaco Editor instance with SQL syntax highlighting, line numbers, `Ctrl+Enter` shortcut, toolbar (Run Query, Reset, Copy SQL).

- [ ] **Step 1: Implement `SqlEditor.tsx` using `@monaco-editor/react`**

Bind `Ctrl+Enter` / `Cmd+Enter` keyboard shortcut. Set editor options (minimap disabled, lineNumbers enabled, scrollBeyondLastLine: false). Coordinate Monaco theme with active theme.

- [ ] **Step 2: Commit**

```bash
git add React_UI/src/components/SqlEditor.tsx
git commit -m "feat(react-ui): implement Monaco SQL editor component with theme coordination"
```

---

### Task 6: Results Data Grid & CSV Export Component

**Files:**
- Create: `React_UI/src/components/ResultsTable.tsx`

**Interfaces:**
- Consumes: `ExecuteResponse`, `isLoading`, `error`
- Produces: Execution stats bar (row count, time ms, preview truncation badge), scrollable data grid with sticky headers and distinct NULL styling, client-side CSV download button.

- [ ] **Step 1: Implement `ResultsTable.tsx`**

Format table columns, render empty states, format NULL values, and generate client-side CSV blob download.

- [ ] **Step 2: Commit**

```bash
git add React_UI/src/components/ResultsTable.tsx
git commit -m "feat(react-ui): implement ResultsTable and client-side CSV exporter"
```

---

### Task 7: App Integration & Production Build Pipeline

**Files:**
- Create: `React_UI/src/App.tsx`
- Create: `React_UI/src/App.css`
- Modify: `main.py` (ensure root asset fallback if needed)
- Test: `tests/test_frontend.py`

- [ ] **Step 1: Implement `App.tsx` coordinating all components and state**

Wire active DB, active query, SQL editor state, query execution, and database switching preservation.

- [ ] **Step 2: Run production build in `React_UI`**

Run: `npm run build` inside `React_UI` and verify output in `../static/`.

- [ ] **Step 3: Run full pytest suite**

Run: `uv run pytest -v`
Expected: 24+ tests passing.

- [ ] **Step 4: Commit**

```bash
git add React_UI/ static/ tests/
git commit -m "feat(react-ui): build React SPA to static folder and verify FastAPI delivery"
```
