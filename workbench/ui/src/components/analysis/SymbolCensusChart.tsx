import React, { useState } from "react";
import { SymbolCensusItem } from "../../types";

interface SymbolCensusChartProps {
  census: SymbolCensusItem[];
}

export const SymbolCensusChart: React.FC<SymbolCensusChartProps> = ({ census }) => {
  const [metric, setMetric] = useState<"symbols" | "containers" | "callables">("symbols");

  const getMetricValue = (item: SymbolCensusItem) => {
    switch (metric) {
      case "symbols": return item.total_symbols;
      case "containers": return item.total_containers;
      case "callables": return item.total_callables;
    }
  };

  const maxVal = Math.max(...census.map(getMetricValue), 1);

  const getLanguageColor = (lang: string) => {
    switch (lang.toLowerCase()) {
      case "python": return "#38bdf8"; // Light sky blue
      case "csharp": return "#a855f7"; // Purple
      case "rust": return "#f97316";   // Rust orange
      case "typescript": return "#3b82f6"; // TS blue
      case "cpp": return "#ec4899";    // C++ pink
      case "go": return "#10b981";     // Go emerald/cyan
      default: return "#64748b";
    }
  };

  return (
    <div className="analysis-card census-chart-card">
      <div className="card-header-row">
        <div>
          <h3 className="section-title">📊 Multi-Language Standard Library Surface Area</h3>
          <p className="section-subtitle">
            Catalog surface area across Layer 1 relational entities (Symbols, Containers, Callables).
          </p>
        </div>
        <div className="metric-toggle-group">
          <button
            className={`btn-toggle ${metric === "symbols" ? "active" : ""}`}
            onClick={() => setMetric("symbols")}
          >
            Symbols
          </button>
          <button
            className={`btn-toggle ${metric === "containers" ? "active" : ""}`}
            onClick={() => setMetric("containers")}
          >
            Containers
          </button>
          <button
            className={`btn-toggle ${metric === "callables" ? "active" : ""}`}
            onClick={() => setMetric("callables")}
          >
            Callables
          </button>
        </div>
      </div>

      <div className="census-bars-container">
        {census.map(item => {
          const val = getMetricValue(item);
          const pct = Math.max(2, (val / maxVal) * 100);
          const color = getLanguageColor(item.language);
          const callableDensity = item.total_symbols > 0
            ? ((item.total_callables / item.total_symbols) * 100).toFixed(1)
            : "0.0";

          return (
            <div key={item.language} className="census-bar-row">
              <div className="census-lang-label">
                <span className="lang-bullet" style={{ backgroundColor: color }} />
                <span className="lang-name">{item.language.toUpperCase()}</span>
              </div>

              <div className="census-bar-track">
                <div
                  className="census-bar-fill"
                  style={{
                    width: `${pct}%`,
                    backgroundColor: color
                  }}
                />
                <span className="census-bar-count">
                  {val.toLocaleString()}
                </span>
              </div>

              <div className="census-stats-micro">
                <span title="Callable Density">
                  {callableDensity}% Callables
                </span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="census-summary-table-wrapper">
        <table className="compact-data-table">
          <thead>
            <tr>
              <th>Language</th>
              <th>Total Symbols</th>
              <th>Containers</th>
              <th>Callables</th>
              <th>Callable Density</th>
            </tr>
          </thead>
          <tbody>
            {census.map(item => (
              <tr key={item.language}>
                <td>
                  <strong>{item.language.toUpperCase()}</strong>
                </td>
                <td>{item.total_symbols.toLocaleString()}</td>
                <td>{item.total_containers.toLocaleString()}</td>
                <td>{item.total_callables.toLocaleString()}</td>
                <td>
                  {item.total_symbols > 0
                    ? `${((item.total_callables / item.total_symbols) * 100).toFixed(1)}%`
                    : "0.0%"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
