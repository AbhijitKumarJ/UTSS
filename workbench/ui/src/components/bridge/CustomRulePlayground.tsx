import React, { useState, useEffect } from "react";
import Editor from "@monaco-editor/react";
import {
  CustomRuleTestRequest,
  CustomRuleTestResponse,
  TargetLanguage
} from "../../types";
import { testCustomTranspilationRule } from "../../api";
import { useTheme } from "../../context/ThemeContext";

interface RulePreset {
  title: string;
  rule: CustomRuleTestRequest;
}

const RULE_PRESETS: RulePreset[] = [
  {
    title: "1. Rust: Custom FastBuffer with push_fast() (Zero-Cost Heap)",
    rule: {
      rule_name: "FastBufferRule",
      target_language: "rust",
      base_concept_key: "collection.dynamic_array",
      target_type_name: "FastBuffer",
      type_syntax_template: "FastBuffer<{T}>",
      required_import: "my_crate::collections::FastBuffer",
      memory_model: "owned_heap",
      nullability_model: "value_default",
      custom_operations: {
        append: "{receiver}.push_fast({item})"
      },
      python_code: "items: list[int] = []\nitems.append(42)\nitems.append(99)"
    }
  },
  {
    title: "2. C#: ThreadSafe SynchronizedCollection with AddSafe()",
    rule: {
      rule_name: "ConcurrentListRule",
      target_language: "csharp",
      base_concept_key: "collection.dynamic_array",
      target_type_name: "SynchronizedCollection",
      type_syntax_template: "SynchronizedCollection<{T}>",
      required_import: "System.Collections.Generic",
      memory_model: "ref_gc",
      nullability_model: "nullable_ref",
      custom_operations: {
        append: "{receiver}.AddSafe({item})"
      },
      python_code: "tasks: list[int] = []\ntasks.append(1001)"
    }
  },
  {
    title: "3. Go: FastRingBuffer with Enqueue() (Escape-Analyzed Heap)",
    rule: {
      rule_name: "RingBufferRule",
      target_language: "go",
      base_concept_key: "collection.fifo_queue",
      target_type_name: "RingBuffer",
      type_syntax_template: "*ring.RingBuffer[{T}]",
      required_import: "container/ring",
      memory_model: "slice_header",
      nullability_model: "value_default",
      custom_operations: {
        append: "{receiver}.Enqueue({item})"
      },
      python_code: "q: list[int] = []\nq.append(77)"
    }
  },
  {
    title: "4. C++: LLVM SmallVector with push_back() (RAII)",
    rule: {
      rule_name: "SmallVectorRule",
      target_language: "cpp",
      base_concept_key: "collection.dynamic_array",
      target_type_name: "llvm::SmallVector",
      type_syntax_template: "llvm::SmallVector<{T}, 16>",
      required_import: "llvm/ADT/SmallVector.h",
      memory_model: "raii_value",
      nullability_model: "value_default",
      custom_operations: {
        append: "{receiver}.push_back({item})"
      },
      python_code: "items: list[int] = []\nitems.append(128)"
    }
  }
];

