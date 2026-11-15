import React, { useState, useEffect } from "react";
import { CompilerPipelineResponse, TargetLanguage } from "../../types";
import { fetchCompilerPipeline } from "../../api";

interface CompilerPipelineStepperProps {
  pythonCode: string;
}

const TARGET_LANG_OPTIONS: Array<{ key: TargetLanguage; label: string; badge: string }> = [
  { key: "rust", label: "Rust 1.85", badge: "RS" },
  { key: "csharp", label: "C# .NET 10", badge: "C#" },
  { key: "typescript", label: "TypeScript", badge: "TS" },
  { key: "cpp", label: "C++20", badge: "C++" },
  { key: "go", label: "Go 1.24", badge: "GO" },
];

export const CompilerPipelineStepper: React.FC<CompilerPipelineStepperProps> = ({ pythonCode }) => {
  const [selectedLang, setSelectedLang] = useState<TargetLanguage>("rust");
  const [activePassIndex, setActivePassIndex] = useState<number>(0);
  const [pipelineData, setPipelineData] = useState<CompilerPipelineResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  const loadPipeline = async (code: string, lang: TargetLanguage) => {
    if (!code || !code.trim()) {
      setPipelineData(null);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await fetchCompilerPipeline(code, lang);
      setPipelineData(res);
    } catch (err: any) {
      setError(err.message || "Failed to execute compiler pipeline passes");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPipeline(pythonCode, selectedLang);
  }, [pythonCode, selectedLang]);

  const handleCopyCode = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  const currentPass = pipelineData?.passes[activePassIndex];

  return (
    <div className="compiler-pipeline-container">
      {/* Pipeline Header */}
      <div className="pipeline-header">
        <div className="pipeline-title-group">
          <h3 className="pipeline-title">⚙️ Classical 4-Pass Multi-Language Compiler Transformation Pipeline</h3>
          <p className="pipeline-subtitle">
            Inspect intermediate compiler states: from Python AST parsing, through semantic symbol binding and IR memory model normalization, to multi-target emission.
          </p>
        </div>

        {/* Target Language Switcher */}
        <div className="pipeline-target-group">
          <span className="control-label">Target Architecture:</span>
          <div className="pipeline-target-pills">
            {TARGET_LANG_OPTIONS.map(opt => (
              <button
                key={opt.key}
                type="button"
                className={`pipeline-lang-pill ${selectedLang === opt.key ? "active" : ""}`}
                onClick={() => setSelectedLang(opt.key)}
              >
                {opt.badge} {opt.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {error && (
        <div className="pipeline-error-banner">
          <span>⚠️ {error}</span>
          <button type="button" className="btn btn-icon btn-sm" onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {/* 4-Pass Stepper Navigation Bar */}
      <div className="pipeline-stepper-bar">
        {[
          { idx: 0, title: "Pass 1: Frontend AST", stage: "Frontend Syntax" },
          { idx: 1, title: "Pass 2: Semantic Analysis", stage: "Symbol Environment" },
          { idx: 2, title: "Pass 3: IR Memory Model", stage: "Middle-End IR" },
          { idx: 3, title: "Pass 4: Target Emission", stage: "Backend Codegen" }
        ].map(step => (
          <button
            key={step.idx}
            type="button"
            className={`stepper-step-btn ${activePassIndex === step.idx ? "active" : ""}`}
            onClick={() => setActivePassIndex(step.idx)}
          >
            <span className="step-num">{step.idx + 1}</span>
            <div className="step-meta">
              <span className="step-title">{step.title}</span>
              <span className="step-stage">{step.stage}</span>
            </div>
          </button>
        ))}
      </div>

      {loading && (
        <div className="pipeline-loading-overlay">
          <div className="spinner"></div>
          <span>Executing compiler transformation passes for {selectedLang.toUpperCase()}...</span>
        </div>
      )}

      {!loading && currentPass && (
        <div className="pipeline-pass-content">
          {/* Pass Summary Banner */}
          <div className="pass-summary-card">
            <div className="pass-summary-header">
              <span className="stage-pill">{currentPass.stage}</span>
              <h4>{currentPass.name}</h4>
            </div>
            <p className="pass-summary-text">{currentPass.summary}</p>
          </div>

          {/* Pass 1: Frontend AST Display */}
          {activePassIndex === 0 && (
            <div className="pass-view-grid">
              <div className="pass-metrics-card">
                <h5>Syntax Tree Metrics</h5>
                <div className="metric-row">
                  <span className="metric-name">Total AST Nodes:</span>
                  <span className="metric-val"><strong>{currentPass.metrics?.total_ast_nodes}</strong></span>
                </div>
                <div className="metric-row">
                  <span className="metric-name">Top-Level Statements:</span>
                  <span className="metric-val"><strong>{currentPass.metrics?.top_level_statements}</strong></span>
                </div>
                <div className="stmt-kinds-breakdown">
                  <span className="sub-label">Statement Kinds:</span>
                  <div className="breakdown-chips">
                    {Object.entries(currentPass.metrics?.statement_breakdown || {}).map(([k, count]: [string, any]) => (
                      <span key={k} className="chip chip-stmt">{k} ({count})</span>
                    ))}
                  </div>
                </div>
              </div>

              <div className="pass-artifact-card">
                <div className="artifact-header">
                  <h5>Raw Python Abstract Syntax Tree (ast.dump)</h5>
                </div>
                <pre className="ast-dump-pre">
                  <code>{currentPass.artifacts?.ast_dump}</code>
                </pre>
              </div>
            </div>
          )}

          {/* Pass 2: Semantic Analysis & Symbol Environment Binding */}
          {activePassIndex === 1 && (
            <div className="pass-view-semantic">
              <div className="semantic-metrics-strip">
                <div className="metric-pill">
                  <span className="pill-label">Bound Symbols:</span>
                  <span className="pill-val">{currentPass.metrics?.total_symbols}</span>
                </div>
                <div className="metric-pill">
                  <span className="pill-label">User Classes:</span>
                  <span className="pill-val">{currentPass.metrics?.user_classes_count}</span>
                </div>
                <div className="metric-pill">
                  <span className="pill-label">User Functions:</span>
                  <span className="pill-val">{currentPass.metrics?.user_functions_count}</span>
                </div>
              </div>

              <div className="symbol-table-wrapper">
                <table className="symbol-env-table">
                  <thead>
                    <tr>
                      <th>Identifier</th>
                      <th>Kind</th>
                      <th>Inferred Type</th>
                      <th>Universal Concept Key</th>
                      <th>Scope</th>
                      <th>Source Line</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(currentPass.artifacts?.symbol_table || []).map((sym: any, idx: number) => (
                      <tr key={idx}>
                        <td className="sym-name"><code>{sym.identifier}</code></td>
                        <td><span className="badge badge-kind">{sym.symbol_kind}</span></td>
                        <td className="sym-type"><code>{sym.inferred_type}</code></td>
                        <td><span className="badge badge-concept">⚡ {sym.concept_key}</span></td>
                        <td className="sym-scope">{sym.scope}</td>
                        <td className="sym-line">{sym.line ? `L${sym.line}` : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Pass 3: IR Memory Model & Mutability Analysis */}
          {activePassIndex === 2 && (
            <div className="pass-view-ir">
              <div className="ir-metrics-grid">
                <div className="ir-card">
                  <h5>Target Memory Architecture</h5>
                  <div className="ir-badge-large">
                    <code>{currentPass.metrics?.target_memory_model}</code>
                  </div>
                  <p className="ir-desc">
                    Hardware allocation model for <strong>{selectedLang.toUpperCase()}</strong> execution.
                  </p>
                </div>

                <div className="ir-card">
                  <h5>Receiver Passing Semantics</h5>
                  <div className="ir-badge-large">
                    <code>{currentPass.metrics?.receiver_pass_kind}</code>
                  </div>
                  <p className="ir-desc">
                    Passing contract applied to method invocations and mutating receivers.
                  </p>
                </div>

                <div className="ir-card">
                  <h5>Required Target Imports</h5>
                  <div className="imports-list">
                    {(currentPass.artifacts?.required_imports || []).length > 0 ? (
                      (currentPass.artifacts?.required_imports || []).map((imp: string) => (
                        <span key={imp} className="chip chip-import">{imp}</span>
                      ))
                    ) : (
                      <span className="text-muted">None (Built-in Prelude / Core)</span>
                    )}
                  </div>
                </div>
              </div>

              {/* Mutability Analysis Map */}
              <div className="mutability-analysis-card">
                <h5>Inferred Mutability & Binding Synthesizer</h5>
                <div className="mutability-grid">
                  {Object.entries(currentPass.artifacts?.mutability_map || {}).map(([id, info]: [string, any]) => (
                    <div key={id} className={`mut-item ${info.mutated ? "is-mut" : "is-const"}`}>
                      <span className="mut-id"><code>{id}</code></span>
                      <span className={`badge ${info.mutated ? "badge-mut" : "badge-const"}`}>
                        {info.mutated ? "MUTATED" : "IMMUTABLE"}
                      </span>
                      <span className="mut-target-binding">
                        Emits: <code>{info.binding_declaration} {id}</code>
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Compiler Impedance Notes */}
              {(currentPass.artifacts?.impedance_notes || []).length > 0 && (
                <div className="impedance-notes-card">
                  <h5>Compiler Impedance Notes for {selectedLang.toUpperCase()}</h5>
                  <ul className="notes-list">
                    {(currentPass.artifacts?.impedance_notes || []).map((note: string, idx: number) => (
                      <li key={idx}>💡 {note}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Pass 4: Backend Emission & Catalog Provenance */}
          {activePassIndex === 3 && (
            <div className="pass-view-codegen">
              <div className="codegen-split">
                <div className="codegen-left">
                  <div className="code-header-bar">
                    <h5>Synthesized {selectedLang.toUpperCase()} Output</h5>
                    <button
                      type="button"
                      className="btn btn-sm btn-outline"
                      onClick={() => handleCopyCode(currentPass.artifacts?.emitted_code || "")}
                    >
                      {copied ? "✓ Copied!" : "📋 Copy Code"}
                    </button>
                  </div>
                  <pre className="emitted-code-pre">
                    <code>{currentPass.artifacts?.emitted_code || "// No code emitted"}</code>
                  </pre>
                </div>

                <div className="codegen-right">
                  <h5>Catalog Provenance Trace ({currentPass.metrics?.provenance_trace_count} operations)</h5>
                  <div className="provenance-list-container">
                    {(currentPass.artifacts?.provenance_records || []).map((rec: any, idx: number) => (
                      <div key={idx} className="prov-item-card">
                        <div className="prov-top">
                          <span className="prov-construct"><code>{rec.construct}</code></span>
                          <span className="badge badge-verified">{rec.verification_status}</span>
                        </div>
                        <div className="prov-detail">
                          Concept: <code>{rec.concept_key}</code> → Target: <code>{rec.resolved_target}</code>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
