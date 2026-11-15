import React, { useState } from "react";
import { ProvenanceRecord } from "../../types";

interface ProvenanceInspectorProps {
  records: ProvenanceRecord[];
}

export const ProvenanceInspector: React.FC<ProvenanceInspectorProps> = ({ records }) => {
  const [filterText, setFilterText] = useState<string>("");

  const filtered = records.filter(r => {
    if (!filterText.trim()) return true;
    const q = filterText.toLowerCase();
    return (
      r.construct.toLowerCase().includes(q) ||
      r.concept_key.toLowerCase().includes(q) ||
      r.resolved_target.toLowerCase().includes(q) ||
      (r.catalog_signature && r.catalog_signature.toLowerCase().includes(q))
    );
  });

  return (
    <div className="provenance-inspector-container">
      <div className="provenance-header">
        <div className="provenance-title-group">
          <h4>🏛️ Empirical Catalog Provenance Trace</h4>
          <span className="badge badge-info">{records.length} Lowered Constructs</span>
        </div>

        <div className="provenance-search">
          <input
            type="text"
            className="filter-input"
            placeholder="Filter constructs or symbols..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
          />
        </div>
      </div>

      <div className="provenance-table-wrapper">
        <table className="provenance-table">
          <thead>
            <tr>
              <th>Construct</th>
              <th>Universal Concept</th>
              <th>Resolved Target Symbol</th>
              <th>Verification</th>
              <th>Pass Semantics</th>
              <th>Catalog Signature</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={6} className="provenance-empty">
                  {records.length === 0
                    ? "No lowering operations traced yet. Transpile a Python snippet above."
                    : "No constructs match the search filter."}
                </td>
              </tr>
            ) : (
              filtered.map((item, idx) => (
                <tr key={idx}>
                  <td className="provenance-construct">
                    <code>{item.construct}</code>
                  </td>
                  <td className="provenance-concept">
                    <span className="concept-tag">{item.concept_key}</span>
                  </td>
                  <td className="provenance-symbol">
                    <strong>{item.resolved_target}</strong>
                  </td>
                  <td>
                    <span
                      className={`badge ${item.verification_status === "verified" ? "badge-success" : "badge-cat"}`}
                    >
                      {item.verification_status}
                    </span>
                  </td>
                  <td>
                    {item.receiver_pass_kind ? (
                      <span className="badge badge-warn">{item.receiver_pass_kind}</span>
                    ) : (
                      "—"
                    )}
                  </td>
                  <td className="provenance-sig">
                    {item.catalog_signature ? (
                      <code>{item.catalog_signature}</code>
                    ) : (
                      <span className="sig-muted">Universal Template Binding</span>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
