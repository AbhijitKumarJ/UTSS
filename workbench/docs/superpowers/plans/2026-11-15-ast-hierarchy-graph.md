# Phase 3.1: Interactive AST & Container Hierarchy Graph Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement an interactive AST & Container Hierarchy Graph visualizer for UTSS Workbench with containment trees, inheritance DAGs, universal concept clusters, and an interactive inspector with direct SQL runner jump.

**Architecture:** 
- Backend endpoints in `server/routes.py` and graph extraction routines in `server/db_manager.py` query SQLite containers and language facet tables to emit clean node-link graph JSON.
- Frontend React component suite (`AstGraphView.tsx`, `GraphCanvas.tsx`, `GraphInspector.tsx`, `GraphControls.tsx`) renders interactive SVG/Canvas graphs with pan/zoom, node selection, search filtering, and seamless SQL runner navigation.
- Mode integration in `TopNav.tsx` via a compact `🌳 Graph` / `🌳 AST Graph` tab, fully themed across all 4 palettes.

**Tech Stack:** FastAPI, SQLite3 (URI mode `ro`), React 18, TypeScript, SVG/HTML5 Canvas, CSS Variables.

---

## Global Constraints
- Read-only database access (`mode=ro&immutable=1`) must be preserved.
- Zero external runtime CDN dependencies; all code and layout calculations must run locally offline.
- Theme compatibility across all 4 themes (`utss-dark`, `vscode-dark`, `vscode-light`, `monokai`).
- Top navigation bar must remain compact without pushing off the `🎨 Theme` selector.

---

## Tasks

### Task 1: Backend Graph API Endpoints & Extraction Logic
- [x] Create `tests/test_graph_api.py` with failing tests for:
  - `GET /api/graph/containers?db_id=python_recommended`
  - `GET /api/graph/inheritance?db_id=cs_recommended`
  - `GET /api/graph/inheritance?db_id=python_recommended`
  - `GET /api/graph/concept-cluster?concept_key=collection.dynamic_array`
  - Error handling for invalid database IDs.
- [x] Implement `get_container_graph(db_id)` in `server/db_manager.py`:
  - Queries `containers` joined with `symbols` count.
  - Builds node list (`id`, `parent_id`, `name`, `qualified_name`, `kind`, `visibility`, `symbol_count`, `stratum`).
  - Builds edges (`source`, `target`, `type='contains'`).
- [x] Implement `get_inheritance_graph(db_id)` in `server/db_manager.py`:
  - Queries language-specific container facets (`py_container_facets`, `cs_container_facets`, `ts_container_facets`, `cpp_container_facets`, `go_container_facets`).
  - Extracts `base_classes_json`, `base_type_qname`, `implemented_interfaces_json`, `heritage_clauses_json`, `embedded_fields_json`.
  - Builds typed DAG edges (`extends`, `implements`, `embeds`).
- [x] Implement `get_concept_cluster(concept_key)` in `server/db_manager.py`:
  - Queries `dbs/utss_universal_bridge.db` for the concept and its type mappings across all 6 languages.
  - Returns star graph with central concept node and 6 target language implementation nodes.
- [x] Expose routes in `server/routes.py`:
  - `/api/graph/containers`
  - `/api/graph/inheritance`
  - `/api/graph/concept-cluster`
- [x] Run pytest to verify all tests pass.
- [x] Commit: `feat(api): implement AST containment, inheritance, and concept cluster graph endpoints`.

---

### Task 2: Graph Data Types & API Client in React
- [x] Add graph interfaces to `React_UI/src/types.ts`:
  - `GraphNode`: `id`, `name`, `qualified_name`, `kind`, `visibility`, `symbol_count`, `stratum`, `data?`
  - `GraphEdge`: `source`, `target`, `relation_kind`, `label?`
  - `GraphResponse`: `nodes: GraphNode[]`, `edges: GraphEdge[]`, `root_ids?: string[]`
  - `ConceptClusterResponse`: `concept: string`, `category: string`, `nodes: GraphNode[]`, `edges: GraphEdge[]`
