import React, { useRef, useState } from "react";
import Editor, { OnMount } from "@monaco-editor/react";
import { useTheme } from "../context/ThemeContext";

interface SqlEditorProps {
  sql: string;
  onChange: (val: string) => void;
  onRunQuery: () => void;
  onResetQuery: () => void;
  onShowSchema: () => void;
  isLoading: boolean;
}

export const SqlEditor: React.FC<SqlEditorProps> = ({
  sql,
  onChange,
  onRunQuery,
  onResetQuery,
  onShowSchema,
  isLoading
}) => {
  const { monacoTheme } = useTheme();
  const [copied, setCopied] = useState(false);
  const editorRef = useRef<any>(null);

  // Keep a ref to the latest onRunQuery callback to prevent stale closures
  const onRunQueryRef = useRef(onRunQuery);
  onRunQueryRef.current = onRunQuery;

  const handleEditorDidMount: OnMount = (editor, monaco) => {
    editorRef.current = editor;

    // Bind Ctrl+Enter / Cmd+Enter to execute query using latest callback
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.Enter, () => {
      onRunQueryRef.current();
    });
  };

  const handleCopy = () => {
    if (navigator?.clipboard?.writeText) {
      navigator.clipboard.writeText(sql).then(() => {
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
      }).catch((err) => {
        console.warn("Clipboard copy failed:", err);
      });
    }
  };

  return (
    <div id="sql-editor" className="editor-panel">
      <div className="editor-toolbar">
        <div className="toolbar-left">
          <span className="toolbar-label">Interactive SQL Runner (Read-Only)</span>
          <span className="shortcut-hint">
            Press <kbd>Ctrl</kbd> + <kbd>Enter</kbd> to run
          </span>
        </div>
        <div className="toolbar-actions">
          <button className="btn btn-secondary" onClick={handleCopy} title="Copy SQL">
            {copied ? "✓ Copied!" : "📋 Copy"}
          </button>
          <button className="btn btn-secondary" onClick={onResetQuery} title="Reset to original lesson SQL">
            ↺ Reset
          </button>
          <button
            className="btn btn-secondary"
            onClick={onShowSchema}
            title="Inspect Database Schema (SELECT * FROM sqlite_schema;)"
          >
            🔍 Show Schema
          </button>
          <button
            className="btn btn-primary"
            onClick={onRunQuery}
            disabled={isLoading}
            title="Execute Query (Ctrl+Enter)"
          >
            {isLoading ? "Executing..." : "▶ Run Query"}
          </button>
        </div>
      </div>

      <div className="monaco-wrapper">
        <Editor
          height="100%"
          language="sql"
          theme={monacoTheme}
          value={sql}
          onChange={(val) => onChange(val || "")}
          onMount={handleEditorDidMount}
          options={{
            minimap: { enabled: false },
            lineNumbers: "on",
            scrollBeyondLastLine: false,
            automaticLayout: true,
            fontSize: 13.5,
            fontFamily: "'JetBrains Mono', 'Fira Code', Consolas, Menlo, monospace",
            tabSize: 2,
            wordWrap: "on",
            renderLineHighlight: "all"
          }}
        />
      </div>
    </div>
  );
};
