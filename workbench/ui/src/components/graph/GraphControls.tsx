import React, { useState, useRef, useEffect } from "react";
import { BridgeConcept, GraphNode } from "../../types";

export type GraphViewMode = "containment" | "inheritance" | "concept";

interface GraphControlsProps {
  viewMode: GraphViewMode;
  onSelectViewMode: (mode: GraphViewMode) => void;
  concepts: BridgeConcept[];
  selectedConceptKey: string;
  onSelectConceptKey: (key: string) => void;
  searchQuery: string;
  onSearchChange: (query: string) => void;
  totalNodes: number;
  totalEdges: number;
  visibleNodesCount: number;
  activeDbId: string;
  onCollapseAll: () => void;
  onExpandAll: () => void;
  depthLimit: number | "all";
  onDepthLimitChange: (limit: number | "all") => void;
  availableKinds: string[];
  activeKinds: Set<string>;
  onToggleKind: (kind: string) => void;
  focusedNode: GraphNode | null;
  onClearFocus: () => void;
  searchMatches: GraphNode[];
  currentMatchIndex: number;
  onSelectMatch: (node: GraphNode) => void;
  onNextMatch: () => void;
  onPrevMatch: () => void;
}

export const GraphControls: React.FC<GraphControlsProps> = ({
  viewMode,
  onSelectViewMode,
  concepts,
  selectedConceptKey,
  onSelectConceptKey,
  searchQuery,
  onSearchChange,
  totalNodes,
  totalEdges,
  visibleNodesCount,
  activeDbId,
  onCollapseAll,
  onExpandAll,
  depthLimit,
  onDepthLimitChange,
  availableKinds,
  activeKinds,
  onToggleKind,
  focusedNode,
  onClearFocus,
  searchMatches,
  currentMatchIndex,
  onSelectMatch,
  onNextMatch,
  onPrevMatch
}) => {
  const [showSuggestions, setShowSuggestions] = useState(false);
  const searchContainerRef = useRef<HTMLDivElement>(null);

  // Close suggestions on outside click
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(e.target as Node)) {
        setShowSuggestions(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="graph-controls-bar">
      {/* Mode Switcher */}
      <div className="graph-mode-toggle">
        <button
          type="button"
          className={`btn-mode-tab ${viewMode === "containment" ? "active" : ""}`}
          onClick={() => onSelectViewMode("containment")}
          title="Lexical Scope & Containment Hierarchy Tree"
        >
          📁 Containment Tree
        </button>
        <button
          type="button"
          className={`btn-mode-tab ${viewMode === "inheritance" ? "active" : ""}`}
          onClick={() => onSelectViewMode("inheritance")}
          title="Type Inheritance & Interface Implementation DAG"
        >
          🧬 Inheritance DAG
        </button>
        <button
          type="button"
          className={`btn-mode-tab ${viewMode === "concept" ? "active" : ""}`}
          onClick={() => onSelectViewMode("concept")}
          title="Universal Bridge Canonical Concept Cluster"
        >
          🌐 Concept Cluster
        </button>
      </div>

      {/* Concept Selector Dropdown (When Concept Mode is active) */}
      {viewMode === "concept" && (
        <div className="graph-concept-picker">
          <label htmlFor="graph-concept-select" className="control-label">Concept:</label>
          <select
            id="graph-concept-select"
            className="db-dropdown"
            value={selectedConceptKey}
            onChange={(e) => onSelectConceptKey(e.target.value)}
          >
            {concepts.map(c => (
              <option key={c.concept_key} value={c.concept_key}>
                {c.category}: {c.concept_key}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Tree Depth Limiter (Containment & Inheritance modes) */}
      {viewMode !== "concept" && (
        <div className="graph-depth-control" title="Limit rendering depth to prevent visual overload">
          <span className="control-label">Depth:</span>
          <div className="depth-btn-group">
            {([1, 2, 3, "all"] as const).map(d => (
              <button
                key={d}
                type="button"
                className={`btn-depth-pill ${depthLimit === d ? "active" : ""}`}
                onClick={() => onDepthLimitChange(d)}
                title={d === "all" ? "Show all levels" : `Limit tree depth to Level ${d}`}
              >
                {d === "all" ? "All" : `L${d}`}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Search Input with Autocomplete & Fly-To Controls */}
      <div className="graph-search-container" ref={searchContainerRef}>
        <div className="graph-search-box">
          <input
            type="text"
            className="search-input"
            placeholder="Find & fly to node (e.g. List, dict)..."
            value={searchQuery}
            onChange={(e) => {
              onSearchChange(e.target.value);
              setShowSuggestions(true);
            }}
            onFocus={() => {
              if (searchQuery.trim()) setShowSuggestions(true);
            }}
          />
          {searchQuery && (
            <button
              type="button"
              className="search-clear-btn"
              onClick={() => {
                onSearchChange("");
                setShowSuggestions(false);
              }}
              title="Clear search"
            >
              ✕
            </button>
          )}

          {searchMatches.length > 0 && (
            <div className="search-match-nav">
              <span className="match-counter">
                {currentMatchIndex + 1}/{searchMatches.length}
              </span>
              <button
                type="button"
                className="btn-match-nav"
                onClick={onPrevMatch}
                title="Previous match"
              >
                ▲
              </button>
              <button
                type="button"
                className="btn-match-nav"
                onClick={onNextMatch}
                title="Next match"
              >
                ▼
              </button>
            </div>
          )}
        </div>

        {/* Autocomplete Dropdown List */}
        {showSuggestions && searchQuery.trim().length > 0 && searchMatches.length > 0 && (
          <div className="search-suggestions-dropdown">
            <div className="suggestions-header">
              <span>Matching Nodes ({searchMatches.length})</span>
              <span className="hint">Click to center view</span>
            </div>
            <div className="suggestions-list">
              {searchMatches.slice(0, 10).map((m, idx) => (
                <div
                  key={m.id}
                  className={`suggestion-item ${idx === currentMatchIndex ? "active" : ""}`}
                  onClick={() => {
                    onSelectMatch(m);
                    setShowSuggestions(false);
                  }}
                >
                  <span className="sugg-kind-badge">{m.kind}</span>
                  <span className="sugg-name">{m.name}</span>
                  <span className="sugg-qname" title={m.qualified_name}>
                    {m.qualified_name.length > 30 ? `…${m.qualified_name.slice(-28)}` : m.qualified_name}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Subtree Focus Banner (when focusing a neighborhood) */}
      {focusedNode && (
        <div className="graph-focus-banner" title="Isolating 2-hop neighborhood of this node">
          <span className="focus-icon">🎯</span>
          <span className="focus-text">
            Focus: <strong>{focusedNode.name}</strong>
          </span>
          <button
            type="button"
            className="btn-exit-focus"
            onClick={onClearFocus}
            title="Exit focus mode and show all nodes"
          >
            ✕ Reset
          </button>
        </div>
      )}

      {/* Entity Kind Filters */}
      {viewMode !== "concept" && availableKinds && availableKinds.length > 0 && (
        <div className="graph-kind-filters" title="Toggle entity kinds">
          {availableKinds.slice(0, 4).map(k => (
            <button
              key={k}
              type="button"
              className={`kind-filter-chip ${activeKinds.has(k) ? "active" : "inactive"}`}
              onClick={() => onToggleKind(k)}
              title={`Toggle visibility of ${k} nodes`}
            >
              {activeKinds.has(k) ? `✓ ${k}` : k}
            </button>
          ))}
        </div>
      )}

      {/* Bulk Expand / Collapse Buttons */}
      {viewMode !== "concept" && (
        <div className="graph-tree-actions">
          <button
            type="button"
            className="btn btn-secondary btn-tree-toggle"
            onClick={onCollapseAll}
            title="Collapse all child nodes"
          >
            [−] Collapse
          </button>
          <button
            type="button"
            className="btn btn-secondary btn-tree-toggle"
            onClick={onExpandAll}
            title="Expand all child nodes"
          >
            [+] Expand
          </button>
        </div>
      )}

      {/* Stats Badges */}
      <div className="graph-stats-group">
        <span className="badge badge-info">
          {visibleNodesCount !== totalNodes ? `${visibleNodesCount} / ${totalNodes} NODES` : `${totalNodes} NODES`}
        </span>
        <span className="badge badge-cat">
          {totalEdges} EDGES
        </span>
        {viewMode !== "concept" && (
          <span className="graph-db-tag" title={`Active Target: ${activeDbId}`}>
            Target: <code>{activeDbId}</code>
          </span>
        )}
      </div>
    </div>
  );
};
