import React, { useState, useMemo, useEffect } from "react";
import { QueryInfo } from "../types";
import { isLabCompleted } from "../utils/labProgress";

interface SidebarProps {
  queries: QueryInfo[];
  activeQueryId: string;
  onSelectQuery: (queryId: string) => void;
}

export const Sidebar: React.FC<SidebarProps> = ({
  queries,
  activeQueryId,
  onSelectQuery
}) => {
  const [search, setSearch] = useState("");
  const [selectedLevel, setSelectedLevel] = useState("all");
  const [, setTick] = useState(0);

  useEffect(() => {
    const handleUpdate = () => setTick(t => t + 1);
    window.addEventListener("utss-lab-updated", handleUpdate);
    return () => window.removeEventListener("utss-lab-updated", handleUpdate);
  }, []);

  const filteredQueries = useMemo(() => {
    return queries.filter(q => {
      const matchesLevel = selectedLevel === "all" || q.level.toLowerCase() === selectedLevel.toLowerCase();
      const matchesSearch = !search ||
        q.title.toLowerCase().includes(search.toLowerCase()) ||
        q.category.toLowerCase().includes(search.toLowerCase());
      return matchesLevel && matchesSearch;
    });
  }, [queries, search, selectedLevel]);

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <h2 className="sidebar-title">Curriculum & Queries</h2>
        <div className="search-box">
          <input
            type="text"
            placeholder="Filter lessons or topics..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="filter-pills">
          {["all", "Basic", "Intermediate", "Advanced"].map(lvl => (
            <button
              key={lvl}
              className={`pill-btn ${selectedLevel === lvl ? "active" : ""}`}
              onClick={() => setSelectedLevel(lvl)}
            >
              {lvl.charAt(0).toUpperCase() + lvl.slice(1)}
            </button>
          ))}
        </div>
      </div>

      <div className="sidebar-content">
        {filteredQueries.length === 0 ? (
          <div className="loading-state">No matching queries found.</div>
        ) : (
          filteredQueries.map(q => (
            <div
              key={q.id}
              className={`query-card ${q.id === activeQueryId ? "active" : ""}`}
              onClick={() => onSelectQuery(q.id)}
            >
              <div className="query-card-top">
                <span className="query-sequence">LESSON {q.sequence}</span>
                <span className="query-level-pill">{q.level}</span>
                {q.lab_challenge && (
                  <span className={`query-lab-pill ${isLabCompleted(q.id) ? "solved" : ""}`}>
                    {isLabCompleted(q.id) ? "🏆 Solved" : "⚡ Lab"}
                  </span>
                )}
              </div>
              <div className="query-card-title">{q.title}</div>
              <div className="query-card-cat">{q.category || q.suite}</div>
            </div>
          ))
        )}
      </div>
    </aside>
  );
};
