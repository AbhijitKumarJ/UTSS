# Graph UX Upgrade: Depth Limiting, Fly-To Navigation, Subtree Focus & Mini-Map

This plan establishes significant UX improvements for the **Containment Tree** and **Inheritance DAG** visualizers in the Universal Language Architecture platform. It addresses graph density, horizontal sprawl, and navigation friction when visualizing large codebases.

---

## User Stories & Architecture

### User Experience:
1. **Interactive Depth Limiter (`1 | 2 | 3 | All`)**:
   - Students and compiler engineers can limit tree/DAG depth to level 1, 2, 3, or All.
   - Defaulting to level 2 avoids visual cognitive overload upon initial database selection.
2. **Search Autocomplete & Smooth "Fly-To" Centering**:
   - Typing into the search bar suggests matching nodes (by name, qualified name, or kind).
   - Selecting a node smoothly animates the camera (`pan` and `zoom`) to center the target node in the viewport with a pulsating focus glow.
   - "Next" / "Prev" jump buttons cycle between search matches.
3. **Subtree Isolation ("Focus Mode")**:
   - In the inspector panel or via a node action, users can click **"🎯 Focus Subtree"**.
   - Filters the entire graph to only the selected node, its ancestors, and its descendants (2-hop neighborhood), making complex class hierarchies immediately understandable.
   - A breadcrumbs banner allows one-click exit back to the full graph.
4. **Entity Kind Filters (`[✓ Modules] [✓ Classes] [✓ Interfaces]`)**:
   - One-click filter pills allow removing classes, interfaces, or packages on the fly.
5. **Interactive Picture-in-Picture Mini-Map (Radar Navigation)**:
   - A sleek mini-map in the bottom-right corner renders a scaled overview of all active nodes.
   - Outlines the current camera viewport; clicking anywhere on the mini-map pans the camera directly to that location.
6. **Grid Sibling Wrapping Layout**:
   - Instead of laying out 100 siblings in a single horizontal ribbon, sibling groups wrap into compact multi-column grids (up to 4–6 columns) under their parent.

---

## Proposed Changes

### 1. `React_UI/src/components/graph/GraphControls.tsx`
- Add depth limit control: `depthLimit: number | "all"`, `onDepthLimitChange: (depth: number | "all") => void`.
- Add kind filter toggles: `activeKinds: Set<string>`, `onToggleKind: (kind: string) => void`.
- Add focused node breadcrumb indicator: `focusedNode: GraphNode | null`, `onClearFocus: () => void`.
- Add search match navigation: match count indicator (`Match X of Y`) with Prev (`▲`) and Next (`▼`) buttons.

### 2. `React_UI/src/components/graph/GraphCanvas.tsx`
- **Fly-To Animation Engine**:
  - `flyToNode(nodeId: string)`: computes target `pan` and `zoom` to center node in container bounds and smoothly updates state.
- **Mini-Map Canvas Component**:
  - Embeds a canvas/SVG mini-map overlay (160px × 110px) with viewport bounding box and click-to-pan handler.
- **Layout Grid Sibling Wrapping**:
  - Organizes sibling nodes under each parent into sub-grid clusters when sibling count > 5, reducing horizontal width by up to 75%.
- **Depth & Kind Filtering**:
  - Filters `nodes` and `edges` by `depthLimit`, `activeKinds`, and `focusedNodeId`.

### 3. `React_UI/src/components/graph/AstGraphView.tsx`
- Manages state for `depthLimit` (default `2`), `activeKinds`, `focusedNode`, and current search match index.
- Connects Inspector Panel with "Focus Subtree" action.

### 4. `React_UI/src/components/graph/GraphInspector.tsx`
- Adds a **"🎯 Focus Subtree"** button in the inspector header.
- Displays incoming/outgoing links with quick-jump links.

---

## Verification Plan
1. Compile React bundle: `npm --prefix React_UI run build`.
2. Run automated test suite: `.venv/bin/pytest -v`.
3. Verify interactive controls:
   - Changing depth limit to 1, 2, 3 updates visible node count cleanly.
   - Searching a class centers camera on it with fly-to animation.
   - Clicking "Focus Subtree" isolates its neighborhood; breadcrumb exits focus.
   - Mini-map reflects viewport position and teleports camera on click.
