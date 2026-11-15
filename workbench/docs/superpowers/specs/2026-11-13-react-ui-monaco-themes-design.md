# React UI Client with Monaco Editor & Multi-Theme Workbench — Design Document

## 1. Intent & Purpose

To enable modular, reliable, and expressive frontend development for the UTSS Universal Language Analysis & Synthesis Platform, we are adding a client-only React application inside `React_UI/`.

The React application replaces the manual vanilla DOM manipulations with a structured component architecture, integrates the **Monaco Editor** (`@monaco-editor/react`) for full VS Code editing ergonomics (syntax highlighting, line numbers, shortcuts, command palette), supports multiple editor and workbench themes (including **VS Code Dark+**, **VS Code Light+**, **Monokai**, and **UTSS Dark**), and builds directly into `static/` so FastAPI serves it at `/` with zero backend changes.

---

## 2. Goals, Non-Goals, and Anti-Goals

### Goals
- **Monaco Editor Integration**: Real in-browser VS Code editor supporting SQL syntax highlighting, keyboard shortcuts (`Ctrl+Enter` / `Cmd+Enter`), line numbers, and theme coordination.
- **Multi-Theme Support**: Instant theme switching across the entire workbench and Monaco editor:
  - `utss-dark`: The current slate/indigo aesthetic.
  - `vscode-dark`: Classic VS Code Dark+ (`#1e1e1e` workspace, `#252526` sidebar, `#007acc` accents, `vs-dark` Monaco theme).
  - `vscode-light`: Clean VS Code Light+ (`#ffffff` editor, `#f3f3f3` surface, `vs` Monaco theme).
  - `monokai`: Classic hacker Monokai (`#272822` background, vibrant yellow/green accents).
- **Direct Build Pipeline to `static/`**: `npm run build` in `React_UI/` bundles the HTML, JS, CSS, and assets directly into `../static`, allowing `uv run main.py` or FastAPI to serve the new UI out of the box.
- **Full Feature Parity**:
  - Top bar: Database dropdown with live symbol stats, Mode switcher (Tutoring vs Comparative), and Theme switcher.
  - Left sidebar: Search filter, Level pills (All, Basic, Intermediate, Advanced), lesson cards with sequence numbers.
  - Tutor card: Collapsible/expandable, lesson rationale, guided experiments list.
  - Query runner: Monaco Editor with run, reset, and copy actions.
  - Results table: Sticky headers, formatted rows, NULL value styling, execution stats (row count, time ms, truncation badge), CSV download.
  - State preservation: Changing databases in the dropdown preserves current SQL in the editor.
- **Fast Developer Experience**: Vite dev server with proxy forwarding `/api/*` to `http://localhost:8000` for instant HMR during UI development.

### Non-Goals
- Server-side rendering (SSR) or Node.js runtime in production (this is strictly a client-side SPA build).
- Replacing the existing FastAPI backend (all `/api/*` contracts remain unchanged).

---

## 3. Directory Structure

```
React_UI/
├── package.json                          # React, Vite, TypeScript, @monaco-editor/react
├── vite.config.ts                        # Configured outDir: "../static", dev proxy to :8000
├── tsconfig.json
├── index.html                            # HTML template with theme init script
├── src/
│   ├── types.ts                          # DB, Query, Execution TypeScript interfaces
│   ├── api.ts                            # REST API client (/api/dbs, /api/queries, /api/execute, /api/export)
│   ├── context/
│   │   └── ThemeContext.tsx              # Theme provider & persistence (localStorage)
│   ├── components/
│   │   ├── TopNav.tsx                    # Header, DB switcher, mode tabs, theme dropdown
│   │   ├── Sidebar.tsx                   # Search, level filters, curriculum query cards
│   │   ├── TutorCard.tsx                 # Collapsible rationale and guided experiments
│   │   ├── SqlEditor.tsx                 # Monaco Editor with Ctrl+Enter runner & toolbar
│   │   └── ResultsTable.tsx              # Stats bar, data grid, NULL styling, CSV download
│   ├── styles/
│   │   └── themes.css                    # CSS variables for UTSS, VS Code Dark, VS Code Light, Monokai
│   ├── App.tsx                           # Main state coordination
│   ├── App.css                           # Layout and component styles
│   └── main.tsx                          # React entrypoint
```

---

## 4. Theme Specification

Themes are declared via CSS Custom Properties on `[data-theme="..."]`:

| Theme Token | UTSS Dark (`utss-dark`) | VS Code Dark (`vscode-dark`) | VS Code Light (`vscode-light`) | Monokai (`monokai`) |
| :--- | :--- | :--- | :--- | :--- |
| `--bg-main` | `#0b0f19` | `#181818` | `#f3f3f3` | `#1e1f1c` |
| `--bg-surface` | `#111827` | `#252526` | `#ffffff` | `#272822` |
| `--bg-card` | `#1f2937` | `#2d2d2d` | `#f8f8f8` | `#3e3d32` |
| `--border-color`| `#374151` | `#3c3c3c` | `#e5e5e5` | `#49483e` |
| `--text-primary`| `#f9fafb` | `#cccccc` | `#333333` | `#f8f8f2` |
| `--accent-primary`| `#3b82f6` | `#007acc` | `#007acc` | `#fd971f` |
| **Monaco Theme**| `vs-dark` | `vs-dark` | `vs` | `monokai` |

Theme state is synced to Monaco's theme API (`editor.setTheme`) and persisted in `localStorage`.

---

## 5. Build & Integration Pipeline

1. **Vite Output**:
   In `React_UI/vite.config.ts`:
   ```typescript
   export default defineConfig({
     plugins: [react()],
     base: "/",
     build: {
       outDir: "../static",
       emptyOutDir: false, // Preserves legacy static files if needed
     },
     server: {
       proxy: {
         "/api": "http://localhost:8000"
       }
     }
   });
   ```
2. **FastAPI Serving**:
   `main.py` serves `static/index.html` at `/` and static assets via `/static` or root paths.
   When the React app builds to `../static/index.html` and `../static/assets/`, visiting `http://localhost:8000/` immediately renders the React application.
