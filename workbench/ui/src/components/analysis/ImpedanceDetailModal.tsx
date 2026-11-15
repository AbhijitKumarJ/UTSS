import React from "react";
import { PairwiseImpedanceMatrix } from "../../types";

interface ImpedanceDetailModalProps {
  sourceLang: string;
  targetLang: string;
  score: number;
  onClose: () => void;
  onNavigateToPlayground?: (src: string, tgt: string) => void;
}

interface DimensionBreakdown {
  dimension: string;
  sourceTrait: string;
  targetTrait: string;
  penalty: string;
  severity: "low" | "medium" | "high";
  guidance: string;
}

export const ImpedanceDetailModal: React.FC<ImpedanceDetailModalProps> = ({
  sourceLang,
  targetLang,
  score,
  onClose,
  onNavigateToPlayground
}) => {
  const isSame = sourceLang === targetLang;

  // Compute domain-specific architectural recommendations
  const getBreakdowns = (): DimensionBreakdown[] => {
    if (isSame) {
      return [
        {
          dimension: "Identity Normalization",
          sourceTrait: `${sourceLang.toUpperCase()} AST`,
          targetTrait: `${targetLang.toUpperCase()} AST`,
          penalty: "0.00",
          severity: "low",
          guidance: "Identity AST lowering; no semantics or ABI translation required."
        }
      ];
    }

    const items: DimensionBreakdown[] = [];

    // 1. Memory & Ownership
    if ((sourceLang === "python" || sourceLang === "typescript") && targetLang === "rust") {
      items.push({
        dimension: "Memory & Ownership",
        sourceTrait: "Garbage-Collected / Reference-Counted Heap Objects",
        targetTrait: "Strict Affine Type System (Borrow Checker, &T / &mut T)",
        penalty: "High (+0.35)",
        severity: "high",
        guidance: "Transpiler must synthesize owned allocations (Box/Arc), determine clone boundaries, or generate lifetime annotations."
      });
    } else if (sourceLang === "rust" && (targetLang === "python" || targetLang === "typescript" || targetLang === "csharp")) {
      items.push({
        dimension: "Memory & Ownership",
        sourceTrait: "Explicit Borrow & Lifetime Annotations",
        targetTrait: "Managed Runtime with Garbage Collector",
        penalty: "Low (+0.08)",
        severity: "low",
        guidance: "Strip borrow qualifiers (&, &mut) and lifetime parameters ('a); allocate transparently on managed heap."
      });
    } else {
      items.push({
        dimension: "Memory & Ownership",
        sourceTrait: sourceLang === "cpp" ? "Manual / RAII / Value Semantics" : "Managed References",
        targetTrait: targetLang === "cpp" ? "Value Defaults with RAII" : "Runtime Managed",
        penalty: "Moderate (+0.15)",
        severity: "medium",
        guidance: "Align pointer/reference pass-by conventions and destructor lifecycle requirements."
      });
    }

    // 2. Function Overloads
    if ((sourceLang === "csharp" || sourceLang === "cpp") && (targetLang === "go" || targetLang === "rust")) {
      items.push({
        dimension: "Polymorphism & Overloads",
        sourceTrait: "Dense Static Method Overloading (Ad-hoc Polymorphism)",
        targetTrait: "Strict Zero-Overload Design (Single Function per Name)",
        penalty: "High (+0.25)",
        severity: "high",
        guidance: "Transpiler must synthesize unique suffixed identifiers (e.g. read_all, read_buffer) or generate tagged union/enum wrappers."
      });
    } else if ((sourceLang === "python" || sourceLang === "typescript") && (targetLang === "csharp" || targetLang === "cpp")) {
      items.push({
        dimension: "Polymorphism & Overloads",
        sourceTrait: "Optional / Default / Kwarg Parameters",
        targetTrait: "Nominal Static Overloads or Default Arguments",
        penalty: "Moderate (+0.12)",
        severity: "medium",
        guidance: "Decompose variable-arity signatures into discrete overloaded methods or C++ default argument syntax."
      });
    } else {
      items.push({
        dimension: "Polymorphism & Overloads",
        sourceTrait: "Standard signature matching",
        targetTrait: "Standard signature matching",
        penalty: "Low (+0.05)",
        severity: "low",
        guidance: "Direct 1:1 callable lowering with identical parameter arity."
      });
    }

    // 3. Error Handling
    if ((sourceLang === "python" || sourceLang === "csharp") && (targetLang === "rust" || targetLang === "go")) {
      items.push({
        dimension: "Error Handling Paradigms",
        sourceTrait: "Stack-Unwinding Exceptions (try/catch/raise)",
        targetTrait: targetLang === "rust" ? "Monadic Result<T, E> Propagation" : "Tuple Return (val, error) Checking",
        penalty: "High (+0.22)",
        severity: "high",
        guidance: targetLang === "rust"
          ? "Wrap callable return types into Result<T, TranspilerError> and append '?' operators at lowering sites."
          : "Rewrite signatures to return (T, error) and insert 'if err != nil { return nil, err }' guards."
      });
    } else if ((sourceLang === "rust" || sourceLang === "go") && (sourceLang !== targetLang)) {
      items.push({
        dimension: "Error Handling Paradigms",
        sourceTrait: "Explicit Return-Based Error Signatures",
        targetTrait: "Exception Throwing / Structured Handling",
        penalty: "Moderate (+0.10)",
        severity: "medium",
        guidance: "Unwrap Result/error checks and synthesize throw/raise statements on non-zero error states."
      });
    }

    // 4. Type System
    if (sourceLang === "python" && (targetLang === "rust" || targetLang === "cpp" || targetLang === "csharp" || targetLang === "go")) {
      items.push({
        dimension: "Type System Rigidity",
        sourceTrait: "Dynamic Duck Typing / Gradual Typing",
        targetTrait: "Static Nominal / Invariant Type Hierarchy",
        penalty: "High (+0.28)",
        severity: "high",
        guidance: "Requires type inference or .pyi stub overlay to infer concrete types; fallback to polymorphic Any / interface{} incurs runtime boxing overhead."
      });
    }

    return items;
  };

  const breakdowns = getBreakdowns();

  const getSeverityBadge = (s: "low" | "medium" | "high") => {
    switch (s) {
      case "low":
        return <span className="badge badge-success">Minimal Impedance</span>;
      case "medium":
        return <span className="badge badge-warn">Moderate Impedance</span>;
      case "high":
        return <span className="badge badge-danger">Severe Impedance</span>;
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card impedance-detail-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="impedance-pair-title">
            <span className="lang-tag source">{sourceLang.toUpperCase()}</span>
            <span className="pair-arrow">➔</span>
            <span className="lang-tag target">{targetLang.toUpperCase()}</span>
            <span className="impedance-score-pill">
              Impedance: <strong>{score.toFixed(3)}</strong> / 1.000
            </span>
          </div>
          <button className="modal-close-btn" onClick={onClose} title="Close">✕</button>
        </div>

        <div className="modal-body">
          <div className="impedance-meter-container">
            <div className="meter-label-row">
              <span>Transpiler Semantic Distance</span>
              <span>{(score * 100).toFixed(1)}% Divergence</span>
            </div>
            <div className="meter-track">
              <div
                className="meter-fill"
                style={{
                  width: `${Math.max(4, score * 100)}%`,
                  backgroundColor:
                    score < 0.25 ? "var(--accent-green, #10b981)" :
                    score < 0.55 ? "var(--accent-cyan, #06b6d4)" :
                    score < 0.80 ? "var(--accent-amber, #f59e0b)" : "var(--accent-danger, #ef4444)"
                }}
              />
            </div>
          </div>

          <div className="breakdown-list">
            <h4>Dimensional Architectural Breakdown</h4>
            {breakdowns.map((b, idx) => (
              <div key={idx} className="breakdown-item">
                <div className="breakdown-header">
                  <span className="dimension-name">{b.dimension}</span>
                  <div className="breakdown-meta">
                    <span className="penalty-tag">{b.penalty}</span>
                    {getSeverityBadge(b.severity)}
                  </div>
                </div>
                <div className="breakdown-comparison">
                  <div className="comp-col">
                    <span className="col-label">Source ({sourceLang}):</span>
                    <span className="col-value">{b.sourceTrait}</span>
                  </div>
                  <div className="comp-col">
                    <span className="col-label">Target ({targetLang}):</span>
                    <span className="col-value">{b.targetTrait}</span>
                  </div>
                </div>
                <div className="breakdown-guidance">
                  <strong>Transpiler Engine Action:</strong> {b.guidance}
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="modal-footer">
          {onNavigateToPlayground && !isSame && (
            <button
              className="btn btn-primary"
              onClick={() => {
                onClose();
                onNavigateToPlayground(sourceLang, targetLang);
              }}
            >
              🔄 Test in Rosetta Playground
            </button>
          )}
          <button className="btn btn-secondary" onClick={onClose}>
            Close Inspector
          </button>
        </div>
      </div>
    </div>
  );
};
