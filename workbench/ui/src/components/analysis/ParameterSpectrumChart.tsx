import React, { useState } from "react";

interface ParameterSpectrumChartProps {
  parameters: Record<string, Record<string, number>>;
  languages: string[];
}

export const ParameterSpectrumChart: React.FC<ParameterSpectrumChartProps> = ({
  parameters,
  languages
}) => {
  const [hoveredMode, setHoveredMode] = useState<string | null>(null);

  // Harmonized palette for parameter passing semantics
  const getModeColor = (mode: string) => {
    const m = mode.toLowerCase();
    if (m.includes("val") || m === "value") return "var(--accent-cyan, #06b6d4)";
    if (m.includes("mut")) return "var(--accent-danger, #ef4444)";
    if (m.includes("ref") || m.includes("borrow")) return "var(--accent-amber, #f59e0b)";
    if (m.includes("pointer") || m.includes("*")) return "#a855f7";
    if (m.includes("out") || m.includes("inout")) return "var(--accent-green, #10b981)";
    if (m.includes("keyword") || m.includes("positional")) return "#3b82f6";
    if (m.includes("variadic") || m.includes("rest") || m.includes("params")) return "#ec4899";
    return "#64748b";
  };

  // Collect all unique pass modes across languages
  const allModes = Array.from(
    new Set(
      Object.values(parameters).flatMap(dict => Object.keys(dict))
    )
  ).sort();

  return (
    <div className="analysis-card parameter-spectrum-card">
      <div className="card-header-row">
        <div>
          <h3 className="section-title">🧬 Parameter Passing & Ownership Conventions</h3>
          <p className="section-subtitle">
            Proportional breakdown of calling conventions (Value, Reference, Mutable Borrow, Pointer, Out, Keyword).
          </p>
        </div>
      </div>

      <div className="spectrum-bars-list">
        {languages.map(lang => {
          const dict = parameters[lang] || {};
          const totalParams = Object.values(dict).reduce((a, b) => a + b, 0);

          return (
            <div key={lang} className="spectrum-lang-row">
              <div className="spectrum-lang-label">
                <span className="lang-name">{lang.toUpperCase()}</span>
                <span className="param-total">({totalParams.toLocaleString()} params)</span>
              </div>

              <div className="spectrum-stacked-track">
                {Object.entries(dict).map(([mode, count]) => {
                  if (totalParams === 0) return null;
                  const pct = (count / totalParams) * 100;
                  const color = getModeColor(mode);
                  const isHovered = hoveredMode === mode;

                  return (
                    <div
                      key={mode}
                      className={`spectrum-segment ${isHovered ? "segment-hovered" : ""}`}
                      style={{
                        width: `${pct}%`,
                        backgroundColor: color,
                        opacity: hoveredMode && !isHovered ? 0.35 : 1
                      }}
                      onMouseEnter={() => setHoveredMode(mode)}
                      onMouseLeave={() => setHoveredMode(null)}
                      title={`${lang.toUpperCase()} - ${mode}: ${count.toLocaleString()} (${pct.toFixed(1)}%)`}
                    >
                      {pct > 12 && (
                        <span className="segment-label">
                          {mode} ({pct.toFixed(0)}%)
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>

      {/* Interactive Legend */}
      <div className="spectrum-legend">
        <span className="legend-label">Passing Semantic Classes:</span>
        <div className="legend-pills">
          {allModes.map(mode => (
            <button
              key={mode}
              className={`legend-pill ${hoveredMode === mode ? "active" : ""}`}
              onMouseEnter={() => setHoveredMode(mode)}
              onMouseLeave={() => setHoveredMode(null)}
            >
              <span className="pill-dot" style={{ backgroundColor: getModeColor(mode) }} />
              <span className="pill-name">{mode}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="transpiler-insight-banner">
        <strong>Transpiler Impedance Rule:</strong> When lowering from pass-by-reference/pointer languages (C++, Go) to pass-by-value/object-reference runtimes (Python, TypeScript), mutability side-effects require wrapping mutated parameters in tuple returns or dedicated result containers.
      </div>
    </div>
  );
};
