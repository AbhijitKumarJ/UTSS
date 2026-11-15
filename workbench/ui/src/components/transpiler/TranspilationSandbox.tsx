import React, { useState, useEffect, useCallback, useRef } from "react";
import Editor, { OnMount } from "@monaco-editor/react";
import { TargetLanguage, TranspileSnippetResponse, TargetSynthesisOutput } from "../../types";
import { transpileSnippet, exportProjectScaffold, downloadBlob } from "../../api";
import { useTheme } from "../../context/ThemeContext";
import { ProvenanceInspector } from "./ProvenanceInspector";
import { AstFlowVisualizer } from "./AstFlowVisualizer";
import { CompilerPipelineStepper } from "./CompilerPipelineStepper";

const LANGUAGE_META: Record<
  TargetLanguage,
  { label: string; monacoLang: string; badge: string }
> = {
  csharp: { label: "C# .NET", monacoLang: "csharp", badge: "C#" },
  rust: { label: "Rust", monacoLang: "rust", badge: "RS" },
  typescript: { label: "TypeScript", monacoLang: "typescript", badge: "TS" },
  cpp: { label: "C++20", monacoLang: "cpp", badge: "C++" },
  go: { label: "Go", monacoLang: "go", badge: "GO" },
};

const PRESETS: Record<string, { title: string; code: string }> = {
  full_rosetta: {
    title: "1. Full Rosetta Suite (Collections, I/O & Exceptions)",
    code: `items: list[int] = []
items.append(42)
count = len(items)

scores: dict[str, int] = {}
scores["alice"] = 100
has_alice = "alice" in scores

with open("audit.log") as f:
    chunk = f.read(1024)

raise ValueError("invalid audit state")`,
  },
  sequences_maps_sets: {
    title: "2. Generic Sequences, Maps & Hash Sets",
    code: `ids: list[int] = []
ids.append(101)
ids.append(202)
last_id = ids.pop()
ids.clear()

seen: set[str] = set()
seen.add("token_a")
has_token = "token_a" in seen`,
  },
  control_flow_loops: {
    title: "3. Control Flow & Looping (for, while, if/else)",
    code: `total = 0
numbers: list[int] = []
numbers.append(10)
numbers.append(20)

for n in numbers:
    if n > 15:
        total = total + n
    else:
        total = total - n

while total > 0:
    total = total - 5`,
  },
  function_signatures: {
    title: "4. Function Signatures & Return Types",
    code: `def multiply(a: int, b: int) -> int:
    return a * b

def is_positive(val: int) -> bool:
    if val > 0:
        return True
    return False

result = multiply(6, 7)
flag = is_positive(result)`,
  },
  classes_and_objects: {
    title: "5. OOP: Classes, Structs & Methods",
    code: `class User:
    id: int
    name: str
    is_active: bool

class Counter:
    count: int

    def increment(self, step: int) -> int:
        self.count = self.count + step
        return self.count

user = User(1, "Alice", True)
c = Counter(0)
new_count = c.increment(5)`,
  },
  error_recovery_try_finally: {
    title: "6. Error Recovery (try / except / finally)",
    code: `try:
    items: list[int] = []
    val = items[0]
except IndexError as err:
    val = -1
finally:
    items.clear()`,
  },
};

