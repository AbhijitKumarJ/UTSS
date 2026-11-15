import React, { useState, useEffect, useMemo } from "react";
import { AstFlowNode, AstFlowResponse } from "../../types";
import { fetchAstFlow } from "../../api";

interface AstFlowVisualizerProps {
  pythonCode: string;
}

const NODE_TYPE_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  Module: { bg: "rgba(148, 163, 184, 0.15)", text: "#cbd5e1", border: "rgba(148, 163, 184, 0.4)" },
  ClassDef: { bg: "rgba(168, 85, 247, 0.15)", text: "#c084fc", border: "rgba(168, 85, 247, 0.4)" },
  FunctionDef: { bg: "rgba(59, 130, 246, 0.15)", text: "#60a5fa", border: "rgba(59, 130, 246, 0.4)" },
  AsyncFunctionDef: { bg: "rgba(59, 130, 246, 0.15)", text: "#60a5fa", border: "rgba(59, 130, 246, 0.4)" },
  Assign: { bg: "rgba(6, 182, 212, 0.15)", text: "#22d3ee", border: "rgba(6, 182, 212, 0.4)" },
  AnnAssign: { bg: "rgba(6, 182, 212, 0.15)", text: "#22d3ee", border: "rgba(6, 182, 212, 0.4)" },
  AugAssign: { bg: "rgba(6, 182, 212, 0.15)", text: "#22d3ee", border: "rgba(6, 182, 212, 0.4)" },
  For: { bg: "rgba(234, 179, 8, 0.15)", text: "#facc15", border: "rgba(234, 179, 8, 0.4)" },
  While: { bg: "rgba(234, 179, 8, 0.15)", text: "#facc15", border: "rgba(234, 179, 8, 0.4)" },
  If: { bg: "rgba(249, 115, 22, 0.15)", text: "#fb923c", border: "rgba(249, 115, 22, 0.4)" },
  Try: { bg: "rgba(239, 68, 68, 0.15)", text: "#f87171", border: "rgba(239, 68, 68, 0.4)" },
  ExceptHandler: { bg: "rgba(239, 68, 68, 0.15)", text: "#f87171", border: "rgba(239, 68, 68, 0.4)" },
  Call: { bg: "rgba(16, 185, 129, 0.15)", text: "#34d399", border: "rgba(16, 185, 129, 0.4)" },
  Return: { bg: "rgba(236, 72, 153, 0.15)", text: "#f472b6", border: "rgba(236, 72, 153, 0.4)" },
  Attribute: { bg: "rgba(139, 92, 246, 0.15)", text: "#a78bfa", border: "rgba(139, 92, 246, 0.4)" }
};

interface TreeNodeItemProps {
  node: AstFlowNode;
  selectedId: string | null;
  onSelect: (node: AstFlowNode) => void;
  filterText: string;
  expandedMap: Record<string, boolean>;
  onToggleExpand: (id: string) => void;
  depth?: number;
}