export const CustomRulePlayground: React.FC = () => {
  const { monacoTheme } = useTheme();

  const [ruleName, setRuleName] = useState<string>(RULE_PRESETS[0].rule.rule_name);
  const [targetLang, setTargetLang] = useState<TargetLanguage>("rust");
  const [baseConcept, setBaseConcept] = useState<string>(RULE_PRESETS[0].rule.base_concept_key);
  const [targetTypeName, setTargetTypeName] = useState<string>(RULE_PRESETS[0].rule.target_type_name);
  const [typeTemplate, setTypeTemplate] = useState<string>(RULE_PRESETS[0].rule.type_syntax_template);
  const [requiredImport, setRequiredImport] = useState<string>(RULE_PRESETS[0].rule.required_import || "");
  const [memoryModel, setMemoryModel] = useState<string>(RULE_PRESETS[0].rule.memory_model);
  const [nullabilityModel, setNullabilityModel] = useState<string>(RULE_PRESETS[0].rule.nullability_model);
  const [opName, setOpName] = useState<string>("append");
  const [opTemplate, setOpTemplate] = useState<string>("{receiver}.push_fast({item})");

  const [pythonCode, setPythonCode] = useState<string>(RULE_PRESETS[0].rule.python_code);
  const [result, setResult] = useState<CustomRuleTestResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const applyPreset = (preset: RulePreset) => {
    setRuleName(preset.rule.rule_name);
    setTargetLang(preset.rule.target_language as TargetLanguage);
    setBaseConcept(preset.rule.base_concept_key);
    setTargetTypeName(preset.rule.target_type_name);
    setTypeTemplate(preset.rule.type_syntax_template);
    setRequiredImport(preset.rule.required_import || "");
    setMemoryModel(preset.rule.memory_model);
    setNullabilityModel(preset.rule.nullability_model);
    setPythonCode(preset.rule.python_code);

    const ops = Object.entries(preset.rule.custom_operations);
    if (ops.length > 0) {
      setOpName(ops[0][0]);
      setOpTemplate(ops[0][1]);
    }
  };

  const handleRunTest = async () => {
    if (!pythonCode.trim()) return;
    setLoading(true);
    setError(null);
    try {
      const customOps: Record<string, string> = {};
      if (opName.trim() && opTemplate.trim()) {
        customOps[opName.trim()] = opTemplate.trim();
      }

      const res = await testCustomTranspilationRule({
        python_code: pythonCode,
        target_language: targetLang,
        rule_name: ruleName,
        base_concept_key: baseConcept,
        target_type_name: targetTypeName,
        type_syntax_template: typeTemplate,
        required_import: requiredImport.trim() || undefined,
        memory_model: memoryModel,
        nullability_model: nullabilityModel,
        custom_operations: customOps
      });
      setResult(res);
    } catch (err: any) {
      setError(err.message || "Failed to execute custom rule test");
    } finally {
      setLoading(false);
    }
  };

  // Run initial test
  useEffect(() => {
    handleRunTest();
  }, [targetLang]);

  return (
    <div className="custom-rule-playground">
      {/* Playground Header */}
      <div className="rule-header">
        <div className="rule-title-group">
          <h3 className="rule-title">🧪 Custom Transpilation Rule Playground & Empirical Impedance Tester</h3>
          <p className="rule-subtitle">
            Define custom syntax templates, memory models, and lowering operations. Test against Python ASTs and verify
            cross-language impedance scores in real-time before database ingestion.
          </p>
        </div>

        {/* Presets dropdown */}
        <div className="rule-presets-wrapper">
          <label className="toolbar-label">Rule Presets:</label>
          <select
            className="db-dropdown preset-dropdown"
            onChange={(e) => {
              const idx = parseInt(e.target.value, 10);
              if (!isNaN(idx) && RULE_PRESETS[idx]) {
                applyPreset(RULE_PRESETS[idx]);
              }
            }}
          >
            {RULE_PRESETS.map((p, idx) => (
              <option key={idx} value={idx}>
                {p.title}
              </option>
            ))}
          </select>
        </div>
      </div>

      {error && (
        <div className="rule-error-banner">
          <span>⚠️ {error}</span>
          <button type="button" className="btn btn-icon btn-sm" onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {/* Main 3-Column Layout */}
      <div className="rule-workspace-grid">
        {/* Column 1: Rule Form */}
        <div className="rule-form-pane">
          <div className="pane-header">
            <span className="pane-title">🛠️ Rule Configuration</span>
            <span className="badge badge-purple">{targetLang.toUpperCase()}</span>
          </div>

          <div className="rule-form-body">
            <div className="form-group">
              <label className="form-label">Rule Identifier:</label>
              <input
                type="text"
                className="form-input"
                value={ruleName}
                onChange={(e) => setRuleName(e.target.value)}
              />
            </div>

            <div className="form-row">
              <div className="form-group flex-1">
                <label className="form-label">Target Architecture:</label>
                <select
                  className="form-select"
                  value={targetLang}
                  onChange={(e) => setTargetLang(e.target.value as TargetLanguage)}
                >
                  <option value="rust">Rust 1.85 (Cargo)</option>
                  <option value="csharp">C# .NET 10</option>
                  <option value="go">Go 1.24</option>
                  <option value="typescript">TypeScript</option>
                  <option value="cpp">C++20 (CMake)</option>
                </select>
              </div>

              <div className="form-group flex-1">
                <label className="form-label">Base Concept Key:</label>
                <select
                  className="form-select"
                  value={baseConcept}
                  onChange={(e) => setBaseConcept(e.target.value)}
                >
                  <option value="collection.dynamic_array">collection.dynamic_array</option>
                  <option value="collection.hash_map">collection.hash_map</option>
                  <option value="collection.hash_set">collection.hash_set</option>
                  <option value="collection.fifo_queue">collection.fifo_queue</option>
                  <option value="io.file_handle">io.file_handle</option>
                </select>
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Custom Target Type Name:</label>
              <input
                type="text"
                className="form-input"
                value={targetTypeName}
                onChange={(e) => setTargetTypeName(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Type Syntax Template (use {'{T}'}, {'{K}'}, {'{V}'}):</label>
              <input
                type="text"
                className="form-input font-code"
                value={typeTemplate}
                onChange={(e) => setTypeTemplate(e.target.value)}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Required Import (use / namespace):</label>
              <input
                type="text"
                className="form-input font-code"
                placeholder="e.g. crate::collections::FastBuffer"
                value={requiredImport}
                onChange={(e) => setRequiredImport(e.target.value)}
              />
            </div>

            <div className="form-row">
              <div className="form-group flex-1">
                <label className="form-label">Memory Model:</label>
                <select
                  className="form-select"
                  value={memoryModel}
                  onChange={(e) => setMemoryModel(e.target.value)}
                >
                  <option value="owned_heap">owned_heap (Affine Ownership)</option>
                  <option value="ref_gc">ref_gc (Tracing Garbage Collection)</option>
                  <option value="slice_header">slice_header (Slice / Value Header)</option>
                  <option value="raii_value">raii_value (C++ RAII Stack/Heap)</option>
                </select>
              </div>

              <div className="form-group flex-1">
                <label className="form-label">Nullability Model:</label>
                <select
                  className="form-select"
                  value={nullabilityModel}
                  onChange={(e) => setNullabilityModel(e.target.value)}
                >
                  <option value="value_default">value_default</option>
                  <option value="nullable_ref">nullable_ref</option>
                  <option value="option_enum">option_enum</option>
                </select>
              </div>
            </div>

            <div className="form-section-divider">
              <span>Custom Method Call Lowering</span>
            </div>

            <div className="form-row">
              <div className="form-group" style={{ width: "110px" }}>
                <label className="form-label">Op Name:</label>
                <input
                  type="text"
                  className="form-input"
                  value={opName}
                  onChange={(e) => setOpName(e.target.value)}
                />
              </div>
              <div className="form-group flex-1">
                <label className="form-label">Call Template (e.g. {'{receiver}.push_fast({item})'}):</label>
                <input
                  type="text"
                  className="form-input font-code"
                  value={opTemplate}
                  onChange={(e) => setOpTemplate(e.target.value)}
                />
              </div>
            </div>

            <button
              type="button"
              className="btn btn-primary btn-block"
              onClick={handleRunTest}
              disabled={loading}
            >
              {loading ? "⚡ Verifying..." : "🚀 Test Lowering & Evaluate Impedance"}
            </button>
          </div>
        </div>

        {/* Column 2: Python Test Code */}
        <div className="rule-code-pane">
          <div className="pane-header">
            <span className="pane-title">🐍 Python Test Snippet</span>
            <span className="badge badge-blue">Input</span>
          </div>

          <div className="monaco-wrapper">
            <Editor
              height="100%"
              language="python"
              theme={monacoTheme}
              value={pythonCode}
              onChange={(val) => setPythonCode(val || "")}
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                fontFamily: "var(--font-code, monospace)",
                lineNumbers: "on",
                scrollBeyondLastLine: false,
                automaticLayout: true,
                tabSize: 4
              }}
            />
          </div>
        </div>

        {/* Column 3: Synthesized Output & Impedance Report */}
        <div className="rule-results-pane">
          <div className="pane-header">
            <span className="pane-title">🎯 Synthesized Target & Impedance Radar</span>
            {result && (
              <span className={`risk-pill risk-${result.impedance_risk.toLowerCase()}`}>
                Score: {result.impedance_score}/100 ({result.impedance_risk} Risk)
              </span>
            )}
          </div>

          <div className="results-pane-body">
            {/* Emitted Code */}
            <div className="emitted-box">
              <span className="box-label">Lowered Source Code ({targetLang}):</span>
              <pre className="code-pre">
                <code>{result?.emitted_code || "// Click 'Test Lowering' to synthesize code"}</code>
              </pre>
            </div>

            {/* Impedance Breakdown */}
            {result && (
              <div className="impedance-breakdown-card">
                <span className="box-label">Empirical Impedance Verification Factors:</span>

                <div className="factors-bars">
                  <div className="factor-row">
                    <span className="factor-name">Memory Safety</span>
                    <div className="factor-bar-bg">
                      <div
                        className="factor-bar-fill fill-green"
                        style={{ width: `${(result.score_factors.memory_safety / 30) * 100}%` }}
                      />
                    </div>
                    <span className="factor-val">{result.score_factors.memory_safety} / 30</span>
                  </div>

                  <div className="factor-row">
                    <span className="factor-name">Mutability Contract</span>
                    <div className="factor-bar-bg">
                      <div
                        className="factor-bar-fill fill-blue"
                        style={{ width: `${(result.score_factors.mutability_contract / 25) * 100}%` }}
                      />
                    </div>
                    <span className="factor-val">{result.score_factors.mutability_contract} / 25</span>
                  </div>

                  <div className="factor-row">
                    <span className="factor-name">Import Resolution</span>
                    <div className="factor-bar-bg">
                      <div
                        className="factor-bar-fill fill-purple"
                        style={{ width: `${(result.score_factors.import_resolution / 20) * 100}%` }}
                      />
                    </div>
                    <span className="factor-val">{result.score_factors.import_resolution} / 20</span>
                  </div>

                  <div className="factor-row">
                    <span className="factor-name">Template Integrity</span>
                    <div className="factor-bar-bg">
                      <div
                        className="factor-bar-fill fill-amber"
                        style={{ width: `${(result.score_factors.template_integrity / 25) * 100}%` }}
                      />
                    </div>
                    <span className="factor-val">{result.score_factors.template_integrity} / 25</span>
                  </div>
                </div>

                {/* Diagnostics List */}
                <div className="diagnostics-box">
                  <span className="box-label">Compiler & Semantics Diagnostics:</span>
                  <ul className="diag-list">
                    {result.diagnostics.map((diag, i) => (
                      <li key={i} className="diag-item">
                        {diag.includes("zero impedance") ? "✅ " : "⚠️ "}
                        {diag}
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
