import React, { useState, useEffect, useCallback, useMemo } from "react";
import { GraphNode, GraphResponse, BridgeConcept } from "../../types";
import {
  fetchContainerGraph,
  fetchInheritanceGraph,
  fetchConceptCluster,
  fetchBridgeConcepts
} from "../../api";
import { GraphControls, GraphViewMode } from "./GraphControls";
import { GraphCanvas } from "./GraphCanvas";
import { GraphInspector } from "./GraphInspector";

interface AstGraphViewProps {
  activeDbId: string;
  onJumpToSql: (sql: string) => void;
}

export const AstGraphView: React.FC<AstGraphViewProps> = ({
  activeDbId,
  onJumpToSql
}) => {
  const [viewMode, setViewMode] = useState<GraphViewMode>("containment");
  const [concepts, setConcepts] = useState<BridgeConcept[]>([]);
  const [selectedConceptKey, setSelectedConceptKey] = useState<string>("collection.dynamic_array");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);

  // Depth Limiter state: default to 2 to eliminate the initial 800+ node cognitive explosion!
  const [depthLimit, setDepthLimit] = useState<number | "all">(2);

  // Subtree focus state
  const [focusedNode, setFocusedNode] = useState<GraphNode | null>(null);

  // Active entity kinds filter
  const [activeKinds, setActiveKinds] = useState<Set<string>>(new Set());

  // Fly-to target ID for camera transitions
  const [flyToTargetId, setFlyToTargetId] = useState<string | null>(null);

  // Search match navigation index
  const [currentMatchIndex, setCurrentMatchIndex] = useState<number>(0);

  const [graphData, setGraphData] = useState<GraphResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Set of collapsed node IDs whose child branches/outgoing links are hidden
  const [collapsedNodeIds, setCollapsedNodeIds] = useState<Set<string>>(new Set());

  // Reset collapsed nodes, focused node, and search when activeDbId or viewMode changes
  useEffect(() => {
    setCollapsedNodeIds(new Set());
    setFocusedNode(null);
    setSearchQuery("");
  }, [activeDbId, viewMode, selectedConceptKey]);

  // Load Bridge concepts on mount for Concept Cluster mode
  useEffect(() => {
    fetchBridgeConcepts()
      .then(cList => {
        setConcepts(cList);
        if (cList.length > 0 && !selectedConceptKey) {
          setSelectedConceptKey(cList[0].concept_key);
        }
      })
      .catch(err => console.error("Failed to load bridge concepts:", err));
  }, []);

  // Load graph data based on mode and activeDbId
  const loadGraph = useCallback(async () => {
    if (!activeDbId && viewMode !== "concept") return;
    setIsLoading(true);
    setError(null);
    setSelectedNode(null);
    setFocusedNode(null);

    try {
      let data: GraphResponse;
      if (viewMode === "containment") {
        data = await fetchContainerGraph(activeDbId);
      } else if (viewMode === "inheritance") {
        data = await fetchInheritanceGraph(activeDbId);
      } else {
        data = await fetchConceptCluster(selectedConceptKey || "collection.dynamic_array");
      }
      setGraphData(data);

      // Initialize active kinds with all available kinds
      const kinds = new Set<string>();
      (data.nodes || []).forEach(n => {
        if (n.kind) kinds.add(n.kind);
      });
      setActiveKinds(kinds);
    } catch (err: any) {
      setError(err.message || "Failed to load graph data");
      setGraphData(null);
    } finally {
      setIsLoading(false);
    }
  }, [activeDbId, viewMode, selectedConceptKey]);

  useEffect(() => {
    loadGraph();
  }, [loadGraph]);

  // Available entity kinds across current dataset
  const availableKinds = useMemo(() => {
    if (!graphData?.nodes) return [];
    const kinds = new Set<string>();
    graphData.nodes.forEach(n => {
      if (n.kind) kinds.add(n.kind);
    });
    return Array.from(kinds);
  }, [graphData]);

  const handleToggleKind = (kind: string) => {
    setActiveKinds(prev => {
      const next = new Set(prev);
      if (next.has(kind)) {
        if (next.size > 1) next.delete(kind);
      } else {
        next.add(kind);
      }
      return next;
    });
  };

  // Search matching nodes
  const searchMatches = useMemo(() => {
    if (!graphData?.nodes || !searchQuery.trim()) return [];
    const q = searchQuery.toLowerCase().trim();
    return graphData.nodes.filter(n =>
      n.name.toLowerCase().includes(q) ||
      n.qualified_name.toLowerCase().includes(q) ||
      (n.kind && n.kind.toLowerCase().includes(q))
    );
  }, [graphData, searchQuery]);

  // Reset match index when matches change
  useEffect(() => {
    setCurrentMatchIndex(0);
  }, [searchMatches.length]);

  const handleSelectMatch = (node: GraphNode) => {
    setSelectedNode(node);
    setFlyToTargetId(node.id);
  };

  const handleNextMatch = () => {
    if (searchMatches.length === 0) return;
    const nextIdx = (currentMatchIndex + 1) % searchMatches.length;
    setCurrentMatchIndex(nextIdx);
    handleSelectMatch(searchMatches[nextIdx]);
  };

  const handlePrevMatch = () => {
    if (searchMatches.length === 0) return;
    const prevIdx = (currentMatchIndex - 1 + searchMatches.length) % searchMatches.length;
    setCurrentMatchIndex(prevIdx);
    handleSelectMatch(searchMatches[prevIdx]);
  };

  const handleToggleCollapse = (nodeId: string) => {
    setCollapsedNodeIds(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  const handleCollapseAll = () => {
    if (!graphData) return;
    const parents = new Set<string>();
    graphData.edges.forEach(e => parents.add(e.source));
    setCollapsedNodeIds(parents);
  };

  const handleExpandAll = () => {
    setCollapsedNodeIds(new Set());
    setDepthLimit("all");
  };

  const handleToggleFocus = (node: GraphNode) => {
    if (focusedNode?.id === node.id) {
      setFocusedNode(null);
    } else {
      setFocusedNode(node);
      setSelectedNode(node);
      setFlyToTargetId(node.id);
    }
  };

  return (
    <div className="ast-graph-view">
      {/* Top Controls Bar */}
      <GraphControls
        viewMode={viewMode}
        onSelectViewMode={setViewMode}
        concepts={concepts}
        selectedConceptKey={selectedConceptKey}
        onSelectConceptKey={setSelectedConceptKey}
        searchQuery={searchQuery}
        onSearchChange={setSearchQuery}
        totalNodes={graphData?.total_nodes || 0}
        totalEdges={graphData?.total_edges || 0}
        visibleNodesCount={graphData?.nodes?.length || 0}
        activeDbId={activeDbId}
        onCollapseAll={handleCollapseAll}
        onExpandAll={handleExpandAll}
        depthLimit={depthLimit}
        onDepthLimitChange={setDepthLimit}
        availableKinds={availableKinds}
        activeKinds={activeKinds}
        onToggleKind={handleToggleKind}
        focusedNode={focusedNode}
        onClearFocus={() => setFocusedNode(null)}
        searchMatches={searchMatches}
        currentMatchIndex={currentMatchIndex}
        onSelectMatch={handleSelectMatch}
        onNextMatch={handleNextMatch}
        onPrevMatch={handlePrevMatch}
      />

      {/* Main Canvas & Inspector Area */}
      <div className="graph-content-area">
        {isLoading ? (
          <div className="graph-loading-overlay">
            <div className="spinner"></div>
            <p>Constructing {viewMode} graph topology...</p>
          </div>
        ) : error ? (
          <div className="graph-error-box">
            <h4>Graph Generation Notice</h4>
            <p>{error}</p>
            {viewMode === "inheritance" && (
              <p className="error-hint">
                Note: Inheritance DAGs require language facet tables. If this database has no multi-class hierarchy, try <code>python_recommended</code> or <code>cs_recommended</code>.
              </p>
            )}
            <button className="btn btn-secondary" onClick={loadGraph} type="button">
              🔄 Retry
            </button>
          </div>
        ) : (
          <GraphCanvas
            nodes={graphData?.nodes || []}
            edges={graphData?.edges || []}
            selectedNodeId={selectedNode?.id || null}
            onSelectNode={setSelectedNode}
            searchQuery={searchQuery}
            isRadialLayout={viewMode === "concept"}
            collapsedNodeIds={collapsedNodeIds}
            onToggleCollapse={handleToggleCollapse}
            depthLimit={depthLimit}
            activeKinds={activeKinds}
            focusedNodeId={focusedNode?.id || null}
            flyToTargetId={flyToTargetId}
          />
        )}

        {/* Inspector Sidebar */}
        <GraphInspector
          node={selectedNode}
          onClose={() => setSelectedNode(null)}
          onJumpToSql={onJumpToSql}
          isFocused={focusedNode?.id === selectedNode?.id}
          onToggleFocus={handleToggleFocus}
        />
      </div>
    </div>
  );
};