const TreeNodeItem: React.FC<TreeNodeItemProps> = ({
  node,
  selectedId,
  onSelect,
  filterText,
  expandedMap,
  onToggleExpand,
  depth = 0
}) => {
  const isExpanded = expandedMap[node.id] !== false;
  const isSelected = selectedId === node.id;
  const hasChildren = node.children && node.children.length > 0;

  const matchesFilter = useMemo(() => {
    if (!filterText) return true;
    const term = filterText.toLowerCase();
    const selfMatch = node.node_type.toLowerCase().includes(term) ||
                      node.label.toLowerCase().includes(term) ||
                      (node.ir_concept && node.ir_concept.toLowerCase().includes(term));
    if (selfMatch) return true;
    const checkChild = (n: AstFlowNode): boolean => {
      if (n.node_type.toLowerCase().includes(term) || n.label.toLowerCase().includes(term)) return true;
      return (n.children || []).some(checkChild);
    };
    return (node.children || []).some(checkChild);
  }, [node, filterText]);

  if (!matchesFilter) return null;

  const colorStyle = NODE_TYPE_COLORS[node.node_type] || {
    bg: "rgba(100, 116, 139, 0.15)",
    text: "#94a3b8",
    border: "rgba(100, 116, 139, 0.3)"
  };

  return (
    <div className="ast-tree-node-wrapper" style={{ marginLeft: depth > 0 ? "1.25rem" : "0" }}>
      <div
        className={`ast-tree-node ${isSelected ? "selected" : ""}`}
        onClick={() => onSelect(node)}
      >
        {hasChildren ? (
          <button
            type="button"
            className="ast-expand-btn"
            onClick={(e) => {
              e.stopPropagation();
              onToggleExpand(node.id);
            }}
          >
            {isExpanded ? "▼" : "▶"}
          </button>
        ) : (
          <span className="ast-leaf-spacer">•</span>
        )}

        <span
          className="ast-node-type-pill"
          style={{
            backgroundColor: colorStyle.bg,
            color: colorStyle.text,
            borderColor: colorStyle.border
          }}
        >
          {node.node_type}
        </span>

        <span className="ast-node-label" title={node.label}>
          {node.label}
        </span>

        {node.ir_concept && (
          <span className="ast-ir-concept-pill" title={`Universal IR: ${node.ir_concept}`}>
            ⚡ {node.ir_concept.split(".").pop()}
          </span>
        )}

        {node.line_start !== null && node.line_start !== undefined && (
          <span className="ast-line-badge">
            L{node.line_start}{node.line_end && node.line_end !== node.line_start ? `-${node.line_end}` : ""}
          </span>
        )}
      </div>

      {hasChildren && isExpanded && (
        <div className="ast-tree-children">
          {node.children.map(child => (
            <TreeNodeItem
              key={child.id}
              node={child}
              selectedId={selectedId}
              onSelect={onSelect}
              filterText={filterText}
              expandedMap={expandedMap}
              onToggleExpand={onToggleExpand}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
};

export const AstFlowVisualizer: React.FC<AstFlowVisualizerProps> = ({ pythonCode }) => {
  const [data, setData] = useState<AstFlowResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<AstFlowNode | null>(null);
  const [filterText, setFilterText] = useState("");
  const [expandedMap, setExpandedMap] = useState<Record<string, boolean>>({});
  const [selectedLang, setSelectedLang] = useState<"csharp" | "rust" | "typescript" | "cpp" | "go">("csharp");
  const [copySuccess, setCopySuccess] = useState(false);

  const loadAstFlow = async (code: string) => {
    if (!code || !code.trim()) {
      setData(null);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetchAstFlow(code);
      setData(res);
      if (res.root) {
        setSelectedNode(res.root);
        // Expand top 2 levels by default
        const initExpanded: Record<string, boolean> = { [res.root.id]: true };
        (res.root.children || []).forEach(c => {
          initExpanded[c.id] = true;
        });
        setExpandedMap(initExpanded);
      }
    } catch (err: any) {
      setError(err.message || "Failed to generate AST flow graph");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAstFlow(pythonCode);
  }, [pythonCode]);

  const handleToggleExpand = (id: string) => {
    setExpandedMap(prev => ({ ...prev, [id]: prev[id] === false ? true : false }));
  };

  const handleExpandAll = () => {
    if (!data?.root) return;
    const allExpanded: Record<string, boolean> = {};
    const recurse = (n: AstFlowNode) => {
      allExpanded[n.id] = true;
      (n.children || []).forEach(recurse);
    };
    recurse(data.root);
    setExpandedMap(allExpanded);
  };

  const handleCollapseAll = () => {
    if (!data?.root) return;
    setExpandedMap({ [data.root.id]: false });
  };

  const handleCopySnippet = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopySuccess(true);
    setTimeout(() => setCopySuccess(false), 1800);
  };

  return (
    <div className="ast-flow-container">
      {/* Header bar */}
      <div className="ast-flow-header">
        <div className="ast-header-left">
          <h3 className="ast-header-title">🌳 Abstract Syntax Tree & Transpilation Lowering Flow</h3>
          {data && (
            <div className="ast-meta-tags">
              <span className="ast-meta-pill">{data.node_count} AST Nodes</span>
              <span className="ast-meta-pill">Max Depth: {data.max_depth}</span>
              <span className="ast-meta-pill">{data.concepts_detected.length} Concepts Identified</span>
            </div>
          )}
        </div>

        <div className="ast-header-controls">
          <input
            type="text"
            className="ast-search-input"
            placeholder="Filter AST nodes (e.g. ClassDef, For)..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
          />
          <button type="button" className="btn btn-sm btn-outline" onClick={handleExpandAll}>
            Expand All
          </button>
          <button type="button" className="btn btn-sm btn-outline" onClick={handleCollapseAll}>
            Collapse All
          </button>
          <button
            type="button"
            className="btn btn-sm btn-outline"
            onClick={() => loadAstFlow(pythonCode)}
            title="Refresh AST Flow from active source"
          >
            🔄 Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="ast-error-banner">
          <span className="error-icon">⚠️</span>
          <div className="error-content">
            <strong>Unable to parse AST:</strong> {error}
          </div>
        </div>
      )}

      {loading && (
        <div className="ast-loading-state">
          <div className="spinner"></div>
          <span>Parsing Abstract Syntax Tree and synthesizing target lowerings...</span>
        </div>
      )}

      {!loading && data?.root && (
        <div className="ast-flow-layout">
          {/* Left: Tree Viewer */}
          <div className="ast-tree-panel">
            <TreeNodeItem
              node={data.root}
              selectedId={selectedNode?.id || null}
              onSelect={setSelectedNode}
              filterText={filterText}
              expandedMap={expandedMap}
              onToggleExpand={handleToggleExpand}
            />
          </div>

          {/* Right: Node Lowering Inspector */}
          <div className="ast-inspector-panel">
            {selectedNode ? (
              <div className="node-inspector-content">
                <div className="inspector-header">
                  <div className="inspector-title-area">
                    <span
                      className="inspector-type-pill"
                      style={{
                        backgroundColor: NODE_TYPE_COLORS[selectedNode.node_type]?.bg || "rgba(100, 116, 139, 0.2)",
                        color: NODE_TYPE_COLORS[selectedNode.node_type]?.text || "#94a3b8"
                      }}
                    >
                      {selectedNode.node_type}
                    </span>
                    <h4 className="inspector-node-label">{selectedNode.label}</h4>
                  </div>
                  {selectedNode.line_start !== null && selectedNode.line_start !== undefined && (
                    <span className="inspector-coords">
                      Lines {selectedNode.line_start} - {selectedNode.line_end || selectedNode.line_start}
                    </span>
                  )}
                </div>

                {/* IR Concept Card */}
                {selectedNode.ir_concept && (
                  <div className="inspector-concept-box">
                    <span className="concept-icon">⚡</span>
                    <div className="concept-info">
                      <span className="concept-key">{selectedNode.ir_concept}</span>
                      <p className="concept-desc">
                        Matches universal transpilation concept in <code>utss_universal_bridge.db</code>.
                      </p>
                    </div>
                  </div>
                )}

                {/* Source Code Extract */}
                {selectedNode.source_snippet && (
                  <div className="inspector-section">
                    <div className="inspector-section-label">Source Extract (Python AST Node):</div>
                    <pre className="source-snippet-box">
                      <code>{selectedNode.source_snippet}</code>
                    </pre>
                  </div>
                )}

                {/* Multi-Target Lowering Previews */}
                <div className="inspector-section">
                  <div className="inspector-lowering-header">
                    <div className="inspector-section-label">Per-Node Target Lowering Synthesis:</div>
                    <div className="target-lang-tabs">
                      {(["csharp", "rust", "typescript", "cpp", "go"] as const).map(lang => (
                        <button
                          key={lang}
                          type="button"
                          className={`target-lang-tab ${selectedLang === lang ? "active" : ""}`}
                          onClick={() => setSelectedLang(lang)}
                        >
                          {lang.toUpperCase()}
                        </button>
                      ))}
                    </div>
                  </div>

                  <div className="lowering-preview-box">
                    {selectedNode.lowering_previews && selectedNode.lowering_previews[selectedLang] ? (
                      <div className="code-with-copy">
                        <button
                          type="button"
                          className="copy-btn"
                          onClick={() => handleCopySnippet(selectedNode.lowering_previews[selectedLang])}
                        >
                          {copySuccess ? "✓ Copied" : "📋 Copy"}
                        </button>
                        <pre>
                          <code>{selectedNode.lowering_previews[selectedLang]}</code>
                        </pre>
                      </div>
                    ) : (
                      <div className="no-lowering-note">
                        <em>This node is lowered as part of its parent container ({selectedNode.node_type}). Select the enclosing container to view synthesized output.</em>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : (
              <div className="inspector-placeholder">
                <div className="placeholder-icon">🌳</div>
                <h4>Select an AST Node</h4>
                <p>Click any node in the AST hierarchy to inspect its source span and multi-language lowerings.</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
