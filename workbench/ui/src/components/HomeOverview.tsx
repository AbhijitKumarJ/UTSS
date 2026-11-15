import React from "react";
import { DatabaseInfo } from "../types";

interface HomeOverviewProps {
  databases: DatabaseInfo[];
  activeDbId: string;
  onNavigate: (suite: string, action?: string) => void;
}

export const HomeOverview: React.FC<HomeOverviewProps> = ({
  databases,
  activeDbId,
  onNavigate
}) => {
  const currentDb = databases.find(d => d.id === activeDbId);
  const totalDatabases = databases.length;

  return (
    <div className="home-overview">
      {/* Hero Section */}
      <section className="home-hero">
        <div className="hero-badge">
          <span className="badge-pill">UTSS v2.0</span>
          <span className="hero-badge-desc">Cross-Language Relational AST Platform</span>
        </div>
        <h1 className="hero-title">
          UTSS Universal Language Analysis & Synthesis Workbench
        </h1>
        <p className="hero-subtitle">
          Interactive Internals Tutor, Multi-Database AST Explorer & Comparative Analytics
        </p>
        <p className="hero-intro">
          A high-performance relational workbench for inspecting, analyzing, and synthesizing programming
          language standard libraries and ASTs. Query normalized relational schemas across C++, C#, Go,
          Python, Rust, and TypeScript with real-time in-memory federation and canonical transpilation bridges.
        </p>

        {/* Quick Launch Cards */}
        <div className="launch-grid">
          {/* Card 1: Tutoring & Internals */}
          <div className="launch-card">
            <div className="card-header">
              <span className="card-icon">🎓</span>
              <div className="card-title-group">
                <h3>Language Tutoring & Internals</h3>
                <span className="card-tag">Curriculum & Sandbox</span>
              </div>
            </div>
            <p className="card-description">
              Interactive step-by-step SQL curriculum exploring the anatomy of language standard libraries.
              Inspect fundamental types, header & module strata, container topologies, templates, classes,
              functions, and state member mutability.
            </p>
            <div className="card-badges">
              <span className="mini-badge">Monaco SQL Editor</span>
              <span className="mini-badge">Read-Only SQLite</span>
              <span className="mini-badge">CSV Export</span>
            </div>
            <button
              className="btn btn-primary card-action-btn"
              onClick={() => onNavigate("tutoring")}
            >
              Start Tutoring →
            </button>
          </div>

          {/* Card 2: Comparative Analytics */}
          <div className="launch-card">
            <div className="card-header">
              <span className="card-icon">📊</span>
              <div className="card-title-group">
                <h3>Comparative Analytics</h3>
                <span className="card-tag">Federated Catalogs</span>
              </div>
            </div>
            <p className="card-description">
              Federated multi-language analysis querying 6 distinct language ecosystems simultaneously.
              Cross-analyze ambient type volumes, container nesting depths, parameter variance, and
              mutability strata using unified master views.
            </p>
            <div className="card-badges">
              <span className="mini-badge">6-Language Federation</span>
              <span className="mini-badge">v_all_* Views</span>
              <span className="mini-badge">10 Benchmark Queries</span>
            </div>
            <button
              className="btn btn-primary card-action-btn"
              onClick={() => onNavigate("comparative")}
            >
              Explore Federation →
            </button>
          </div>

          {/* Card 3: Rosetta Transpiler Playground */}
          <div className="launch-card">
            <div className="card-header">
              <span className="card-icon">🔄</span>
              <div className="card-title-group">
                <h3>Rosetta Transpiler Playground</h3>
                <span className="card-tag">Semantic Crosswalk</span>
              </div>
            </div>
            <p className="card-description">
              Semantic crosswalk matrix and live bidirectional transpilation sandbox. Translate collections,
              control flow, memory, and functional idioms across all 6 supported languages with type preservation
              and runtime semantics.
            </p>
            <div className="card-badges">
              <span className="mini-badge">22 Canonical Concepts</span>
              <span className="mini-badge">Live Transpilation</span>
              <span className="mini-badge">Bidirectional Bridges</span>
            </div>
            <button
              className="btn btn-primary card-action-btn"
              onClick={() => onNavigate("playground")}
            >
              Open Rosetta Playground →
            </button>
          </div>

          {/* Card 4: AST & Hierarchy Graph Visualizer */}
          <div className="launch-card">
            <div className="card-header">
              <span className="card-icon">🌳</span>
              <div className="card-title-group">
                <h3>AST & Hierarchy Graph</h3>
                <span className="card-tag">Interactive Topology</span>
              </div>
            </div>
            <p className="card-description">
              Visualize package and module containment trees, class inheritance and interface implementation
              DAGs, and universal concept clusters with an interactive pan/zoom canvas and direct SQL inspector.
            </p>
            <div className="card-badges">
              <span className="mini-badge">Containment Trees</span>
              <span className="mini-badge">Inheritance DAG</span>
              <span className="mini-badge">SQL Bridge</span>
            </div>
            <button
              className="btn btn-primary card-action-btn"
              onClick={() => onNavigate("graph")}
            >
              Explore AST Graph →
            </button>
          </div>
        </div>
      </section>

      {/* Architecture & Workflows */}
      <section className="home-section">
        <h2 className="section-title">🏛️ Architecture & Database Hierarchy</h2>
        <div className="arch-grid">
          <div className="arch-card">
            <h4>Curated Recommended Catalogs</h4>
            <p>
              Pre-filtered baselines containing 150–500 essential symbols per language. Tailored for targeted
              tutoring and sub-millisecond query evaluation without noise from tertiary compiler internals.
            </p>
            <div className="arch-tags">
              <code>cpp_recommended</code>
              <code>cs_recommended</code>
              <code>go_recommended</code>
              <code>python_recommended</code>
              <code>rust_recommended</code>
              <code>ts_recommended</code>
            </div>
          </div>

          <div className="arch-card">
            <h4>Full Standard Library Catalogs</h4>
            <p>
              Exhaustive standard library and runtime ecosystem databases containing thousands of AST entities,
              templates, classes, interfaces, built-in types, and external framework packages.
            </p>
            <div className="arch-tags">
              <code>cpp_full</code>
              <code>cs_full</code>
              <code>go_full</code>
              <code>python_base_full</code>
              <code>rust_full</code>
              <code>ts_full</code>
            </div>
          </div>

          <div className="arch-card">
            <h4>Federated In-Memory Multi-Catalogs</h4>
            <p>
              Dynamic SQLite <code>:memory:</code> connections attaching all 6 catalogs with zero on-disk
              duplication. Provides unified cross-language views (<code>v_all_symbols</code>, <code>v_all_containers</code>,
              <code>v_all_callables</code>, etc.).
            </p>
            <div className="arch-tags">
              <code>federated_recommended</code>
              <code>federated_full</code>
            </div>
          </div>

          <div className="arch-card">
            <h4>Universal Bridge Database</h4>
            <p>
              Normalized cross-language semantic concepts, impedance scores, and bidirectional operational
              bridges (<code>dbs/utss_universal_bridge.db</code>) linking idiomatic expressions across languages.
            </p>
            <div className="arch-tags">
              <code>utss_universal_bridge</code>
            </div>
          </div>
        </div>
      </section>

      {/* Relational AST Schema Breakdown */}
      <section className="home-section">
        <h2 className="section-title">🧬 Relational AST Schema Model</h2>
        <p className="section-desc">
          UTSS standardizes diverse language syntaxes into a canonical 6-table relational schema:
        </p>
        <div className="schema-table-container">
          <table className="schema-summary-table">
            <thead>
              <tr>
                <th>Table</th>
                <th>Entity Represented</th>
                <th>Key Columns</th>
                <th>Cross-Language Role</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><code>distributions</code></td>
                <td>Distribution / Package Root</td>
                <td><code>dist_id, dist_name, dist_version, stratum</code></td>
                <td>Distinguishes ambient built-ins (stratum 0), standard library (stratum 1), and workspace code (stratum 3).</td>
              </tr>
              <tr>
                <td><code>containers</code></td>
                <td>Scope / Namespace / Module / Class</td>
                <td><code>container_id, kind, qualified_name, parent_id</code></td>
                <td>Hierarchical lexical scopes: packages, namespaces, classes, structs, modules, and interfaces.</td>
              </tr>
              <tr>
                <td><code>symbols</code></td>
                <td>Named Program Entity / Type</td>
                <td><code>symbol_id, name, kind, data_type, is_type</code></td>
                <td>Fundamental types, user types, aliases, variables, constants, and type parameters.</td>
              </tr>
              <tr>
                <td><code>callables</code></td>
                <td>Function / Method / Constructor</td>
                <td><code>callable_id, name, return_type, is_async, is_generator</code></td>
                <td>Invocable units: free functions, member methods, constructors, operators, and lambdas.</td>
              </tr>
              <tr>
                <td><code>parameters</code></td>
                <td>Callable Parameter Signature</td>
                <td><code>param_id, name, position, data_type, is_variadic</code></td>
                <td>Ordered parameter signatures, defaults, pass-by-reference semantics, and variadic packs.</td>
              </tr>
              <tr>
                <td><code>state_members</code></td>
                <td>Field / Property / State Variable</td>
                <td><code>member_id, name, is_mutable, access_modifier</code></td>
                <td>Class fields, struct properties, enum members, and immutability guarantees.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      {/* Pro Tips & Keyboard Shortcuts */}
      <section className="home-section">
        <h2 className="section-title">⌨️ Pro Tips & Shortcuts</h2>
        <div className="tips-grid">
          <div className="tip-card">
            <span className="tip-key">Ctrl + Enter</span>
            <div className="tip-content">
              <strong>Run Active Query</strong>
              <p>Execute SQL directly from the Monaco Editor without clicking the run button.</p>
            </div>
          </div>
          <div className="tip-card">
            <span className="tip-key">🔍 Show Schema</span>
            <div className="tip-content">
              <strong>Instant Schema Discovery</strong>
              <p>Loads and runs <code>SELECT * FROM sqlite_schema;</code> on the currently active database.</p>
            </div>
          </div>
          <div className="tip-card">
            <span className="tip-key">↺ Reset Query</span>
            <div className="tip-content">
              <strong>Revert to Lesson SQL</strong>
              <p>Discards scratchpad modifications and reloads the pristine lesson query.</p>
            </div>
          </div>
          <div className="tip-card">
            <span className="tip-key">🎨 Theme Selector</span>
            <div className="tip-content">
              <strong>Theme Customization</strong>
              <p>Switch between UTSS Slate Dark, VS Code Dark+, VS Code Light+, and Monokai in the top nav.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Connected Status Footer */}
      <section className="home-footer-status">
        <div className="status-item">
          <span className="status-dot"></span>
          <span><strong>{totalDatabases}</strong> Databases Discovered & Ready</span>
        </div>
        <div className="status-item">
          <span>Active Target: <strong>{activeDbId || "None"}</strong></span>
          {currentDb && (
            <span className="badge badge-info" style={{ marginLeft: "0.5rem" }}>
              {currentDb.language.toUpperCase()} • {(currentDb.symbol_count || 0).toLocaleString()} SYMBOLS
            </span>
          )}
        </div>
        <div className="status-item">
          <span>Mode: <strong>Read-Only Sandbox (Guaranteed Safe)</strong></span>
        </div>
      </section>
    </div>
  );
};
