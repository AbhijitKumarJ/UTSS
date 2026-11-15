import React, { useState, useEffect } from "react";
import { DatabaseInfo, ThemeName } from "../types";
import { useTheme } from "../context/ThemeContext";
import { getTotalLabXp, getCompletedLabs } from "../utils/labProgress";
import { GraduationCertificateModal } from "./lab/GraduationCertificateModal";

interface TopNavProps {
  databases: DatabaseInfo[];
  activeDbId: string;
  onSelectDb: (dbId: string) => void;
  onRefreshDbs: () => void;
  activeSuite: string;
  onSelectSuite: (suite: string) => void;
}

export const TopNav: React.FC<TopNavProps> = ({
  databases,
  activeDbId,
  onSelectDb,
  onRefreshDbs,
  activeSuite,
  onSelectSuite
}) => {
  const { theme, setTheme } = useTheme();
  const currentDb = databases.find(d => d.id === activeDbId);
  const [totalXp, setTotalXp] = useState(getTotalLabXp());
  const [completedCount, setCompletedCount] = useState(Object.keys(getCompletedLabs()).length);
  const [isCertOpen, setIsCertOpen] = useState(false);

  useEffect(() => {
    const handleUpdate = () => {
      setTotalXp(getTotalLabXp());
      setCompletedCount(Object.keys(getCompletedLabs()).length);
    };
    window.addEventListener("utss-lab-updated", handleUpdate);
    return () => window.removeEventListener("utss-lab-updated", handleUpdate);
  }, []);

  return (
    <header className="top-nav">
      {/* Brand logo - clicking navigates to Home Overview */}
      <button
        className="brand-clickable"
        onClick={() => onSelectSuite("home")}
        title="UTSS Home Overview & Guide"
        type="button"
      >
        <div className="brand-logo">UTSS</div>
      </button>

      <div className="nav-controls">
        {/* Mode Tabs */}
        <div className="mode-tabs">
          <button
            className={`tab-btn icon-only-tab ${activeSuite === "home" ? "active" : ""}`}
            onClick={() => onSelectSuite("home")}
            title="Overview & Guide"
            aria-label="Home Overview"
          >
            🏠
          </button>
          <button
            className={`tab-btn ${activeSuite === "tutoring" ? "active" : ""}`}
            onClick={() => onSelectSuite("tutoring")}
            title="Interactive SQL Language Tutoring & AST Exploration"
          >
            🎓 Tutoring & Internals
          </button>
          <button
            className={`tab-btn ${activeSuite === "comparative" ? "active" : ""}`}
            onClick={() => onSelectSuite("comparative")}
            title="Federated Multi-Language Comparative Analytics"
          >
            📊 Comparative Analytics
          </button>
          <button
            className={`tab-btn ${activeSuite === "graph" ? "active" : ""}`}
            onClick={() => onSelectSuite("graph")}
            title="Interactive AST & Container Hierarchy Graph Visualizer"
          >
            🌳 AST Graph
          </button>
          <button
            className={`tab-btn ${activeSuite === "playground" ? "active" : ""}`}
            onClick={() => onSelectSuite("playground")}
            title="Rosetta Transpiler Playground & Crosswalk Matrix"
          >
            🔄 Rosetta Playground
          </button>
        </div>

        {/* Database Switcher */}
        <div className="db-switcher">
          <label htmlFor="db-select" className="db-label">Database:</label>
          <select
            id="db-select"
            className="db-dropdown"
            value={activeDbId}
            onChange={(e) => onSelectDb(e.target.value)}
            title="Select target database catalog"
          >
            {databases.map(db => {
              const langLabel = db.language !== "unknown" ? db.language.toUpperCase() : "Custom";
              const symLabel = db.symbol_count ? ` (${db.symbol_count.toLocaleString()} symbols)` : "";
              return (
                <option key={db.id} value={db.id}>
                  {langLabel}: {db.id}{symLabel}
                </option>
              );
            })}
          </select>
          <button className="btn btn-icon" onClick={onRefreshDbs} title="Refresh Databases" type="button">
            🔄
          </button>
        </div>

        {/* Student Lab Progress Badge - Clickable to open Graduation Certificate */}
        <div
          className="student-xp-pill clickable-pill"
          onClick={() => setIsCertOpen(true)}
          title={`Student Challenge Progress: ${completedCount} Solved (${totalXp} XP) — Click to view Graduation Certificate 🎓`}
          role="button"
          tabIndex={0}
        >
          <span className="xp-icon">⚡</span>
          <span className="xp-val">{totalXp} XP</span>
          <span className="xp-count">({completedCount} solved 🎓)</span>
        </div>

        <GraduationCertificateModal
          isOpen={isCertOpen}
          onClose={() => setIsCertOpen(false)}
        />

        {/* Theme Switcher - Guaranteed Visible */}
        <div className="theme-switcher">
          <label htmlFor="theme-select" className="db-label theme-label">🎨 Theme:</label>
          <select
            id="theme-select"
            className="db-dropdown theme-dropdown"
            value={theme}
            onChange={(e) => setTheme(e.target.value as ThemeName)}
            title="Select visual theme"
          >
            <option value="utss-dark">UTSS Slate Dark</option>
            <option value="vscode-dark">VS Code Dark+</option>
            <option value="vscode-light">VS Code Light+</option>
            <option value="monokai">Monokai</option>
          </select>
        </div>
      </div>
    </header>
  );
};
