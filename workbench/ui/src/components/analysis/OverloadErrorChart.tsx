import React from "react";
import { OverloadingItem, ErrorHandlingItem } from "../../types";

interface OverloadErrorChartProps {
  overloading: OverloadingItem[];
  errorHandling: ErrorHandlingItem[];
}

export const OverloadErrorChart: React.FC<OverloadErrorChartProps> = ({
  overloading,
  errorHandling
}) => {
  return (
    <div className="overload-error-split-container">
      {/* 1. Overloading Multiplicity */}
      <div className="analysis-card split-col">
        <div className="card-header-row">
          <div>
            <h3 className="section-title">⚙️ Function Overload Multiplicity</h3>
            <p className="section-subtitle">
              Ad-hoc polymorphism vs zero-overload language design constraints.
            </p>
          </div>
        </div>

        <div className="overload-list">
          {overloading.map(item => {
            const ratio = item.total_callables > 0
              ? (item.overloaded_callables / item.total_callables) * 100
              : 0;

            const isZeroOverload = item.overloaded_callables === 0;

            return (
              <div key={item.language} className="overload-row">
                <div className="overload-lang-col">
                  <span className="lang-name">{item.language.toUpperCase()}</span>
                  <span className="overload-badge">
                    {isZeroOverload ? "Zero Overloads" : `Max: ${item.max_overload_multiplicity}×`}
                  </span>
                </div>

                <div className="overload-bar-track">
                  <div
                    className="overload-bar-fill"
                    style={{
                      width: `${Math.max(2, ratio)}%`,
                      backgroundColor: isZeroOverload
                        ? "var(--text-muted)"
                        : "var(--accent-primary, #6366f1)"
                    }}
                  />
                  <span className="overload-stat-text">
                    {item.overloaded_callables.toLocaleString()} / {item.total_callables.toLocaleString()} ({ratio.toFixed(1)}%)
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        <div className="transpiler-insight-banner">
          <strong>Transpiler Impact:</strong> Lowering from overloaded languages (C#, C++, TS) into Go or Rust requires name-mangling or Options structs, since functions cannot share the same identifier in the same namespace.
        </div>
      </div>

      {/* 2. Error Handling Paradigms */}
      <div className="analysis-card split-col">
        <div className="card-header-row">
          <div>
            <h3 className="section-title">🛡️ Error Handling Paradigms</h3>
            <p className="section-subtitle">
              Declared exception classes vs explicit error-returning callables (Result&lt;T,E&gt;, tuple error).
            </p>
          </div>
        </div>

        <div className="error-handling-list">
          {errorHandling.map(item => {
            const totalSignals = (item.exception_types_count + item.result_error_callables_count) || 1;
            const excPct = (item.exception_types_count / totalSignals) * 100;
            const resPct = (item.result_error_callables_count / totalSignals) * 100;

            const primaryModel = item.exception_types_count > item.result_error_callables_count
              ? "Exception Unwinding"
              : "Explicit Return Type (Result/Error)";

            return (
              <div key={item.language} className="error-row">
                <div className="error-lang-col">
                  <span className="lang-name">{item.language.toUpperCase()}</span>
                  <span className="model-label">{primaryModel}</span>
                </div>

                <div className="error-bar-track">
                  <div
                    className="error-fill exc"
                    style={{ width: `${excPct}%` }}
                    title={`Exceptions: ${item.exception_types_count.toLocaleString()}`}
                  />
                  <div
                    className="error-fill res"
                    style={{ width: `${resPct}%` }}
                    title={`Result/Error returns: ${item.result_error_callables_count.toLocaleString()}`}
                  />
                </div>

                <div className="error-stat-micro">
                  <span className="exc-tag">{item.exception_types_count.toLocaleString()} Exceptions</span>
                  <span className="res-tag">{item.result_error_callables_count.toLocaleString()} Result Callables</span>
                </div>
              </div>
            );
          })}
        </div>

        <div className="transpiler-insight-banner">
          <strong>Transpiler Impact:</strong> Exception models require translating `try/catch` into pattern-matching over `Result&lt;T, E&gt;` in Rust or `if err != nil` handling in Go.
        </div>
      </div>
    </div>
  );
};
