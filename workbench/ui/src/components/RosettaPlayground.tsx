import React, { useState, useEffect, useCallback } from "react";
import {
  BridgeConcept,
  BridgeLookupResponse,
  TranslateResponse
} from "../types";
import {
  fetchBridgeConcepts,
  fetchBridgeLookup,
  translateBridge
} from "../api";
import { TranspilationSandbox } from "./transpiler/TranspilationSandbox";
import { StdlibTaxonomyExplorer } from "./bridge/StdlibTaxonomyExplorer";
import { CustomRulePlayground } from "./bridge/CustomRulePlayground";

export const RosettaPlayground: React.FC = () => {
  const [subMode, setSubMode] = useState<"sandbox" | "matrix" | "taxonomy" | "custom_rules">("sandbox");
  const [concepts, setConcepts] = useState<BridgeConcept[]>([]);
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedConceptKey, setSelectedConceptKey] = useState<string>("collection.dynamic_array");
  const [lookupData, setLookupData] = useState<BridgeLookupResponse | null>(null);
  const [isLoadingLookup, setIsLoadingLookup] = useState<boolean>(false);

  // Transpiler Sandbox State
  const [sourceLang, setSourceLang] = useState<string>("python");
  const [targetLang, setTargetLang] = useState<string>("rust");
  const [selectedOp, setSelectedOp] = useState<string>("append");
  const [receiverName, setReceiverName] = useState<string>("items");
  const [keyVal, setKeyVal] = useState<string>("alice");
  const [argumentVal, setArgumentVal] = useState<string>("42");
  const [translation, setTranslation] = useState<TranslateResponse | null>(null);
  const [isTranslating, setIsTranslating] = useState<boolean>(false);

  // Load all concepts on mount
  useEffect(() => {
    async function loadConcepts() {
      try {
        const list = await fetchBridgeConcepts();
        setConcepts(list);
        if (list.length > 0 && !list.some(c => c.concept_key === selectedConceptKey)) {
          setSelectedConceptKey(list[0].concept_key);
        }
      } catch (err) {
        console.error("Failed to load bridge concepts:", err);
      }
    }
    loadConcepts();
  }, []);

  // Fetch lookup details when selectedConceptKey changes
  const loadConceptDetails = useCallback(async (key: string) => {
    if (!key) return;
    setIsLoadingLookup(true);
    try {
      const data = await fetchBridgeLookup(key);
      setLookupData(data);

      // Default selected op if available
      const ops = Object.keys(data.operation_mappings || {});
      if (ops.length > 0) {
        setSelectedOp(prev => (ops.includes(prev) ? prev : ops[0]));
        if (key.includes("map") && (receiverName === "items" || !receiverName)) {
          setReceiverName("cache");
        } else if (key.includes("array") && (receiverName === "cache" || !receiverName)) {
          setReceiverName("items");
        }
      } else {
        setSelectedOp("");
        setTranslation(null);
      }
    } catch (err) {
      console.error(`Failed to lookup concept ${key}:`, err);
    } finally {
      setIsLoadingLookup(false);
    }
  }, [receiverName]);

  useEffect(() => {
    if (selectedConceptKey) {
      loadConceptDetails(selectedConceptKey);
    }
  }, [selectedConceptKey, loadConceptDetails]);

  const availableOps = Object.keys(lookupData?.operation_mappings || {});
  const hasOperations = availableOps.length > 0;

  // Determine parameter requirements for the selected operation
  const selectedOpMappings = lookupData?.operation_mappings?.[selectedOp] || {};
  const templatesStr = Object.values(selectedOpMappings)
    .map(m => m.call_syntax_template)
    .join(" ");

  const needsKey = templatesStr.includes("{key}");
  const needsVal = templatesStr.includes("{val}");
  const needsItem = templatesStr.includes("{item}");
  const needsArgs = needsKey || needsVal || needsItem;

  // Trigger translation
  const runTranslation = useCallback(async () => {
    if (!selectedConceptKey || !selectedOp || !hasOperations) {
      setTranslation(null);
      return;
    }
    setIsTranslating(true);
    try {
      const argsList: string[] = [];
      if (needsKey && needsVal) {
        argsList.push(keyVal || "key", argumentVal || "val");
      } else if (needsKey) {
        argsList.push(keyVal || "key");
      } else if (needsItem) {
        argsList.push(argumentVal || "42");
      }

      const defaultReceiver = selectedConceptKey.includes("map") ? "cache" : "items";
      const res = await translateBridge({
        source_language: sourceLang,
        target_language: targetLang,
        concept_key: selectedConceptKey,
        canonical_op: selectedOp,
        receiver: receiverName || defaultReceiver,
        args: argsList
      });
      setTranslation(res);
    } catch (err) {
      console.error("Translation error:", err);
    } finally {
      setIsTranslating(false);
    }
  }, [
    selectedConceptKey,
    selectedOp,
    hasOperations,
    sourceLang,
    targetLang,
    receiverName,
    keyVal,
    argumentVal,
    needsKey,
    needsVal,
    needsItem
  ]);

  useEffect(() => {
    if (selectedConceptKey && lookupData && hasOperations && selectedOp) {
      runTranslation();
    } else {
      setTranslation(null);
    }
  }, [runTranslation, selectedConceptKey, lookupData, hasOperations, selectedOp]);

  const categories = ["all", "collection", "primitive", "control_flow", "exception", "io", "protocol"];
  const filteredConcepts = selectedCategory === "all"
    ? concepts
    : concepts.filter(c => c.category === selectedCategory);

  const languages = ["python", "csharp", "cpp", "go", "rust", "typescript"];

  return (
    <div className="rosetta-playground">
      {/* Sub-mode Navigation Bar */}
      <div className="rosetta-subnav-bar">
        <div className="submode-switcher">
          <button
            className={`submode-btn ${subMode === "sandbox" ? "active" : ""}`}
            onClick={() => setSubMode("sandbox")}
            type="button"
          >
            🚀 AST Transpiler Sandbox
          </button>
          <button
            className={`submode-btn ${subMode === "matrix" ? "active" : ""}`}
            onClick={() => setSubMode("matrix")}
            type="button"
          >
            🗂️ Universal Concept Matrix & Crosswalk
          </button>
          <button
            className={`submode-btn ${subMode === "taxonomy" ? "active" : ""}`}
            onClick={() => setSubMode("taxonomy")}
            type="button"
          >
            📚 Stdlib Universe Explorer & Coverage Matrix
          </button>
          <button
            className={`submode-btn ${subMode === "custom_rules" ? "active" : ""}`}
            onClick={() => setSubMode("custom_rules")}
            type="button"
          >
            🧪 Custom Rule Playground & Impedance Tester
          </button>
        </div>
      </div>

      {subMode === "sandbox" ? (
        <TranspilationSandbox />
      ) : subMode === "taxonomy" ? (
        <StdlibTaxonomyExplorer />
      ) : subMode === "custom_rules" ? (
        <CustomRulePlayground />
      ) : (
        <>
          <div className="playground-header">
            <div className="playground-title-row">
              <span className="badge badge-purple">UNIVERSAL TRANSPILATION BRIDGE</span>
              <h2>Universal Bridge & Rosetta Transpiler Playground</h2>
            </div>
            <p className="playground-desc">
              Empirical 6-language crosswalk linking high-level compiler Intermediate Representation (IR) concepts,
              memory models, and method signatures across <strong>Python</strong>, <strong>C#</strong>, <strong>C++</strong>, <strong>Go</strong>, <strong>Rust</strong>, and <strong>TypeScript</strong>.
            </p>
          </div>

      {/* Category Filter & Concept Selector */}
      <div className="concept-toolbar">
        <div className="category-chips">
          {categories.map(cat => (
            <button
              key={cat}
              className={`chip-btn ${selectedCategory === cat ? "active" : ""}`}
              onClick={() => {
                setSelectedCategory(cat);
                const matching = cat === "all" ? concepts : concepts.filter(c => c.category === cat);
                if (matching.length > 0 && !matching.some(c => c.concept_key === selectedConceptKey)) {
                  setSelectedConceptKey(matching[0].concept_key);
                }
              }}
            >
              {cat.replace("_", " ").toUpperCase()}
            </button>
          ))}
        </div>

        <div className="concept-selector">
          <label htmlFor="concept-select">Canonical IR Concept:</label>
          <select
            id="concept-select"
            className="concept-dropdown"
            value={selectedConceptKey}
            onChange={(e) => setSelectedConceptKey(e.target.value)}
          >
            {filteredConcepts.map(c => (
              <option key={c.concept_key} value={c.concept_key}>
                {c.concept_key} ({c.description})
              </option>
            ))}
          </select>
        </div>
      </div>

      {isLoadingLookup ? (
        <div className="loading-spinner">Loading empirical bridge mappings...</div>
      ) : lookupData ? (
        <>
          {/* Section 1: 6-Language Rosetta Parity Matrix */}
          <section className="matrix-section">
            <h3 className="section-title">
              <span className="icon">🏛️</span> 6-Language Universal Type Crosswalk
            </h3>
            <div className="matrix-grid">
              {languages.map(lang => {
                const typeMap = lookupData.type_mappings[lang];
                return (
                  <div key={lang} className={`matrix-card lang-${lang}`}>
                    <div className="card-header">
                      <span className="lang-tag">{lang.toUpperCase()}</span>
                      {typeMap && (
                        <span className={`status-badge status-${typeMap.verification_status}`}>
                          {typeMap.verification_status.replace("_", " ")}
                        </span>
                      )}
                    </div>

                    {typeMap ? (
                      <div className="card-body">
                        <div className="template-box">
                          <code>{typeMap.type_syntax_template}</code>
                        </div>

                        <div className="prop-row">
                          <span className="prop-label">Memory:</span>
                          <span className="prop-pill pill-memory">{typeMap.memory_model}</span>
                        </div>

                        <div className="prop-row">
                          <span className="prop-label">Nullability:</span>
                          <span className="prop-pill pill-null">{typeMap.nullability_model}</span>
                        </div>

                        {typeMap.required_import && (
                          <div className="prop-row import-row">
                            <span className="prop-label">Import:</span>
                            <span className="import-val"><code>{typeMap.required_import}</code></span>
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="card-body empty-body">No mapping registered</div>
                    )}
                  </div>
                );
              })}
            </div>
          </section>

          {/* Section 2: Canonical Operation & Call-Syntax Crosswalk Simulator (Only for concepts with registered operations) */}
          {hasOperations ? (
            <section className="sandbox-section">
              <div className="section-title-wrap">
                <h3 className="section-title">
                  <span className="icon">⚡</span> Canonical Operation & Call-Syntax Crosswalk Simulator
                </h3>
                <span className="section-subtitle">
                  Test how atomic methods ({selectedOp}) lower across languages with your variable names.
                </span>
              </div>

              <div className="sandbox-controls">
                <div className="control-group">
                  <label>Source Language:</label>
                  <select value={sourceLang} onChange={(e) => setSourceLang(e.target.value)}>
                    {languages.map(l => (
                      <option key={l} value={l}>{l.toUpperCase()}</option>
                    ))}
                  </select>
                </div>

                <div className="control-arrow">➔</div>

                <div className="control-group">
                  <label>Target Language:</label>
                  <select value={targetLang} onChange={(e) => setTargetLang(e.target.value)}>
                    {languages.map(l => (
                      <option key={l} value={l}>{l.toUpperCase()}</option>
                    ))}
                  </select>
                </div>

                <div className="control-group">
                  <label>Canonical Operation:</label>
                  <select value={selectedOp} onChange={(e) => setSelectedOp(e.target.value)}>
                    {availableOps.map(op => (
                      <option key={op} value={op}>{op}</option>
                    ))}
                  </select>
                </div>

                <div className="control-group">
                  <label title="Variable name in your source code">
                    Variable Name:
                  </label>
                  <input
                    type="text"
                    value={receiverName}
                    onChange={(e) => setReceiverName(e.target.value)}
                    placeholder={selectedConceptKey.includes("map") ? "cache" : "items"}
                  />
                </div>

                {needsKey && (
                  <div className="control-group">
                    <label>Key Identifier:</label>
                    <input
                      type="text"
                      value={keyVal}
                      onChange={(e) => setKeyVal(e.target.value)}
                      placeholder="alice"
                    />
                  </div>
                )}

                {(needsItem || (needsKey && needsVal)) && (
                  <div className="control-group">
                    <label>{needsVal ? "Value Expression:" : "Item Value:"}</label>
                    <input
                      type="text"
                      value={argumentVal}
                      onChange={(e) => setArgumentVal(e.target.value)}
                      placeholder={needsVal ? "100" : "42"}
                    />
                  </div>
                )}

                {!needsArgs && (
                  <div className="control-group zero-arg-badge-group">
                    <label>Arguments:</label>
                    <div className="zero-arg-pill">Zero-argument method ()</div>
                  </div>
                )}
              </div>

              {/* Translation Output Panels */}
              {translation && (
                <div className="translation-display">
                  <div className="code-panels-row">
                    <div className="code-panel source-panel">
                      <div className="panel-bar">
                        <span className="bar-tag">SOURCE: {sourceLang.toUpperCase()}</span>
                      </div>
                      <pre className="code-block">
                        <code>{translation.source_expression}</code>
                      </pre>
                    </div>

                    <div className="code-panels-divider">➔</div>

                    <div className="code-panel target-panel">
                      <div className="panel-bar">
                        <span className="bar-tag">SYNTHESIZED TARGET: {targetLang.toUpperCase()}</span>
                        <span className="pass-kind-tag">{translation.receiver_pass_kind}</span>
                      </div>
                      <pre className="code-block">
                        <code>{translation.target_expression}</code>
                      </pre>
                    </div>
                  </div>

                  {/* Impedance and Guidance Card */}
                  <div className="impedance-guidance-card">
                    <div className="guidance-header">
                      <span className="badge badge-warning">TRANSPILER IMPEDANCE & SAFETY GUIDANCE</span>
                    </div>
                    <p className="guidance-text">{translation.impedance_note}</p>
                    <div className="guidance-meta">
                      <span><strong>Target Type:</strong> <code>{translation.target_type}</code></span>
                      <span><strong>Memory Model:</strong> <code>{translation.memory_model}</code></span>
                      {translation.required_import && (
                        <span><strong>Required Module:</strong> <code>{translation.required_import}</code></span>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </section>
          ) : (
            <div className="ast-sandbox-hint-banner">
              <div className="hint-content">
                <span className="hint-icon">🚀</span>
                <div className="hint-text">
                  <strong>Multi-Statement / Block Construct: {lookupData.concept.concept_key}</strong>
                  <p>
                    Control-flow patterns (branching, loops), error-handling paradigms (<code>raise</code>, <code>Result&lt;T, E&gt;</code>),
                    and context managers (<code>with open(...)</code>) cannot be reduced to single-expression method templates.
                    Synthesize them as complete programs with full AST lowering in the <strong>AST Transpiler Sandbox</strong>.
                  </p>
                </div>
              </div>
              <button
                type="button"
                className="hint-action-btn"
                onClick={() => setSubMode("sandbox")}
              >
                Open in AST Transpiler Sandbox ➔
              </button>
            </div>
          )}
        </>
      ) : null}
        </>
      )}
    </div>
  );
};
