import React, { useState } from "react";
import { PairwiseImpedanceMatrix } from "../../types";

interface ImpedanceHeatmapProps {
  matrix: PairwiseImpedanceMatrix;
  languages: string[];
  onSelectPair: (sourceLang: string, targetLang: string, score: number) => void;
}

export const ImpedanceHeatmap: React.FC<ImpedanceHeatmapProps> = ({
  matrix,
  languages,
  onSelectPair
}) => {
  const [hoveredCell, setHoveredCell] = useState<{ src: string; tgt: string } | null>(null);

  const getCellColor = (score: number, isSelf: boolean) => {
    if (isSelf) {
      return {
        bg: "rgba(255, 255, 255, 0.03)",
        border: "var(--border-subtle)",
        text: "var(--text-muted)",
        glow: "none"
      };
    }
    if (score < 0.25) {
      return {
        bg: "rgba(16, 185, 129, 0.16)",
        border: "rgba(16, 185, 129, 0.35)",
        text: "#34d399",
        glow: "0 0 8px rgba(16, 185, 129, 0.15)"
      };
    }
    if (score < 0.55) {
      return {
        bg: "rgba(6, 182, 212, 0.16)",
        border: "rgba(6, 182, 212, 0.35)",
        text: "#38bdf8",
        glow: "0 0 8px rgba(6, 182, 212, 0.15)"
      };
    }
    if (score < 0.80) {
      return {
        bg: "rgba(245, 158, 11, 0.18)",
        border: "rgba(245, 158, 11, 0.4)",
        text: "#fbbf24",
        glow: "0 0 8px rgba(245, 158, 11, 0.18)"
      };
    }
    return {
      bg: "rgba(239, 68, 68, 0.22)",
      border: "rgba(239, 68, 68, 0.45)",
      text: "#f87171",
      glow: "0 0 10px rgba(239, 68, 68, 0.25)"
    };
  };

  return (
    <div className="impedance-heatmap-container">
      <div className="heatmap-header-intro">
        <div>
          <h3 className="section-title">⚡ 6×6 Pairwise Transpiler Impedance Matrix</h3>
          <p className="section-subtitle">
            Measures directional semantic impedance (0.0 to 1.0) when transpiling code from a <strong>Source Language (rows)</strong> into a <strong>Target Language (columns)</strong>.
            Click any cell to inspect the dimensional penalty breakdown.
          </p>
        </div>
        <div className="matrix-badge">
          Directional Metric (Asymmetric)
        </div>
      </div>

      <div className="heatmap-grid-wrapper">
        <table className="heatmap-table">
          <thead>
            <tr>
              <th className="corner-header">
                <span className="source-label">Source ▼</span>
                <span className="target-label">Target ▶</span>
              </th>
              {languages.map(tgt => (
                <th
                  key={tgt}
                  className={`target-header ${hoveredCell?.tgt === tgt ? "col-highlight" : ""}`}
                >
                  <span className="lang-code">{tgt.toUpperCase()}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {languages.map(src => {
              const isRowHovered = hoveredCell?.src === src;
              return (
                <tr key={src} className={isRowHovered ? "row-highlight" : ""}>
                  <th className="source-header">
                    <span className="lang-code">{src.toUpperCase()}</span>
                  </th>
                  {languages.map(tgt => {
                    const isSelf = src === tgt;
                    const score = matrix[src]?.[tgt] ?? (isSelf ? 0.0 : 0.5);
                    const colorStyle = getCellColor(score, isSelf);
                    const isHovered = hoveredCell?.src === src && hoveredCell?.tgt === tgt;

                    return (
                      <td
                        key={tgt}
                        className={`heatmap-cell ${isHovered ? "cell-hovered" : ""} ${isSelf ? "cell-self" : ""}`}
                        style={{
                          backgroundColor: colorStyle.bg,
                          borderColor: colorStyle.border,
                          boxShadow: isHovered ? colorStyle.glow : undefined
                        }}
                        onMouseEnter={() => setHoveredCell({ src, tgt })}
                        onMouseLeave={() => setHoveredCell(null)}
                        onClick={() => onSelectPair(src, tgt, score)}
                        title={`${src.toUpperCase()} ➔ ${tgt.toUpperCase()}: ${score.toFixed(3)} ${isSelf ? "(Identity)" : "(Click to inspect)"}`}
                      >
                        <div className="cell-content">
                          <span className="cell-score" style={{ color: colorStyle.text }}>
                            {isSelf ? "—" : score.toFixed(3)}
                          </span>
                        </div>
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Legend & Calibration Footnote */}
      <div className="heatmap-footer">
        <div className="heatmap-legend">
          <span className="legend-label">Impedance Spectrum:</span>
          <div className="legend-scale">
            <div className="legend-step" style={{ backgroundColor: "rgba(16, 185, 129, 0.3)" }}>
              <span>≤ 0.25</span>
              <span className="step-name">Minimal</span>
            </div>
            <div className="legend-step" style={{ backgroundColor: "rgba(6, 182, 212, 0.3)" }}>
              <span>0.25 - 0.55</span>
              <span className="step-name">Moderate</span>
            </div>
            <div className="legend-step" style={{ backgroundColor: "rgba(245, 158, 11, 0.3)" }}>
              <span>0.55 - 0.80</span>
              <span className="step-name">Elevated</span>
            </div>
            <div className="legend-step" style={{ backgroundColor: "rgba(239, 68, 68, 0.35)" }}>
              <span>≥ 0.80</span>
              <span className="step-name">Severe</span>
            </div>
          </div>
        </div>

        <div className="heatmap-footnote">
          * Directional asymmetry: Dynamic languages (Python) Lowering into strict borrow-checked (Rust) incurs high typing, memory and error handling impedance (<strong>{matrix["python"]?.["rust"]?.toFixed(3) ?? "0.812"}</strong>), whereas Rust $\to$ Python requires primarily erasure (<strong>{matrix["rust"]?.["python"]?.toFixed(3) ?? "0.380"}</strong>).
        </div>
      </div>
    </div>
  );
};
