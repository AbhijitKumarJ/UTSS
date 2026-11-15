import React from "react";
import { GraphNode } from "../../types";

interface GraphInspectorProps {
  node: GraphNode | null;
  onClose: () => void;
  onJumpToSql: (sql: string) => void;
  isFocused?: boolean;
  onToggleFocus?: (node: GraphNode) => void;
}

export const GraphInspector: React.FC<GraphInspectorProps> = ({
  node,
  onClose,
  onJumpToSql,
  isFocused = false,
  onToggleFocus
}) => {
  if (!node) {
    return (
      <aside className="graph-inspector empty">
        <div className="inspector-guide">
          <div className="guide-icon">🔍</div>
          <h4>Node Inspector</h4>
          <p>
            Click any node in the graph to inspect its container topology, enclosed symbols, and language facets.
          </p>
          <div className="guide-tips">
            <div className="guide-tip-item">
              <span>🎯 <strong>Fly-To Navigation:</strong> Click any node to smoothly center the camera on it.</span>
            </div>
            <div className="guide-tip-item">
              <span>🔍 <strong>Subtree Isolation:</strong> Click "Focus This Subtree" to isolate its 2-hop neighborhood.</span>
            </div>
            <div className="guide-tip-item">
              <span>⚡ <strong>SQL Bridge:</strong> Inspect a container to query its internal symbols with 1 click.</span>
            </div>
          </div>
        </div>
      </aside>
    );
  }

  const handleQuerySymbols = () => {
    let sql = "";
    if (node.container_id) {
      sql = `-- Symbols enclosed within container: ${node.qualified_name} (ID: ${node.container_id})\nSELECT symbol_id, name, symbol_kind, visibility\nFROM symbols\nWHERE container_id = ${node.container_id}\nORDER BY name ASC;`;
    } else {
      sql = `-- Symbols matching: ${node.qualified_name}\nSELECT s.symbol_id, s.name, s.symbol_kind, c.qualified_name as container\nFROM symbols s\nJOIN containers c ON s.container_id = c.container_id\nWHERE c.qualified_name LIKE '%${node.name}%'\nLIMIT 50;`;
    }
    onJumpToSql(sql);
  };

  return (
    <aside className="graph-inspector">
      <div className="inspector-header">
        <div className="inspector-title-row">
          <span className="badge badge-info">{node.kind.toUpperCase()}</span>
          {node.language && (
            <span className="badge badge-cat">{node.language.toUpperCase()}</span>
          )}
          <button className="btn-close-inspector" onClick={onClose} title="Close Inspector" type="button">
            ✕
          </button>
        </div>
        <h3 className="inspector-node-name">{node.name}</h3>
        <p className="inspector-node-qname" title={node.qualified_name}>
          <code>{node.qualified_name}</code>
        </p>
      </div>

      <div className="inspector-body">
        {/* Details Grid */}
        <div className="inspector-field-group">
          {node.container_id && (
            <div className="inspector-field">
              <span className="field-label">Container ID:</span>
              <span className="field-val"><code>{node.container_id}</code></span>
            </div>
          )}

          {typeof node.stratum === "number" && (
            <div className="inspector-field">
              <span className="field-label">Stratum:</span>
              <span className="field-val">
                {node.stratum === 0 && <span className="badge badge-warning">0: Ambient Built-in</span>}
                {node.stratum === 1 && <span className="badge badge-info">1: Standard Library</span>}
                {node.stratum === 2 && <span className="badge badge-cat">2: Third-Party</span>}
                {node.stratum === 3 && <span className="badge badge-level">3: Workspace Code</span>}
              </span>
            </div>
          )}

          {node.visibility && (
            <div className="inspector-field">
              <span className="field-label">Visibility:</span>
              <span className="field-val"><code>{node.visibility}</code></span>
            </div>
          )}

          {typeof node.symbol_count === "number" && (
            <div className="inspector-field">
              <span className="field-label">Enclosed Symbols:</span>
              <span className="field-val"><strong>{node.symbol_count}</strong> symbols</span>
            </div>
          )}

          {node.syntax_template && (
            <div className="inspector-field">
              <span className="field-label">Syntax Template:</span>
              <span className="field-val"><code>{node.syntax_template}</code></span>
            </div>
          )}

          {node.memory_model && (
            <div className="inspector-field">
              <span className="field-label">Memory Model:</span>
              <span className="field-val"><span className="badge badge-warning">{node.memory_model}</span></span>
            </div>
          )}

          {node.nullability_model && (
            <div className="inspector-field">
              <span className="field-label">Nullability:</span>
              <span className="field-val"><code>{node.nullability_model}</code></span>
            </div>
          )}

          {node.category && (
            <div className="inspector-field">
              <span className="field-label">Category:</span>
              <span className="field-val"><span className="badge badge-info">{node.category}</span></span>
            </div>
          )}

          {node.description && (
            <div className="inspector-field full-width">
              <span className="field-label">Description:</span>
              <p className="field-desc">{node.description}</p>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="inspector-action-section">
          {onToggleFocus && (
            <button
              type="button"
              className={`btn btn-sm ${isFocused ? "btn-warning" : "btn-outline"} btn-focus-subtree`}
              onClick={() => onToggleFocus(node)}
              title="Isolate this node and its direct hierarchy neighborhood"
            >
              {isFocused ? "✕ Reset Subtree Focus" : "🎯 Focus This Subtree"}
            </button>
          )}

          <button
            type="button"
            className="btn btn-primary btn-jump-sql"
            onClick={handleQuerySymbols}
            title="Open Interactive SQL Runner pre-populated with query for this container"
          >
            ⚡ Query in SQL Runner
          </button>
        </div>
      </div>
    </aside>
  );
};
