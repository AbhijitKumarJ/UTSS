import React, { useState, useEffect } from "react";
import { StdlibCoverageResponse, UnmappedTaxonomyCandidate } from "../../types";
import { fetchStdlibCoverage, crawlStdlib } from "../../api";

const LANG_CONFIG: Record<string, { label: string; badge: string; color: string }> = {
  python: { label: "Python", badge: "PY", color: "#38bdf8" },
  csharp: { label: "C# .NET", badge: "C#", color: "#a855f7" },
  cpp: { label: "C++20", badge: "C++", color: "#f43f5e" },
  go: { label: "Go", badge: "GO", color: "#06b6d4" },
  rust: { label: "Rust", badge: "RS", color: "#f97316" },
  typescript: { label: "TypeScript", badge: "TS", color: "#eab308" },
};

const DOMAIN_CONFIG: Record<string, { label: string; icon: string }> = {
  all: { label: "All Domains", icon: "🌐" },
  collection: { label: "Collections", icon: "📦" },
  concurrency: { label: "Concurrency", icon: "⚡" },
  stream_io: { label: "Stream I/O", icon: "💾" },
  exception: { label: "Exceptions", icon: "⚠️" },
  protocol_interface: { label: "Protocols & Traits", icon: "🧩" },
};

export const StdlibTaxonomyExplorer: React.FC = () => {
  const [data, setData] = useState<StdlibCoverageResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [crawling, setCrawling] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedLang, setSelectedLang] = useState<string>("all");
  const [selectedDomain, setSelectedDomain] = useState<string>("all");
  const [selectedRisk, setSelectedRisk] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchStdlibCoverage();
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to load stdlib coverage data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCrawl = async () => {
    setCrawling(true);
    setError(null);
    try {
      const res = await crawlStdlib();
      setData(res);
    } catch (err: any) {
      setError(err.message || "Failed to crawl stdlib databases");
    } finally {
      setCrawling(false);
    }
  };

  const candidates = data?.unmapped_candidates || [];

  const filteredCandidates = candidates.filter((item: UnmappedTaxonomyCandidate) => {
    if (selectedLang !== "all" && item.language !== selectedLang) return false;
    if (selectedDomain !== "all" && item.domain !== selectedDomain) return false;
    if (selectedRisk !== "all" && item.impedance_risk !== selectedRisk) return false;
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      const matchName = item.qualified_name.toLowerCase().includes(q) || item.short_name.toLowerCase().includes(q);
      const matchConcept = item.proposed_concept.toLowerCase().includes(q);
      if (!matchName && !matchConcept) return false;
    }
    return true;
  });

  return (
    <div className="stdlib-taxonomy-container">
      {/* Header */}
      <div className="taxonomy-header">
        <div className="taxonomy-title-group">
          <h3 className="taxonomy-title">📚 Autonomous Stdlib Universe & Unmapped Ecosystem Explorer</h3>
          <p className="taxonomy-subtitle">
            Pass 4 analytical crawler harvesting unmapped standard library containers across 6 languages.
            Evaluates algorithmic impedance risks, detects missing universal concepts, and quantifies bridge coverage.
          </p>
        </div>

        <div className="taxonomy-actions">
          <button
            type="button"
            className="btn btn-primary btn-sm"
            onClick={handleCrawl}
            disabled={crawling || loading}
          >
            {crawling ? "⚙️ Crawling Stdlibs..." : "🔄 Re-crawl & Refresh Catalog"}
          </button>
        </div>
      </div>

      {error && (
        <div className="taxonomy-error-banner">
          <span>⚠️ {error}</span>
          <button type="button" className="btn btn-icon btn-sm" onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {/* Language Coverage Metric Cards */}
      <div className="language-coverage-grid">
        {data &&
          Object.entries(data.languages).map(([langKey, stats]) => {
            const meta = LANG_CONFIG[langKey] || { label: langKey, badge: langKey.toUpperCase(), color: "#64748b" };
            const isSelected = selectedLang === langKey;
            return (
              <div
                key={langKey}
                className={`lang-coverage-card ${isSelected ? "selected" : ""}`}
                onClick={() => setSelectedLang(selectedLang === langKey ? "all" : langKey)}
              >
                <div className="card-top">
                  <span className="lang-badge" style={{ backgroundColor: `${meta.color}22`, borderColor: meta.color, color: meta.color }}>
                    {meta.badge}
                  </span>
                  <span className="lang-label">{meta.label}</span>
                  <span className="coverage-pct-pill">{stats.coverage_pct}% Mapped</span>
                </div>

                <div className="coverage-progress-bar-bg">
                  <div
                    className="coverage-progress-bar-fill"
                    style={{ width: `${Math.max(stats.coverage_pct, 4)}%`, backgroundColor: meta.color }}
                  />
                </div>

                <div className="card-bottom-metrics">
                  <div className="metric-col">
                    <span className="metric-num">{stats.mapped_count}</span>
                    <span className="metric-tag">Mapped</span>
                  </div>
                  <div className="metric-col">
                    <span className="metric-num">{stats.unmapped_count}</span>
                    <span className="metric-tag">Unmapped</span>
                  </div>
                  <div className="metric-col">
                    <span className="metric-num">{stats.total_containers}</span>
                    <span className="metric-tag">Total</span>
                  </div>
                </div>
              </div>
            );
          })}
      </div>

      {/* Controls: Domain Filter, Search, Risk */}
      <div className="taxonomy-controls-bar">
        {/* Domain Filter Pills */}
        <div className="domain-pills-group">
          {Object.entries(DOMAIN_CONFIG).map(([domKey, domMeta]) => (
            <button
              key={domKey}
              type="button"
              className={`domain-pill ${selectedDomain === domKey ? "active" : ""}`}
              onClick={() => setSelectedDomain(domKey)}
            >
              <span>{domMeta.icon}</span>
              <span>{domMeta.label}</span>
              {data?.domain_distribution[domKey] !== undefined && (
                <span className="domain-count-badge">{data.domain_distribution[domKey]}</span>
              )}
            </button>
          ))}
        </div>

        {/* Search & Risk Filter */}
        <div className="secondary-filters-group">
          <div className="search-input-wrapper">
            <span className="search-icon">🔍</span>
            <input
              type="text"
              className="taxonomy-search-input"
              placeholder="Search by container name or proposed concept..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
            {searchQuery && (
              <button
                type="button"
                className="clear-search-btn"
                onClick={() => setSearchQuery("")}
              >
                ✕
              </button>
            )}
          </div>

          <select
            className="db-dropdown filter-dropdown"
            value={selectedRisk}
            onChange={(e) => setSelectedRisk(e.target.value)}
          >
            <option value="all">⚡ All Impedance Levels</option>
            <option value="LOW">🟢 Low Impedance</option>
            <option value="MEDIUM">🟡 Medium Impedance</option>
            <option value="HIGH">🔴 High Impedance</option>
          </select>

          {selectedLang !== "all" && (
            <button
              type="button"
              className="btn btn-outline btn-sm reset-filter-btn"
              onClick={() => setSelectedLang("all")}
            >
              Reset Language ({LANG_CONFIG[selectedLang]?.label || selectedLang}) ✕
            </button>
          )}
        </div>
      </div>

      {/* Candidates Table */}
      <div className="taxonomy-candidates-card">
        <div className="candidates-card-header">
          <span className="results-count">
            Showing <strong>{filteredCandidates.length}</strong> of {candidates.length} unmapped standard library constructs
          </span>
          <span className="catalog-source-tag">Catalog: <code>utss_universal_bridge.db</code></span>
        </div>

        {loading ? (
          <div className="taxonomy-loading-spinner">
            <div className="spinner" />
            <p>Harvesting standard library distributions across 6 databases...</p>
          </div>
        ) : filteredCandidates.length === 0 ? (
          <div className="empty-taxonomy-placeholder">
            <span className="empty-icon">📂</span>
            <h4>No matching unmapped constructs</h4>
            <p>Try clearing filters or changing search keywords.</p>
          </div>
        ) : (
          <div className="table-responsive">
            <table className="taxonomy-table">
              <thead>
                <tr>
                  <th style={{ width: "90px" }}>Language</th>
                  <th>Construct Name & Namespace</th>
                  <th style={{ width: "130px" }}>Domain</th>
                  <th style={{ width: "100px" }}>Kind</th>
                  <th style={{ width: "90px" }}>Methods</th>
                  <th>Proposed Universal IR Concept</th>
                  <th style={{ width: "130px" }}>Impedance Risk</th>
                  <th>Impedance Evaluation</th>
                </tr>
              </thead>
              <tbody>
                {filteredCandidates.map((candidate: UnmappedTaxonomyCandidate, idx: number) => {
                  const meta = LANG_CONFIG[candidate.language] || {
                    badge: candidate.language.toUpperCase(),
                    color: "#64748b",
                  };
                  return (
                    <tr key={`${candidate.language}-${candidate.qualified_name}-${idx}`}>
                      <td>
                        <span
                          className="lang-pill"
                          style={{
                            backgroundColor: `${meta.color}22`,
                            color: meta.color,
                            borderColor: meta.color,
                          }}
                        >
                          {meta.badge}
                        </span>
                      </td>
                      <td>
                        <div className="construct-cell">
                          <strong className="construct-short-name">{candidate.short_name}</strong>
                          <span className="construct-qname">{candidate.qualified_name}</span>
                        </div>
                      </td>
                      <td>
                        <span className="domain-tag">{candidate.domain}</span>
                      </td>
                      <td>
                        <span className="kind-tag">{candidate.entity_kind}</span>
                      </td>
                      <td>
                        <span className="method-count-badge">{candidate.public_methods}</span>
                      </td>
                      <td>
                        <code className="proposed-concept-code">{candidate.proposed_concept}</code>
                      </td>
                      <td>
                        <span className={`risk-pill risk-${candidate.impedance_risk.toLowerCase()}`}>
                          {candidate.impedance_risk === "HIGH" ? "🔴 High" : candidate.impedance_risk === "MEDIUM" ? "🟡 Medium" : "🟢 Low"}
                        </span>
                      </td>
                      <td className="notes-cell">
                        <span className="impedance-note-text">{candidate.impedance_notes}</span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