export const TranspilationSandbox: React.FC = () => {
  const { monacoTheme } = useTheme();
  const [selectedPreset, setSelectedPreset] = useState<string>("full_rosetta");
  const [pythonCode, setPythonCode] = useState<string>(PRESETS.full_rosetta.code);
  const [activeTarget, setActiveTarget] = useState<TargetLanguage>("rust");
  const [transpileResult, setTranspileResult] = useState<TranspileSnippetResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [showProvenance, setShowProvenance] = useState<boolean>(true);
  const [sandboxMode, setSandboxMode] = useState<"generator" | "ast_flow" | "pipeline">("generator");
  const [isExporting, setIsExporting] = useState<boolean>(false);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);

  const handleExportProject = async (targetLang: string) => {
    if (!pythonCode.trim()) return;
    setIsExporting(true);
    setError(null);
    try {
      const blob = await exportProjectScaffold(pythonCode, targetLang);
      const filename = targetLang === "all" ? "rosetta_multilang_suite.zip" : `rosetta_${targetLang}_project.zip`;
      downloadBlob(blob, filename);
      setExportSuccess(`Scaffold ready: ${filename}`);
      setTimeout(() => setExportSuccess(null), 3500);
    } catch (err: any) {
      setError(err.message || "Failed to download project scaffold");
    } finally {
      setIsExporting(false);
    }
  };

  const runTranspile = useCallback(async (codeToRun: string) => {
    if (!codeToRun.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await transpileSnippet(codeToRun);
      setTranspileResult(res);
    } catch (err: any) {
      console.error("Transpilation failed:", err);
      setError(err.message || "Failed to transpile snippet");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial transpile on mount
  const initialRunDone = useRef(false);
  useEffect(() => {
    if (!initialRunDone.current) {
      initialRunDone.current = true;
      runTranspile(pythonCode);
    }
  }, [runTranspile, pythonCode]);

  const handleSelectPreset = (key: string) => {
    setSelectedPreset(key);
    const code = PRESETS[key]?.code || "";
    setPythonCode(code);
    runTranspile(code);
  };

  const handleCopyTarget = () => {
    const currentCode = transpileResult?.targets[activeTarget]?.source_code || "";
    if (navigator?.clipboard?.writeText && currentCode) {
      navigator.clipboard.writeText(currentCode).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      });
    }
  };

  const handleEditorMount: OnMount = (editor, monaco) => {
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      runTranspile(editor.getValue());
    });
  };

  const activeOutput: TargetSynthesisOutput | undefined = transpileResult?.targets[activeTarget];
  const provenanceRecords = activeOutput?.provenance_trace || [];

  return (
    <div className="transpiler-sandbox-container">
      {/* Sandbox Header Toolbar */}
      <div className="sandbox-toolbar">
        <div className="sandbox-preset-group">
          <label htmlFor="preset-select" className="toolbar-label">
            Canonical Presets:
          </label>
          <select
            id="preset-select"
            className="db-dropdown preset-dropdown"
            value={selectedPreset}
            onChange={(e) => handleSelectPreset(e.target.value)}
          >
            {Object.entries(PRESETS).map(([key, item]) => (
              <option key={key} value={key}>
                {item.title}
              </option>
            ))}
          </select>
        </div>

        <div className="sandbox-actions-group">
          <span className="shortcut-hint">
            Press <kbd>Ctrl</kbd> + <kbd>Enter</kbd> to transpile
          </span>
          <button
            className="btn btn-primary btn-transpile"
            onClick={() => runTranspile(pythonCode)}
            disabled={isLoading}
          >
            {isLoading ? "⚡ Transpiling..." : "🚀 Transpile AST"}
          </button>
        </div>
      </div>

      {error && (
        <div className="transpiler-error-banner">
          <span>⚠️ {error}</span>
          <button className="btn btn-icon btn-sm" onClick={() => setError(null)}>✕</button>
        </div>
      )}

      {exportSuccess && (
        <div className="transpiler-success-banner">
          <span>🎉 {exportSuccess}</span>
          <button className="btn btn-icon btn-sm" onClick={() => setExportSuccess(null)}>✕</button>
        </div>
      )}

      {/* Sandbox Mode Switcher Tabs */}
      <div className="sandbox-mode-switcher-bar">
        <div className="sandbox-mode-tabs">
          <button
            type="button"
            className={`sandbox-mode-tab ${sandboxMode === "generator" ? "active" : ""}`}
            onClick={() => setSandboxMode("generator")}
          >
            💻 Multi-Target Code Generator
          </button>
          <button
            type="button"
            className={`sandbox-mode-tab ${sandboxMode === "ast_flow" ? "active" : ""}`}
            onClick={() => setSandboxMode("ast_flow")}
          >
            🌳 Visual AST Pipeline & Lowering Flow
          </button>
          <button
            type="button"
            className={`sandbox-mode-tab ${sandboxMode === "pipeline" ? "active" : ""}`}
            onClick={() => setSandboxMode("pipeline")}
          >
            ⚙️ 4-Pass Compiler Pipeline
          </button>
        </div>
      </div>

      {sandboxMode === "generator" ? (
        <>
          {/* Split-Pane Editors */}
      <div className="sandbox-split-panes">
        {/* Left Pane: Python AST Source */}
        <div className="pane-editor left-pane">
          <div className="pane-header">
            <div className="pane-title">
              <span className="lang-icon">🐍</span>
              <span>Python Source AST</span>
            </div>
            <span className="pane-tag">Input (Lowering Origin)</span>
          </div>

          <div className="monaco-wrapper">
            <Editor
              height="100%"
              language="python"
              theme={monacoTheme}
              value={pythonCode}
              onChange={(val) => setPythonCode(val || "")}
              onMount={handleEditorMount}
              options={{
                minimap: { enabled: false },
                fontSize: 13,
                fontFamily: "var(--font-code, monospace)",
                lineNumbers: "on",
                scrollBeyondLastLine: false,
                automaticLayout: true,
                tabSize: 4,
              }}
            />
          </div>
        </div>

        {/* Right Pane: Target Language Emission */}
        <div className="pane-editor right-pane">
          <div className="pane-header target-tabs-header">
            <div className="target-lang-tabs">
              {(Object.keys(LANGUAGE_META) as TargetLanguage[]).map((lang) => {
                const meta = LANGUAGE_META[lang];
                const isActive = activeTarget === lang;
                return (
                  <button
                    key={lang}
                    className={`target-tab-btn ${isActive ? "active" : ""}`}
                    onClick={() => setActiveTarget(lang)}
                  >
                    <span className="lang-pill">{meta.badge}</span>
                    <span>{meta.label}</span>
                  </button>
                );
              })}
            </div>

            <div className="pane-actions-group">
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={() => handleExportProject(activeTarget)}
                disabled={isExporting}
                title={`Download runnable ${LANGUAGE_META[activeTarget].label} project archive (.zip)`}
              >
                {isExporting ? "⏳ Packaging..." : `📦 Export ${LANGUAGE_META[activeTarget].badge} (.zip)`}
              </button>
              <button
                type="button"
                className="btn btn-outline btn-sm"
                onClick={() => handleExportProject("all")}
                disabled={isExporting}
                title="Download 5-language universal project suite archive (.zip)"
              >
                🌐 Export All (.zip)
              </button>
              <button
                className="btn btn-secondary btn-sm"
                onClick={handleCopyTarget}
                title="Copy synthesized target code"
              >
                {copied ? "✓ Copied!" : "📋 Copy"}
              </button>
            </div>
          </div>

          <div className="monaco-wrapper">
            <Editor
              height="100%"
              language={LANGUAGE_META[activeTarget].monacoLang}
              theme={monacoTheme}
              value={activeOutput?.source_code || (isLoading ? "// Lowering AST..." : "// No emission generated")}
              options={{
                readOnly: true,
                minimap: { enabled: false },
                fontSize: 13,
                fontFamily: "var(--font-code, monospace)",
                lineNumbers: "on",
                scrollBeyondLastLine: false,
                automaticLayout: true,
                tabSize: 4,
              }}
            />
          </div>
        </div>
      </div>

      {/* Bottom Pane: Provenance Inspector */}
      <div className="sandbox-provenance-section">
        <div className="provenance-toggle-bar">
          <button
            className="provenance-toggle-btn"
            onClick={() => setShowProvenance(!showProvenance)}
          >
            <span>{showProvenance ? "▼" : "▶"}</span>
            <span>Empirical Catalog Provenance Inspector ({provenanceRecords.length} operations traced)</span>
          </button>
          <span className="provenance-db-note">Backed by <code>utss_universal_bridge.db</code></span>
        </div>

        {showProvenance && (
          <ProvenanceInspector records={provenanceRecords} />
        )}
      </div>
    </>
  ) : sandboxMode === "ast_flow" ? (
    <AstFlowVisualizer pythonCode={pythonCode} />
  ) : (
    <CompilerPipelineStepper pythonCode={pythonCode} />
  )}
</div>
  );
};