- [x] Add API client functions to `React_UI/src/api.ts`:
  - `fetchContainerGraph(dbId: string): Promise<GraphResponse>`
  - `fetchInheritanceGraph(dbId: string): Promise<GraphResponse>`
  - `fetchConceptCluster(conceptKey: string): Promise<ConceptClusterResponse>`
- [x] Commit: `feat(ui): add graph data models and API client methods`.

---

### Task 3: Interactive Graph Canvas & Layout Engine
- [x] Create `React_UI/src/components/graph/GraphCanvas.tsx`:
  - Interactive SVG canvas with smooth pan (`drag`), zoom (`wheel`), and reset view button.
  - Multi-tiered hierarchical layout algorithm for tree & DAG visualization without external heavy libraries.
  - Node rendering with container kind badges, stratum color-coding, symbol density indicator, and hover/active states.
  - Edge rendering with curved cubic bezier paths and directional arrows with relation labels (`extends`, `implements`, `contains`).
  - Click node to trigger `onSelectNode(node)`.
- [x] Create `React_UI/src/components/graph/GraphControls.tsx`:
  - Mode selector buttons: `📁 Containment Tree` | `🧬 Type Inheritance DAG` | `🌐 Concept Cluster`.
  - Search filter input for quick node finding and focusing.
  - Zoom controls: `[+]`, `[-]`, `[Reset Fit]`.
  - Concept dropdown for Concept Cluster mode.
- [x] Commit: `feat(ui): implement interactive SVG graph canvas and layout controls`.

---

### Task 4: Node Inspector & Direct SQL Bridge
- [x] Create `React_UI/src/components/graph/GraphInspector.tsx`:
  - Displays selected container details: Qualified Name, Kind, Stratum, Visibility, Symbol Count.
  - If facet details exist (base classes, interfaces, traits, MRO), display them as clickable pills.
  - Action button: `⚡ Query Container in SQL Runner`:
    - Generates query: `SELECT * FROM symbols WHERE container_id = <id> ORDER BY name ASC;`
    - Calls `onJumpToSql(sqlQuery)` which navigates to the Tutoring & SQL Editor mode with query loaded and executed.
- [x] Commit: `feat(ui): implement GraphInspector with direct SQL runner jump bridge`.

---

### Task 5: TopNav Integration & Full UI Wiring
- [x] Create `React_UI/src/components/graph/AstGraphView.tsx`:
  - Combines `GraphControls`, `GraphCanvas`, and `GraphInspector`.
  - Manages graph state, loading indicators, active node selection, and jump-to-SQL callback.
- [x] Update `React_UI/src/components/TopNav.tsx`:
  - Add `🌳 Graph` mode tab between `📊 Comparative Analytics` and `🔄 Rosetta Playground`.
  - Ensure total navigation width stays compact and preserves `🎨 Theme` selector visibility.
- [x] Update `React_UI/src/App.tsx`:
  - Wire `activeSuite === "graph"` to render `<AstGraphView />`.
  - Handle `onJumpToSql`: sets active suite to `"tutoring"`, loads query into SQL editor, and executes it.
- [x] Add CSS styling in `React_UI/src/App.css` for graph canvas, nodes, edges, inspector, and controls across all 4 themes.
- [x] Build React frontend (`npm run build`).
- [x] Verify test suite passes (`pytest`).
- [x] Commit: `feat(ui): integrate AST Graph Visualizer into TopNav and workspace`.

---

### Task 6: Verification, End-to-End Tests & Documentation
- [x] Add e2e tests in `tests/test_graph_api.py` and `tests/test_frontend.py` verifying graph endpoints and asset bundling.
- [x] Update `docs/ARCHITECTURE_AND_ROADMAP.md` marking Phase 3.1 as delivered.
- [x] Verify 100% green test suite.
- [x] Final commit.
