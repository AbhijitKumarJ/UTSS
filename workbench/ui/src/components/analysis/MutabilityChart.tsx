import React from "react";
import { MutabilityItem } from "../../types";

interface MutabilityChartProps {
  mutability: MutabilityItem[];
}

export const MutabilityChart: React.FC<MutabilityChartProps> = ({ mutability }) => {
  return (
    <div className="analysis-card mutability-chart-card">
      <div className="card-header-row">
        <div>
          <h3 className="section-title">🔒 State Mutability & Safety Boundaries</h3>
          <p className="section-subtitle">
            Immutability guarantees across struct fields, class members, and package variables.
          </p>
        </div>
      </div>

      <div className="mutability-grid">
        {mutability.map(item => {
          const total = item.total_members || 1;
          const constPct = (item.constant_members / total) * 100;
          const immutPct = Math.max(0, item.immutability_pct - constPct);
          const mutPct = Math.max(0, 100 - item.immutability_pct);

          const isStrict = item.immutability_pct > 75;
          const isModerate = item.immutability_pct >= 40 && item.immutability_pct <= 75;

          return (
            <div key={item.language} className="mutability-item-card">
              <div className="mutability-card-top">
                <span className="lang-tag">{item.language.toUpperCase()}</span>
                <span
                  className={`badge ${isStrict ? "badge-success" : isModerate ? "badge-warn" : "badge-cat"}`}
                >
                  {isStrict ? "Default Immutable" : isModerate ? "Defensive / Mixed" : "Default Mutable"}
                </span>
              </div>

              <div className="mutability-stat-big">
                <span className="stat-number">{item.immutability_pct.toFixed(1)}%</span>
                <span className="stat-desc">Immutable State Members</span>
              </div>

              {/* Progress bar with Constant, Immutable, Mutable */}
              <div className="mutability-split-bar">
                {constPct > 0 && (
                  <div
                    className="split-segment const"
                    style={{ width: `${constPct}%` }}
                    title={`Constants: ${item.constant_members.toLocaleString()} (${constPct.toFixed(1)}%)`}
                  />
                )}
                {immutPct > 0 && (
                  <div
                    className="split-segment immut"
                    style={{ width: `${immutPct}%` }}
                    title={`Immutable Fields: ${item.immutable_members.toLocaleString()} (${immutPct.toFixed(1)}%)`}
                  />
                )}
                {mutPct > 0 && (
                  <div
                    className="split-segment mut"
                    style={{ width: `${mutPct}%` }}
                    title={`Mutable Fields: ${(total - item.immutable_members).toLocaleString()} (${mutPct.toFixed(1)}%)`}
                  />
                )}
              </div>

              <div className="mutability-card-counts">
                <span>Total: {item.total_members.toLocaleString()}</span>
                <span>Const: {item.constant_members.toLocaleString()}</span>
                <span>Immutable: {item.immutable_members.toLocaleString()}</span>
              </div>
            </div>
          );
        })}
      </div>

      <div className="mutability-legend">
        <div className="legend-item">
          <span className="legend-color-box const" />
          <span>Constants (Compile-time / Readonly)</span>
        </div>
        <div className="legend-item">
          <span className="legend-color-box immut" />
          <span>Immutable State (Rust `let`, C# `readonly`)</span>
        </div>
        <div className="legend-item">
          <span className="legend-color-box mut" />
          <span>Mutable State (Reassignable)</span>
        </div>
      </div>
    </div>
  );
};
