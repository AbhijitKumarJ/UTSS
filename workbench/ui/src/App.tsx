import React, { useState, useEffect, useCallback, useRef } from "react";
import { DatabaseInfo, QueryInfo, ExecuteResponse } from "./types";
import { fetchDatabases, fetchQueries, executeQuery } from "./api";
import { TopNav } from "./components/TopNav";
import { Sidebar } from "./components/Sidebar";
import { TutorCard } from "./components/TutorCard";
import { SqlEditor } from "./components/SqlEditor";
import { ResultsTable } from "./components/ResultsTable";
import { RosettaPlayground } from "./components/RosettaPlayground";
import { HomeOverview } from "./components/HomeOverview";
import { AstGraphView } from "./components/graph/AstGraphView";
import { ComparativeDashboard } from "./components/analysis/ComparativeDashboard";
import "./App.css";

export const App: React.FC = () => {
  const [databases, setDatabases] = useState<DatabaseInfo[]>([]);
  const [activeDbId, setActiveDbId] = useState<string>("");
  const [activeSuite, setActiveSuite] = useState<string>("home");
  const [comparativeView, setComparativeView] = useState<"visual" | "sql">("visual");
  const [queries, setQueries] = useState<QueryInfo[]>([]);
  const [activeQueryId, setActiveQueryId] = useState<string>("");
  const [sql, setSql] = useState<string>("");
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [result, setResult] = useState<ExecuteResponse | null>(null);

  // Keep refs to avoid stale closures in callbacks
  const sqlRef = useRef<string>("");
  sqlRef.current = sql;

  const activeQueryIdRef = useRef<string>("");
  activeQueryIdRef.current = activeQueryId;

  // Run SQL against a database
  const runSql = useCallback(async (dbId: string, sqlToRun: string) => {
    if (!dbId || !sqlToRun.trim()) return;
    setIsLoading(true);
    try {
      const res = await executeQuery(dbId, sqlToRun);
      setResult(res);
    } catch (err: any) {
      setResult({
        error: err.message || "Failed to execute query",
        db_id: dbId
      });
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Load databases on mount
  const loadDatabases = useCallback(async () => {
    try {
      const dbs = await fetchDatabases();
      setDatabases(dbs);

      if (dbs.length > 0) {
        // Prefer python_recommended or python_base_full or first available
        const defaultDb = dbs.find(d => d.id === "python_recommended") ||
                          dbs.find(d => d.id === "python_base_full") ||
                          dbs[0];
        setActiveDbId(prev => (prev && dbs.some(d => d.id === prev) ? prev : defaultDb.id));
      }
    } catch (err: any) {
      console.error("Failed to load databases:", err);
    }
  }, []);

  useEffect(() => {
    loadDatabases();
  }, [loadDatabases]);

  // Load queries whenever activeDbId or activeSuite changes
  const loadQueriesForDb = useCallback(async (dbId: string, suite: string, preserveSql: boolean = false) => {
    if (!dbId) return;
    const suiteToFetch = suite === "home" ? "tutoring" : suite;
    try {
      const qList = await fetchQueries(dbId, suiteToFetch);
      setQueries(qList);

      if (qList.length > 0) {
        const matchingQuery = qList.find(q => q.id === activeQueryIdRef.current);
        const targetQuery = matchingQuery || qList[0];
        setActiveQueryId(targetQuery.id);

        if (!preserveSql) {
          setSql(targetQuery.sql);
          if (suite !== "home") {
            runSql(dbId, targetQuery.sql);
          }
        } else {
          // Keep current edited SQL and run against newly selected DB
          if (sqlRef.current.trim()) {
            if (suite !== "home") {
              runSql(dbId, sqlRef.current);
            }
          } else {
            setSql(targetQuery.sql);
            if (suite !== "home") {
              runSql(dbId, targetQuery.sql);
            }
          }
        }
      } else {
        setActiveQueryId("");
        if (!preserveSql) {
          setSql("");
          setResult(null);
        }
      }
    } catch (err: any) {
      console.error("Failed to load queries:", err);
    }
  }, [runSql]);

  // Trigger loading queries when activeDbId is first resolved
  const initialLoadDone = useRef(false);
  useEffect(() => {
    if (activeDbId && !initialLoadDone.current) {
      initialLoadDone.current = true;
      loadQueriesForDb(activeDbId, activeSuite, false);
    }
  }, [activeDbId, activeSuite, loadQueriesForDb]);

  // Handle switching database: preserve user SQL in editor
  const handleSelectDb = (newDbId: string) => {
    if (newDbId === activeDbId) return;
    setActiveDbId(newDbId);
    // Reload queries for this DB, preserving student's SQL
    loadQueriesForDb(newDbId, activeSuite, true);
  };

  // Handle switching suite (home vs tutoring vs comparative vs playground)
  const handleSelectSuite = (newSuite: string) => {
    if (newSuite === activeSuite) return;
    setActiveSuite(newSuite);

    if (newSuite === "home") {
      return;
    }

    let targetDbId = activeDbId;
    if (newSuite === "playground") {
      const bridgeDb = databases.find(d => d.id === "utss_universal_bridge");
      if (bridgeDb) {
        targetDbId = bridgeDb.id;
        setActiveDbId(targetDbId);
      }
    } else if (newSuite === "comparative" && !activeDbId.startsWith("federated_")) {
      const fedDb = databases.find(d => d.id === "federated_recommended") || databases.find(d => d.id === "federated_full");
      if (fedDb) {
        targetDbId = fedDb.id;
        setActiveDbId(targetDbId);
      }
    } else if (newSuite === "tutoring" && (activeDbId.startsWith("federated_") || activeDbId === "utss_universal_bridge")) {
      const langDb = databases.find(d => d.id === "python_recommended") || databases.find(d => !d.id.startsWith("federated_") && d.id !== "utss_universal_bridge");
      if (langDb) {
        targetDbId = langDb.id;
        setActiveDbId(targetDbId);
      }
    }

    if (newSuite !== "playground" && newSuite !== "graph") {
      loadQueriesForDb(targetDbId, newSuite, false);
    }
  };

  // Handle jump from Graph Inspector directly to SQL Runner
  const handleJumpToSql = (sqlToRun: string) => {
    setActiveSuite("tutoring");
    setSql(sqlToRun);
    runSql(activeDbId, sqlToRun);
  };

  // Handle navigate to Rosetta Playground for a specific language pair
  const handleNavigateToPlayground = (sourceLang: string, targetLang: string) => {
    setActiveSuite("playground");
    const bridgeDb = databases.find(d => d.id === "utss_universal_bridge");
    if (bridgeDb) {
      setActiveDbId(bridgeDb.id);
    }
  };

  // Handle home page quick-action navigation
  const handleHomeNavigate = (suite: string, action?: string) => {
    handleSelectSuite(suite);
    if (action === "schema") {
      setTimeout(() => {
        handleShowSchema();
      }, 50);
    }
  };

  // Handle selecting a query from sidebar
  const handleSelectQuery = (queryId: string) => {
    setActiveQueryId(queryId);
    const selected = queries.find(q => q.id === queryId);
    if (selected) {
      setSql(selected.sql);
      runSql(activeDbId, selected.sql);
    }
  };

  // Handle reset query to original lesson SQL
  const handleResetQuery = () => {
    const selected = queries.find(q => q.id === activeQueryId);
    if (selected) {
      setSql(selected.sql);
      runSql(activeDbId, selected.sql);
    }
  };

  // Handle show database schema
  const handleShowSchema = () => {
    const schemaSql = "SELECT * FROM sqlite_schema;";
    setSql(schemaSql);
    runSql(activeDbId, schemaSql);
  };

  const activeQuery = queries.find(q => q.id === activeQueryId) || null;

  return (
    <div className="app-container">
      <TopNav
        databases={databases}
        activeDbId={activeDbId}
        onSelectDb={handleSelectDb}
        onRefreshDbs={loadDatabases}
        activeSuite={activeSuite}
        onSelectSuite={handleSelectSuite}
      />

      <div className="app-body">
        {activeSuite === "home" ? (
          <main className="workspace home-workspace">
            <HomeOverview
              databases={databases}
              activeDbId={activeDbId}
              onNavigate={handleHomeNavigate}
            />
          </main>
        ) : activeSuite === "graph" ? (
          <main className="workspace graph-workspace">
            <AstGraphView
              activeDbId={activeDbId}
              onJumpToSql={handleJumpToSql}
            />
          </main>
        ) : activeSuite === "playground" ? (
          <main className="workspace playground-workspace">
            <RosettaPlayground />
          </main>
        ) : activeSuite === "comparative" && comparativeView === "visual" ? (
          <main className="workspace comparative-workspace">
            <div className="comparative-subnav-bar">
              <div className="submode-switcher">
                <button
                  className="submode-btn active"
                  onClick={() => setComparativeView("visual")}
                  type="button"
                >
                  📈 Empirical Metrics & Impedance
                </button>
                <button
                  className="submode-btn"
                  onClick={() => setComparativeView("sql")}
                  type="button"
                >
                  📖 Federated SQL Curriculum
                </button>
              </div>
            </div>
            <ComparativeDashboard onNavigateToPlayground={handleNavigateToPlayground} />
          </main>
        ) : (
          <>
            <Sidebar
              queries={queries}
              activeQueryId={activeQueryId}
              onSelectQuery={handleSelectQuery}
            />

            <main className="workspace">
              {activeSuite === "comparative" && (
                <div className="comparative-subnav-bar inside-workspace">
                  <div className="submode-switcher">
                    <button
                      className="submode-btn"
                      onClick={() => setComparativeView("visual")}
                      type="button"
                    >
                      📈 Empirical Metrics & Impedance
                    </button>
                    <button
                      className="submode-btn active"
                      onClick={() => setComparativeView("sql")}
                      type="button"
                    >
                      📖 Federated SQL Curriculum
                    </button>
                  </div>
                </div>
              )}

              <TutorCard
                query={activeQuery}
                activeDbId={activeDbId}
                currentSql={sql}
                onSetSql={(scaffold) => {
                  setSql(scaffold);
                  runSql(activeDbId, scaffold);
                }}
                onRunQuery={() => runSql(activeDbId, sql)}
              />

              <SqlEditor
                sql={sql}
                onChange={setSql}
                onRunQuery={() => runSql(activeDbId, sql)}
                onResetQuery={handleResetQuery}
                onShowSchema={handleShowSchema}
                isLoading={isLoading}
              />

              <ResultsTable
                result={result}
                isLoading={isLoading}
                activeDbId={activeDbId}
              />
            </main>
          </>
        )}
      </div>
    </div>
  );
};
export default App;
