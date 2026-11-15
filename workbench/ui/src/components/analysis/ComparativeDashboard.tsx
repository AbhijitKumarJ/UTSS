import React, { useState, useEffect, useCallback } from "react";
import { ComparativeAnalysisData } from "../../types";
import { fetchComparativeAnalysis, fetchAnalysisReport } from "../../api";
import { ImpedanceHeatmap } from "./ImpedanceHeatmap";
import { ImpedanceDetailModal } from "./ImpedanceDetailModal";
import { SymbolCensusChart } from "./SymbolCensusChart";
import { ParameterSpectrumChart } from "./ParameterSpectrumChart";
import { MutabilityChart } from "./MutabilityChart";
import { OverloadErrorChart } from "./OverloadErrorChart";

interface ComparativeDashboardProps {
  onNavigateToPlayground?: (sourceLang: string, targetLang: string) => void;
}

type TabType = "impedance" | "census" | "parameters" | "mutability" | "overloading";

export const ComparativeDashboard: React.FC<ComparativeDashboardProps> = ({
  onNavigateToPlayground
}) => {
  const [variant, setVariant] = useState<"recommended" | "full">("recommended");
  const [activeTab, setActiveTab] = useState<TabType>("impedance");
  const [data, setData] = useState<ComparativeAnalysisData | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Selected cell for impedance modal
  const [selectedPair, setSelectedPair] = useState<{
    source: string;
    target: string;
    score: number;
  } | null>(null);

  const loadData = useCallback(async (v: "recommended" | "full") => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetchComparativeAnalysis(v);
      setData(res);
    } catch (err: any) {
      console.error("Failed to load comparative analysis:", err);
      setError(err.message || "Failed to load comparative metrics");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData(variant);
  }, [variant, loadData]);

  const handleDownloadReport = async () => {
    try {
      const md = await fetchAnalysisReport(variant);
      const blob = new Blob([md], { type: "text/markdown;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `utss_comparative_report_${variant}.md`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Download failed:", err);
      alert("Failed to download analysis report.");
    }
  };

  // Find min and max impedance pairs (excluding diagonal self-pairs)
  let minPair = { src: "", tgt: "", score: 1.0 };
  let maxPair = { src: "", tgt: "", score: 0.0 };
  let totalSymbolsAll = 0;

  if (data) {
    totalSymbolsAll = data.symbol_census.reduce((acc, curr) => acc + curr.total_symbols, 0);

    for (const src of data.languages) {
      for (const tgt of data.languages) {
        if (src === tgt) continue;
        const score = data.pairwise_impedance[src]?.[tgt] ?? 0.5;
        if (score < minPair.score) {
          minPair = { src, tgt, score };
        }
        if (score > maxPair.score) {
          maxPair = { src, tgt, score };
        }
      }
    }
  }

  return (
    <div className="comparative-dashboard-container">
      {/* Top Header & Toolbar */}
      <div className="dashboard-header-toolbar">
        <div className="dashboard-title-group">
          <h2>📊 Empirical Cross-Language Data Science</h2>
          <p>
            Relational AST metrics, state mutability boundaries, and 6×6 transpiler semantic impedance.
          </p>
        </div>

        <div className="dashboard-actions">
          {/* Variant Selector */}
          <div className="variant-switch-group">
            <label className="variant-label">Catalog Variant:</label>
            <div className="toggle-pill-container">
              <button
                className={`toggle-pill ${variant === "recommended" ? "active" : ""}`}
                onClick={() => setVariant("recommended")}
                type="button"
              >
                Recommended
              </button>
              <button
                className={`toggle-pill ${variant === "full" ? "active" : ""}`}
                onClick={() => setVariant("full")}
                type="button"
              >
                Full Stdlib
              </button>
            </div>
          </div>

          <button
            className="btn btn-secondary"
            onClick={() => loadData(variant)}
            title="Refresh metrics from federated database"
            type="button"
          >
            🔄 Refresh
          </button>

          <button
            className="btn btn-primary"
            onClick={handleDownloadReport}
            title="Download full Markdown analysis report"
            type="button"
          >
            📥 Download Report (.md)
          </button>
        </div>
      </div>

      {/* Quick Summary Cards */}
      {data && (
        <div className="dashboard-summary-cards">
          <div className="summary-card">
            <span className="card-micro-title">Profiled Languages</span>
            <span className="card-big-stat">{data.languages.length}</span>
            <span className="card-footer-note">Python, C#, C++, Go, Rust, TS</span>
          </div>

          <div className="summary-card">
            <span className="card-micro-title">Analyzed Catalog Symbols</span>
            <span className="card-big-stat">{totalSymbolsAll.toLocaleString()}</span>
            <span className="card-footer-note">Layer 1 unified schema records</span>
          </div>

          <div className="summary-card">
            <span className="card-micro-title">Lowest Semantic Impedance</span>
            <span className="card-big-stat text-success">
              {minPair.src ? `${minPair.src.toUpperCase()} ➔ ${minPair.tgt.toUpperCase()}` : "—"}
            </span>
            <span className="card-footer-note">
              Score: <strong>{minPair.score.toFixed(3)}</strong> (High syntactic parity)
            </span>
          </div>

          <div className="summary-card">
            <span className="card-micro-title">Highest Semantic Impedance</span>
            <span className="card-big-stat text-danger">
              {maxPair.src ? `${maxPair.src.toUpperCase()} ➔ ${maxPair.tgt.toUpperCase()}` : "—"}
            </span>
            <span className="card-footer-note">
              Score: <strong>{maxPair.score.toFixed(3)}</strong> (Borrow check & errors)
            </span>
          </div>
        </div>
      )}

      {/* Metric Dimension Navigation Tabs */}
      <div className="dimension-tabs-bar">
        <button
          className={`dimension-tab ${activeTab === "impedance" ? "active" : ""}`}
          onClick={() => setActiveTab("impedance")}
        >
          ⚡ 6×6 Transpiler Impedance Matrix
        </button>
        <button
          className={`dimension-tab ${activeTab === "census" ? "active" : ""}`}
          onClick={() => setActiveTab("census")}
        >
          📊 Symbol & Container Census
        </button>
        <button
          className={`dimension-tab ${activeTab === "parameters" ? "active" : ""}`}
          onClick={() => setActiveTab("parameters")}
        >
          🧬 Parameter Passing Spectrum
        </button>
        <button
          className={`dimension-tab ${activeTab === "mutability" ? "active" : ""}`}
          onClick={() => setActiveTab("mutability")}
        >
          🔒 State Mutability & Safety
        </button>
        <button
          className={`dimension-tab ${activeTab === "overloading" ? "active" : ""}`}
          onClick={() => setActiveTab("overloading")}
        >
          ⚙️ Overloading & Error Handling
        </button>
      </div>

      {/* Main Content Area */}
      <div className="dashboard-content-area">
        {isLoading ? (
          <div className="analysis-loading-state">
            <div className="spinner" />
            <p>Querying federated engine across 6 language catalogs...</p>
          </div>
        ) : error ? (
          <div className="analysis-error-state">
            <p className="error-title">⚠️ Error loading comparative data</p>
            <p className="error-msg">{error}</p>
            <button className="btn btn-primary" onClick={() => loadData(variant)}>
              Retry
            </button>
          </div>
        ) : !data ? null : (
          <>
            {activeTab === "impedance" && (
              <ImpedanceHeatmap
                matrix={data.pairwise_impedance}
                languages={data.languages}
                onSelectPair={(src, tgt, score) => {
                  setSelectedPair({ source: src, target: tgt, score });
                }}
              />
            )}

            {activeTab === "census" && (
              <SymbolCensusChart census={data.symbol_census} />
            )}

            {activeTab === "parameters" && (
              <ParameterSpectrumChart
                parameters={data.parameter_passing}
                languages={data.languages}
              />
            )}

            {activeTab === "mutability" && (
              <MutabilityChart mutability={data.mutability_matrix} />
            )}

            {activeTab === "overloading" && (
              <OverloadErrorChart
                overloading={data.overloading_metrics}
                errorHandling={data.error_handling}
              />
            )}
          </>
        )}
      </div>

      {/* Drill-down Modal */}
      {selectedPair && (
        <ImpedanceDetailModal
          sourceLang={selectedPair.source}
          targetLang={selectedPair.target}
          score={selectedPair.score}
          onClose={() => setSelectedPair(null)}
          onNavigateToPlayground={onNavigateToPlayground}
        />
      )}
    </div>
  );
};
