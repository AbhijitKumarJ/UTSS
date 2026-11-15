import React, { useState, useRef, useEffect, useMemo, useCallback } from "react";
import { GraphNode, GraphEdge } from "../../types";

interface GraphCanvasProps {
  nodes: GraphNode[];
  edges: GraphEdge[];
  selectedNodeId: string | null;
  onSelectNode: (node: GraphNode) => void;
  searchQuery: string;
  isRadialLayout?: boolean;
  collapsedNodeIds: Set<string>;
  onToggleCollapse: (nodeId: string) => void;
  depthLimit?: number | "all";
  activeKinds?: Set<string>;
  focusedNodeId?: string | null;
  flyToTargetId?: string | null;
}

interface PositionedNode extends GraphNode {
  x: number;
  y: number;
  width: number;
  height: number;
}

const NODE_WIDTH = 200;
const NODE_HEIGHT = 68;
const X_GAP = 240;
const Y_GAP = 130;
const MAX_LAYER_COLS = 5;

export const GraphCanvas: React.FC<GraphCanvasProps> = ({
  nodes,
  edges,
  selectedNodeId,
  onSelectNode,
  searchQuery,
  isRadialLayout = false,
  collapsedNodeIds,
  onToggleCollapse,
  depthLimit = "all",
  activeKinds,
  focusedNodeId = null,
  flyToTargetId = null
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState<number>(0.85);
  const [pan, setPan] = useState<{ x: number; y: number }>({ x: 100, y: 100 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [focusedPulseId, setFocusedPulseId] = useState<string | null>(null);
  const [showMiniMap, setShowMiniMap] = useState<boolean>(true);

  // Adjacency maps
  const childrenMap = useMemo(() => {
    const map = new Map<string, string[]>();
    nodes.forEach(n => map.set(n.id, []));
    edges.forEach(e => {
      if (map.has(e.source)) {
        map.get(e.source)!.push(e.target);
      }
    });
    return map;
  }, [nodes, edges]);

  const parentMap = useMemo(() => {
    const map = new Map<string, string[]>();
    nodes.forEach(n => map.set(n.id, []));
    edges.forEach(e => {
      if (map.has(e.target)) {
        map.get(e.target)!.push(e.source);
      }
    });
    return map;
  }, [nodes, edges]);

  // Compute 2-hop neighborhood if focusedNodeId is present
  const neighborhoodSet = useMemo<Set<string> | null>(() => {
    if (!focusedNodeId) return null;
    const set = new Set<string>([focusedNodeId]);

    // Ancestors (all the way to roots)
    const ancestorQueue = [focusedNodeId];
    while (ancestorQueue.length > 0) {
      const cur = ancestorQueue.shift()!;
      for (const p of parentMap.get(cur) || []) {
        if (!set.has(p)) {
          set.add(p);
          ancestorQueue.push(p);
        }
      }
    }

    // Descendants (up to 2 hops)
    const descQueue: Array<{ id: string; hop: number }> = [{ id: focusedNodeId, hop: 0 }];
    while (descQueue.length > 0) {
      const { id, hop } = descQueue.shift()!;
      if (hop < 2) {
        for (const ch of childrenMap.get(id) || []) {
          set.add(ch);
          descQueue.push({ id: ch, hop: hop + 1 });
        }
      }
    }
    return set;
  }, [focusedNodeId, parentMap, childrenMap]);

  // Compute node depth from roots
  const depthMap = useMemo<Map<string, number>>(() => {
    const map = new Map<string, number>();
    const roots = nodes.filter(n => (parentMap.get(n.id) || []).length === 0);
    const effectiveRoots = roots.length > 0 ? roots : (nodes.length > 0 ? [nodes[0]] : []);

    const queue: Array<{ id: string; d: number }> = effectiveRoots.map(r => ({ id: r.id, d: 0 }));
    const visited = new Set<string>();

    while (queue.length > 0) {
      const { id, d } = queue.shift()!;
      if (visited.has(id)) continue;
      visited.add(id);
      map.set(id, d);

      for (const ch of childrenMap.get(id) || []) {
        queue.push({ id: ch, d: d + 1 });
      }
    }

    nodes.forEach(n => {
      if (!map.has(n.id)) map.set(n.id, 0);
    });
    return map;
  }, [nodes, parentMap, childrenMap]);

  // Compute visible nodes and edges based on:
  // 1. Focus neighborhood
  // 2. Entity Kind filtering
  // 3. Depth Limiter
  // 4. Manual Collapsed Branches
  const { visibleNodes, visibleEdges } = useMemo(() => {
    // 1. Neighborhood filter
    let candidateNodes = nodes;
    if (neighborhoodSet) {
      candidateNodes = candidateNodes.filter(n => neighborhoodSet.has(n.id));
    }

    // 2. Kind filter
    if (activeKinds && activeKinds.size > 0 && !isRadialLayout) {
      candidateNodes = candidateNodes.filter(n => n.is_root || activeKinds.has(n.kind));
    }

    // 3. Depth Limiter
    if (depthLimit !== "all" && !isRadialLayout) {
      const maxAllowed = typeof depthLimit === "number" ? depthLimit : 999;
      candidateNodes = candidateNodes.filter(n => (depthMap.get(n.id) || 0) <= maxAllowed);
    }

    const candidateIds = new Set(candidateNodes.map(n => n.id));

    // 4. Collapse filtering
    if (collapsedNodeIds.size === 0 || isRadialLayout) {
      const filteredEdges = edges.filter(
        e => candidateIds.has(e.source) && candidateIds.has(e.target)
      );
      return { visibleNodes: candidateNodes, visibleEdges: filteredEdges };
    }

    const inDegreeMap = new Map<string, string[]>();
    candidateNodes.forEach(n => inDegreeMap.set(n.id, []));
    edges.forEach(e => {
      if (candidateIds.has(e.source) && candidateIds.has(e.target) && inDegreeMap.has(e.target)) {
        inDegreeMap.get(e.target)!.push(e.source);
      }
    });

    const roots = candidateNodes.filter(n => (inDegreeMap.get(n.id) || []).length === 0);
    const effectiveRoots = roots.length > 0 ? roots : (candidateNodes.length > 0 ? [candidateNodes[0]] : []);

    const visibleNodeIds = new Set<string>();
    const queue: string[] = [];

    for (const root of effectiveRoots) {
      visibleNodeIds.add(root.id);
      if (!collapsedNodeIds.has(root.id)) {
        queue.push(root.id);
      }
    }

    candidateNodes.forEach(n => {
      const inCount = (inDegreeMap.get(n.id) || []).length;
      const outCount = (childrenMap.get(n.id) || []).filter(c => candidateIds.has(c)).length;
      if (inCount === 0 && outCount === 0) {
        visibleNodeIds.add(n.id);
      }
    });

    while (queue.length > 0) {
      const currentId = queue.shift()!;
      const children = (childrenMap.get(currentId) || []).filter(c => candidateIds.has(c));
      for (const childId of children) {
        if (!visibleNodeIds.has(childId)) {
          visibleNodeIds.add(childId);
          if (!collapsedNodeIds.has(childId)) {
            queue.push(childId);
          }
        }
      }
    }

    const filteredNodes = candidateNodes.filter(n => visibleNodeIds.has(n.id));
    const filteredEdges = edges.filter(
      e => visibleNodeIds.has(e.source) && visibleNodeIds.has(e.target) && !collapsedNodeIds.has(e.source)
    );

    return { visibleNodes: filteredNodes, visibleEdges: filteredEdges };
  }, [nodes, edges, neighborhoodSet, activeKinds, depthLimit, collapsedNodeIds, isRadialLayout, depthMap, childrenMap]);

  // Compute Layout (Radial for Concept Cluster, Layered with Grid-Wrapping for Trees/DAGs)
  const positionedNodes = useMemo<PositionedNode[]>(() => {
    if (!visibleNodes || visibleNodes.length === 0) return [];

    if (isRadialLayout) {
      const centerNode = visibleNodes.find(n => n.is_root) || visibleNodes[0];
      const satellites = visibleNodes.filter(n => n.id !== centerNode.id);
      const cx = 500;
      const cy = 400;
      const radius = 320;

      const result: PositionedNode[] = [
        {
          ...centerNode,
          x: cx - NODE_WIDTH / 2,
          y: cy - NODE_HEIGHT / 2,
          width: NODE_WIDTH,
          height: NODE_HEIGHT
        }
      ];

      const angleStep = (2 * Math.PI) / (satellites.length || 1);
      satellites.forEach((sat, idx) => {
        const angle = idx * angleStep - Math.PI / 2;
        const x = cx + radius * Math.cos(angle) - NODE_WIDTH / 2;
        const y = cy + radius * Math.sin(angle) - NODE_HEIGHT / 2;
        result.push({
          ...sat,
          x,
          y,
          width: NODE_WIDTH,
          height: NODE_HEIGHT
        });
      });

      return result;
    }

    // Layered DAG with Grid-Wrapping to eliminate horizontal sprawl
    const idToNode = new Map<string, GraphNode>(visibleNodes.map(n => [n.id, n]));
    const localChildrenMap = new Map<string, string[]>();
    const inDegree = new Map<string, number>();

    visibleNodes.forEach(n => {
      localChildrenMap.set(n.id, []);
      inDegree.set(n.id, 0);
    });

    visibleEdges.forEach(e => {
      if (localChildrenMap.has(e.source) && idToNode.has(e.target)) {
        localChildrenMap.get(e.source)!.push(e.target);
        inDegree.set(e.target, (inDegree.get(e.target) || 0) + 1);
      }
    });

    let roots = visibleNodes.filter(n => (inDegree.get(n.id) || 0) === 0);
    if (roots.length === 0 && visibleNodes.length > 0) {
      roots = [visibleNodes[0]];
    }

    const layerMap = new Map<string, number>();
    const queue: Array<{ id: string; layer: number }> = roots.map(r => ({ id: r.id, layer: 0 }));
    const visited = new Set<string>();

    while (queue.length > 0) {
      const { id, layer } = queue.shift()!;
      if (visited.has(id)) continue;
      visited.add(id);
      layerMap.set(id, Math.max(layerMap.get(id) || 0, layer));

      const children = localChildrenMap.get(id) || [];
      for (const childId of children) {
        queue.push({ id: childId, layer: layer + 1 });
      }
    }

    visibleNodes.forEach(n => {
      if (!layerMap.has(n.id)) {
        layerMap.set(n.id, 0);
      }
    });

    const layers: Array<GraphNode[]> = [];
    visibleNodes.forEach(n => {
      const l = layerMap.get(n.id) || 0;
      while (layers.length <= l) {
        layers.push([]);
      }
      layers[l].push(n);
    });

    const result: PositionedNode[] = [];
    let currentY = 80;

    layers.forEach((layerNodes) => {
      if (layerNodes.length <= MAX_LAYER_COLS) {
        const totalWidth = layerNodes.length * X_GAP;
        const startX = 600 - totalWidth / 2;

        layerNodes.forEach((node, nodeIndex) => {
          result.push({
            ...node,
            x: startX + nodeIndex * X_GAP,
            y: currentY,
            width: NODE_WIDTH,
            height: NODE_HEIGHT
          });
        });
        currentY += Y_GAP;
      } else {
        // Multi-column grid wrapping: wraps wide sibling layers into compact blocks!
        const cols = Math.min(MAX_LAYER_COLS, layerNodes.length);
        const rows = Math.ceil(layerNodes.length / cols);
        const totalWidth = cols * X_GAP;
        const startX = 600 - totalWidth / 2;

        layerNodes.forEach((node, nodeIndex) => {
          const col = nodeIndex % cols;
          const row = Math.floor(nodeIndex / cols);
          result.push({
            ...node,
            x: startX + col * X_GAP,
            y: currentY + row * Y_GAP,
            width: NODE_WIDTH,
            height: NODE_HEIGHT
          });
        });
        currentY += rows * Y_GAP + 20;
      }
    });

    return result;
  }, [visibleNodes, visibleEdges, isRadialLayout]);

  const nodePosMap = useMemo(() => {
    return new Map<string, PositionedNode>(positionedNodes.map(n => [n.id, n]));
  }, [positionedNodes]);

  // Compute graph bounds for Mini-Map
  const graphBounds = useMemo(() => {
    if (positionedNodes.length === 0) return { minX: 0, maxX: 1200, minY: 0, maxY: 800, width: 1200, height: 800 };
    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    positionedNodes.forEach(n => {
      if (n.x < minX) minX = n.x;
      if (n.x + n.width > maxX) maxX = n.x + n.width;
      if (n.y < minY) minY = n.y;
      if (n.y + n.height > maxY) maxY = n.y + n.height;
    });
    return {
      minX: minX - 100,
      maxX: maxX + 100,
      minY: minY - 100,
      maxY: maxY + 100,
      width: Math.max(600, maxX - minX + 200),
      height: Math.max(400, maxY - minY + 200)
    };
  }, [positionedNodes]);

  // Smooth "Fly-To" Camera Animation
  const flyToNode = useCallback((nodeId: string, customZoom?: number) => {
    const node = nodePosMap.get(nodeId);
    if (!node || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const targetZoom = customZoom || Math.max(zoom, 0.95);
    const nodeCenterX = node.x + node.width / 2;
    const nodeCenterY = node.y + node.height / 2;

    const targetPanX = rect.width / 2 - (nodeCenterX * targetZoom);
    const targetPanY = rect.height / 2 - (nodeCenterY * targetZoom);

    setPan({ x: targetPanX, y: targetPanY });
    setZoom(targetZoom);
    setFocusedPulseId(nodeId);
    setTimeout(() => setFocusedPulseId(null), 2500);
  }, [nodePosMap, zoom]);

  // Handle external flyToTargetId trigger
  useEffect(() => {
    if (flyToTargetId) {
      flyToNode(flyToTargetId);
    }
  }, [flyToTargetId, flyToNode]);

  // Center view on mount or layout change
  useEffect(() => {
    if (positionedNodes.length > 0 && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const avgX = positionedNodes.reduce((acc, n) => acc + n.x + n.width / 2, 0) / positionedNodes.length;
      const avgY = positionedNodes.reduce((acc, n) => acc + n.y + n.height / 2, 0) / positionedNodes.length;

      setPan({
        x: rect.width / 2 - avgX,
        y: rect.height / 2 - avgY
      });
      setZoom(isRadialLayout ? 0.9 : 0.85);
    }
  }, [positionedNodes.length, isRadialLayout]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return;
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    if (!isDragging) return;
    setPan({
      x: e.clientX - dragStart.x,
      y: e.clientY - dragStart.y
    });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    const factor = e.deltaY < 0 ? 1.1 : 0.9;
    setZoom(prev => Math.min(Math.max(prev * factor, 0.2), 2.5));
  };

  const handleResetFit = () => {
    if (positionedNodes.length > 0 && containerRef.current) {
      const rect = containerRef.current.getBoundingClientRect();
      const avgX = positionedNodes.reduce((acc, n) => acc + n.x + n.width / 2, 0) / positionedNodes.length;
      const avgY = positionedNodes.reduce((acc, n) => acc + n.y + n.height / 2, 0) / positionedNodes.length;
      setPan({
        x: rect.width / 2 - avgX,
        y: rect.height / 2 - avgY
      });
      setZoom(isRadialLayout ? 0.9 : 0.85);
    }
  };

  // Mini-map click to teleport camera
  const handleMiniMapClick = (e: React.MouseEvent<SVGSVGElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const mapW = rect.width;
    const mapH = rect.height;

    // Convert to graph coordinates
    const targetGraphX = graphBounds.minX + (clickX / mapW) * graphBounds.width;
    const targetGraphY = graphBounds.minY + (clickY / mapH) * graphBounds.height;

    if (containerRef.current) {
      const containerRect = containerRef.current.getBoundingClientRect();
      setPan({
        x: containerRect.width / 2 - targetGraphX * zoom,
        y: containerRect.height / 2 - targetGraphY * zoom
      });
    }
  };

  const getNodeColor = (kind: string, isRoot?: boolean) => {
    if (isRoot) return { bg: "var(--accent-primary)", border: "var(--accent-cyan)", text: "#ffffff" };
    switch (kind.toLowerCase()) {
      case "package":
      case "crate":
        return { bg: "rgba(99, 102, 241, 0.15)", border: "rgba(99, 102, 241, 0.5)", text: "#a5b4fc" };
      case "namespace":
      case "module":
        return { bg: "rgba(59, 130, 246, 0.15)", border: "rgba(59, 130, 246, 0.5)", text: "#93c5fd" };
      case "class":
      case "record":
        return { bg: "rgba(16, 185, 129, 0.15)", border: "rgba(16, 185, 129, 0.5)", text: "#6ee7b7" };
      case "struct":
        return { bg: "rgba(14, 165, 233, 0.15)", border: "rgba(14, 165, 233, 0.5)", text: "#7dd3fc" };
      case "interface":
      case "trait":
        return { bg: "rgba(168, 85, 247, 0.15)", border: "rgba(168, 85, 247, 0.5)", text: "#d8b4fe" };
      case "concept":
        return { bg: "rgba(244, 63, 94, 0.2)", border: "rgba(244, 63, 94, 0.6)", text: "#fda4af" };
      case "target_type":
        return { bg: "rgba(14, 165, 233, 0.15)", border: "rgba(14, 165, 233, 0.5)", text: "#38bdf8" };
      case "exception_class":
        return { bg: "rgba(239, 68, 68, 0.15)", border: "rgba(239, 68, 68, 0.5)", text: "#fca5a5" };
      default:
        return { bg: "rgba(148, 163, 184, 0.15)", border: "rgba(148, 163, 184, 0.4)", text: "#cbd5e1" };
    }
  };

  const queryLower = searchQuery.toLowerCase().trim();

  // Mini-map Viewport indicators
  const containerW = containerRef.current?.clientWidth || 1000;
  const containerH = containerRef.current?.clientHeight || 700;
  const miniW = 170;
  const miniH = 110;
  const miniScaleX = miniW / graphBounds.width;
  const miniScaleY = miniH / graphBounds.height;
  const miniScale = Math.min(miniScaleX, miniScaleY);

  const vpX = Math.max(0, (-pan.x / zoom - graphBounds.minX) * miniScale);
  const vpY = Math.max(0, (-pan.y / zoom - graphBounds.minY) * miniScale);
  const vpW = Math.min(miniW, (containerW / zoom) * miniScale);
  const vpH = Math.min(miniH, (containerH / zoom) * miniScale);

  return (
    <div
      className="graph-canvas-container"
      ref={containerRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onWheel={handleWheel}
      style={{ cursor: isDragging ? "grabbing" : "grab" }}
    >
      {/* Floating Canvas Controls */}
      <div className="canvas-floating-controls">
        <button
          type="button"
          className="btn btn-icon btn-secondary"
          onClick={() => setZoom(z => Math.min(z * 1.2, 2.5))}
          title="Zoom In"
        >
          ➕
        </button>
        <button
          type="button"
          className="btn btn-icon btn-secondary"
          onClick={() => setZoom(z => Math.max(z * 0.8, 0.2))}
          title="Zoom Out"
        >
          ➖
        </button>
        <button
          type="button"
          className="btn btn-icon btn-secondary"
          onClick={handleResetFit}
          title="Center & Fit All Nodes"
        >
          🎯
        </button>
        <span className="zoom-indicator">{Math.round(zoom * 100)}%</span>
      </div>

      {/* Picture-in-Picture Radar Mini-Map */}
      <div className={`canvas-minimap-card ${showMiniMap ? "expanded" : "collapsed"}`}>
        <div className="minimap-header">
          <span>🗺️ Mini-Map</span>
          <button
            type="button"
            className="btn-minimap-toggle"
            onClick={() => setShowMiniMap(!showMiniMap)}
            title="Toggle Mini-map"
          >
            {showMiniMap ? "▼" : "▲"}
          </button>
        </div>

        {showMiniMap && (
          <div className="minimap-body" title="Click anywhere to pan camera">
            <svg
              width={miniW}
              height={miniH}
              className="minimap-svg"
              onClick={handleMiniMapClick}
            >
              {/* Background */}
              <rect width={miniW} height={miniH} fill="rgba(15, 23, 42, 0.9)" rx="4" />

              {/* Render small nodes */}
              {positionedNodes.map(n => {
                const mx = (n.x - graphBounds.minX) * miniScale;
                const my = (n.y - graphBounds.minY) * miniScale;
                const mw = Math.max(4, n.width * miniScale);
                const mh = Math.max(3, n.height * miniScale);
                return (
                  <rect
                    key={n.id}
                    x={mx}
                    y={my}
                    width={mw}
                    height={mh}
                    rx="1"
                    fill={selectedNodeId === n.id ? "var(--accent-primary)" : "rgba(148, 163, 184, 0.45)"}
                  />
                );
              })}

              {/* Viewport Boundary Box */}
              <rect
                x={vpX}
                y={vpY}
                width={vpW}
                height={vpH}
                fill="rgba(56, 189, 248, 0.15)"
                stroke="var(--accent-cyan)"
                strokeWidth="1.5"
                rx="2"
                style={{ pointerEvents: "none" }}
              />
            </svg>
          </div>
        )}
      </div>

      <svg className="graph-svg" width="100%" height="100%">
        <defs>
          <marker id="arrow-contains" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--text-muted)" opacity="0.6" />
          </marker>
          <marker id="arrow-extends" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--accent-green)" />
          </marker>
          <marker id="arrow-implements" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--accent-purple, #a855f7)" />
          </marker>
          <marker id="arrow-lowers" viewBox="0 0 10 10" refX="22" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" fill="var(--accent-cyan)" />
          </marker>
        </defs>

        <g
          transform={`translate(${pan.x}, ${pan.y}) scale(${zoom})`}
          style={{
            transition: isDragging ? "none" : "transform 0.35s cubic-bezier(0.16, 1, 0.3, 1)"
          }}
        >
          {/* Edge Paths */}
          {visibleEdges.map(edge => {
            const src = nodePosMap.get(edge.source);
            const tgt = nodePosMap.get(edge.target);
            if (!src || !tgt) return null;

            const x1 = src.x + src.width / 2;
            const y1 = src.y + src.height / 2;
            const x2 = tgt.x + tgt.width / 2;
            const y2 = tgt.y + tgt.height / 2;

            let markerId = "arrow-contains";
            let strokeColor = "var(--border-color)";
            let strokeDash = undefined;

            if (edge.relation_kind === "extends") {
              markerId = "arrow-extends";
              strokeColor = "var(--accent-green)";
            } else if (edge.relation_kind === "implements") {
              markerId = "arrow-implements";
              strokeColor = "var(--accent-purple, #a855f7)";
              strokeDash = "4 4";
            } else if (edge.relation_kind === "lowers_to") {
              markerId = "arrow-lowers";
              strokeColor = "var(--accent-cyan)";
            }

            const pathD = isRadialLayout
              ? `M ${x1} ${y1} L ${x2} ${y2}`
              : `M ${x1} ${y1} C ${x1} ${(y1 + y2) / 2}, ${x2} ${(y1 + y2) / 2}, ${x2} ${y2}`;

            const midX = (x1 + x2) / 2;
            const midY = (y1 + y2) / 2;

            return (
              <g key={edge.id} className="graph-edge-group">
                <path
                  d={pathD}
                  fill="none"
                  stroke={strokeColor}
                  strokeWidth="2"
                  strokeDasharray={strokeDash}
                  markerEnd={`url(#${markerId})`}
                  className="graph-edge-line"
                />
                {edge.label && (
                  <text
                    x={midX}
                    y={midY - 4}
                    fill="var(--text-secondary)"
                    fontSize="10"
                    textAnchor="middle"
                    className="edge-label"
                  >
                    {edge.label}
                  </text>
                )}
              </g>
            );
          })}

          {/* Nodes */}
          {positionedNodes.map(node => {
            const isSelected = selectedNodeId === node.id;
            const isPulse = focusedPulseId === node.id;
            const isMatch = queryLower ? (
              node.name.toLowerCase().includes(queryLower) ||
              node.qualified_name.toLowerCase().includes(queryLower)
            ) : false;

            const colors = getNodeColor(node.kind, node.is_root);
            const childTargets = childrenMap.get(node.id) || [];
            const hasChildren = childTargets.length > 0 && !isRadialLayout;
            const isCollapsed = collapsedNodeIds.has(node.id);

            return (
              <g
                key={node.id}
                transform={`translate(${node.x}, ${node.y})`}
                className={`graph-node-group ${isSelected ? "selected" : ""} ${isMatch ? "matched" : ""} ${isPulse ? "pulsing-focus" : ""}`}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectNode(node);
                  flyToNode(node.id);
                }}
                style={{ cursor: "pointer" }}
              >
                {/* Pulsing Aura if focused */}
                {isPulse && (
                  <rect
                    x="-6"
                    y="-6"
                    width={node.width + 12}
                    height={node.height + 12}
                    rx="12"
                    ry="12"
                    fill="none"
                    stroke="var(--accent-cyan)"
                    strokeWidth="3"
                    className="focus-pulse-ring"
                  />
                )}

                {/* Node Box */}
                <rect
                  width={node.width}
                  height={node.height}
                  rx="8"
                  ry="8"
                  fill="var(--bg-card)"
                  stroke={isSelected ? "var(--accent-primary)" : isMatch ? "var(--accent-amber)" : colors.border}
                  strokeWidth={isSelected ? 3 : isMatch ? 2.5 : 1.5}
                  className="node-rect"
                />

                {/* Top Kind Badge */}
                <rect
                  x="8"
                  y="8"
                  width="70"
                  height="16"
                  rx="4"
                  ry="4"
                  fill={colors.bg}
                />
                <text
                  x="43"
                  y="19"
                  fill={colors.text}
                  fontSize="9"
                  fontWeight="700"
                  textAnchor="middle"
                  letterSpacing="0.04em"
                  className="node-badge-text"
                >
                  {(node.kind || "NODE").toUpperCase()}
                </text>

                {/* Language Tag if present */}
                {node.language && (
                  <text
                    x={node.width - 10}
                    y="19"
                    fill="var(--text-muted)"
                    fontSize="9"
                    fontWeight="600"
                    textAnchor="end"
                  >
                    {node.language.toUpperCase()}
                  </text>
                )}

                {/* Symbol count badge if present */}
                {typeof node.symbol_count === "number" && node.symbol_count > 0 && (
                  <text
                    x={node.width - 10}
                    y="19"
                    fill="var(--text-secondary)"
                    fontSize="9"
                    textAnchor="end"
                  >
                    {node.symbol_count} syms
                  </text>
                )}

                {/* Node Main Title */}
                <text
                  x="10"
                  y="42"
                  fill="var(--text-primary)"
                  fontSize="13"
                  fontWeight="700"
                  className="node-title"
                >
                  {node.name.length > 22 ? `${node.name.slice(0, 20)}…` : node.name}
                </text>

                {/* Node Subtitle */}
                <text
                  x="10"
                  y="58"
                  fill="var(--text-secondary)"
                  fontSize="9.5"
                  className="node-subtitle"
                >
                  {node.syntax_template
                    ? (node.syntax_template.length > 25 ? `${node.syntax_template.slice(0, 23)}…` : node.syntax_template)
                    : (node.qualified_name.length > 27 ? `…${node.qualified_name.slice(-25)}` : node.qualified_name)}
                </text>

                {/* Interactive Child Toggle Icon Button */}
                {hasChildren && (
                  <g
                    className={`node-toggle-btn ${isCollapsed ? "collapsed" : "expanded"}`}
                    onClick={(e) => {
                      e.stopPropagation();
                      onToggleCollapse(node.id);
                    }}
                    style={{ cursor: "pointer" }}
                  >
                    <circle
                      cx={node.width / 2}
                      cy={node.height}
                      r="11"
                      fill="var(--bg-surface)"
                      stroke={isCollapsed ? "var(--accent-amber)" : "var(--border-color)"}
                      strokeWidth="1.5"
                      className="toggle-circle"
                    />
                    <text
                      x={node.width / 2}
                      y={node.height + 4}
                      textAnchor="middle"
                      fontSize="10"
                      fontWeight="700"
                      fill={isCollapsed ? "var(--accent-amber)" : "var(--text-secondary)"}
                      className="toggle-text"
                    >
                      {isCollapsed ? `+${childTargets.length}` : "−"}
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </g>
      </svg>
    </div>
  );
};
