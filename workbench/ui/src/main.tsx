import React from "react";
import ReactDOM from "react-dom/client";
import { loader } from "@monaco-editor/react";
import * as monaco from "monaco-editor";
import { ThemeProvider } from "./context/ThemeContext";
import App from "./App";
import "./styles/themes.css";

// Configure local monaco-editor bundle so it doesn't depend on external CDNs
loader.config({ monaco });

// Define custom Monaco themes
monaco.editor.defineTheme("utss-dark", {
  base: "vs-dark",
  inherit: true,
  rules: [
    { token: "keyword", foreground: "3b82f6", fontStyle: "bold" },
    { token: "string", foreground: "10b981" },
    { token: "number", foreground: "f59e0b" },
    { token: "comment", foreground: "6b7280", fontStyle: "italic" }
  ],
  colors: {
    "editor.background": "#0d1117",
    "editor.foreground": "#f9fafb",
    "editorLineNumber.foreground": "#4b5563",
    "editorLineNumber.activeForeground": "#3b82f6",
    "editor.lineHighlightBackground": "#161f2e",
    "editorCursor.foreground": "#3b82f6"
  }
});

monaco.editor.defineTheme("monokai", {
  base: "vs-dark",
  inherit: true,
  rules: [
    { token: "keyword", foreground: "f92672", fontStyle: "bold" },
    { token: "string", foreground: "e6db74" },
    { token: "number", foreground: "ae81ff" },
    { token: "comment", foreground: "75715e", fontStyle: "italic" }
  ],
  colors: {
    "editor.background": "#272822",
    "editor.foreground": "#f8f8f2",
    "editorLineNumber.foreground": "#75715e",
    "editorLineNumber.activeForeground": "#fd971f",
    "editor.lineHighlightBackground": "#3e3d32",
    "editorCursor.foreground": "#f8f8f0"
  }
});

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element not found");
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </React.StrictMode>
);
