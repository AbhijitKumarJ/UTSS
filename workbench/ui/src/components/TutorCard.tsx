import React, { useState, useEffect } from "react";
import { QueryInfo, GradeLabResponse } from "../types";
import { gradeLabQuery } from "../api";
import { isLabCompleted, markLabCompleted } from "../utils/labProgress";

interface TutorCardProps {
  query: QueryInfo | null;
  activeDbId?: string;
  currentSql?: string;
  onSetSql?: (sql: string) => void;
  onRunQuery?: () => void;
}

export const TutorCard: React.FC<TutorCardProps> = ({
  query,
  activeDbId = "python_recommended",
  currentSql = "",
  onSetSql,
  onRunQuery
}) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [activeTab, setActiveTab] = useState<"theory" | "lab">("theory");
  const [showHint, setShowHint] = useState(false);
  const [isGrading, setIsGrading] = useState(false);
  const [gradingResult, setGradingResult] = useState<GradeLabResponse | null>(null);
  const [isSolved, setIsSolved] = useState(false);

  // Sync completion state and reset grading result when query changes
  useEffect(() => {
    if (query) {
      setIsSolved(isLabCompleted(query.id));
      setGradingResult(null);
      setShowHint(false);
    }
  }, [query]);

  if (!query) {
    return (
      <article className="tutor-card">
        <div className="tutor-card-header">
          <h2 className="lesson-title">Select a query to begin</h2>
        </div>
      </article>
    );
  }

  const lab = query.lab_challenge;

  const handleLoadScaffold = () => {
    if (lab?.starter_sql && onSetSql) {
      onSetSql(lab.starter_sql.trim());
    }
  };

  const handleGrade = async () => {
    if (!lab || !query.id) return;
    setIsGrading(true);
    try {
      const res = await gradeLabQuery({
        query_id: query.id,
        db_id: activeDbId,
        student_sql: currentSql
      });
      setGradingResult(res);
      if (res.passed) {
        markLabCompleted(query.id, res.xp_earned);
        setIsSolved(true);
      }
    } catch (err: any) {
      setGradingResult({
        passed: false,
        score: 0,
        xp_earned: 0,
        feedback: `Grading request failed: ${err.message || "Unknown error"}`,
        diagnostics: {
          execution_success: false,
          columns_matched: false,
          missing_columns: lab.expected_columns || [],
          row_count_valid: false,
          student_row_count: 0,
          expected_min_rows: lab.min_rows || 1,
          error_detail: err.message
        }
      });
    } finally {
      setIsGrading(false);
    }
  };

  return (
    <article className={`tutor-card ${isCollapsed ? "is-collapsed" : ""}`}>
      <div className="tutor-card-header">
        <div className="tutor-header-left">
          <div className="tutor-badges">
            <span className="badge badge-level">{query.level}</span>
            <span className="badge badge-lang">{query.target_language.toUpperCase()}</span>
            <span className="badge badge-cat">{query.category || query.suite}</span>
            {lab && (
              <span className={`badge ${isSolved ? "badge-solved" : "badge-lab"}`}>
                {isSolved ? "🏆 Solved (+XP)" : `⚡ Lab (${lab.xp_reward || 50} XP)`}
              </span>
            )}
          </div>
          <h2 className="lesson-title">{query.title}</h2>
        </div>

        <div className="tutor-header-right">
          {/* Mode Switcher Tabs */}
          <div className="tutor-tab-group">
            <button
              type="button"
              className={`tutor-mode-tab ${activeTab === "theory" ? "active" : ""}`}
              onClick={() => setActiveTab("theory")}
            >
              📖 Theory & Notes
            </button>
            <button
              type="button"
              className={`tutor-mode-tab ${activeTab === "lab" ? "active" : ""}`}
              onClick={() => setActiveTab("lab")}
            >
              🧪 Student Lab {lab && (isSolved ? "✓" : "⚡")}
            </button>
          </div>

          <button
            className="btn btn-sm btn-outline"
            onClick={() => setIsCollapsed(!isCollapsed)}
            title="Toggle Tutor Notes"
            type="button"
          >
            {isCollapsed ? "+ Expand" : "− Collapse"}
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <div className="tutor-card-body">
          {activeTab === "theory" ? (
            <>
              <div className="rationale-section">
                <h3 className="section-label">💡 Why This Query Matters (Internals Insight)</h3>
                <p className="rationale-text">{query.pedagogical_rationale}</p>
              </div>

              <div className="experiments-section">
                <h3 className="section-label">🔬 Guided Experiments for Students</h3>
                <ul className="experiments-list">
                  {query.guided_experiments && query.guided_experiments.length > 0 ? (
                    query.guided_experiments.map((exp, idx) => (
                      <li key={idx}>{exp}</li>
                    ))
                  ) : (
                    <li>Try modifying the WHERE, JOIN, or GROUP BY clauses to explore specific records.</li>
                  )}
                </ul>
              </div>

              {lab && (
                <div className="lab-callout-banner">
                  <span className="lab-callout-icon">🧪</span>
                  <div className="lab-callout-text">
                    <strong>Interactive Lab Challenge Available!</strong> Test your skills by solving the guided exercise for this lesson.
                  </div>
                  <button
                    type="button"
                    className="btn btn-sm btn-accent"
                    onClick={() => setActiveTab("lab")}
                  >
                    Launch Lab Challenge →
                  </button>
                </div>
              )}
            </>
          ) : (
            <div className="student-lab-container">
              {lab ? (
                <>
                  <div className="lab-header-banner">
                    <div className="lab-title-area">
                      <h3 className="lab-objective-heading">🎯 Challenge Objective</h3>
                      <div className="lab-xp-badge">
                        {isSolved ? (
                          <span className="solved-badge">🏆 Completed (+{lab.xp_reward || 100} XP)</span>
                        ) : (
                          <span className="unsolved-badge">⚡ Reward: {lab.xp_reward || 100} XP</span>
                        )}
                      </div>
                    </div>
                    <p className="lab-objective-text">{lab.objective}</p>

                    <div className="lab-criteria-strip">
                      <div className="criteria-item">
                        <span className="criteria-label">Required Columns:</span>
                        <div className="criteria-chips">
                          {lab.expected_columns && lab.expected_columns.length > 0 ? (
                            lab.expected_columns.map(col => (
                              <span key={col} className="chip chip-col">{col}</span>
                            ))
                          ) : (
                            <span className="chip">Any</span>
                          )}
                        </div>
                      </div>

                      {lab.min_rows !== undefined && (
                        <div className="criteria-item">
                          <span className="criteria-label">Min Row Count:</span>
                          <span className="chip chip-rows">≥ {lab.min_rows} rows</span>
                        </div>
                      )}

                      <div className="criteria-item">
                        <span className="criteria-label">Active Target:</span>
                        <span className="chip chip-db">{activeDbId}</span>
                      </div>
                    </div>
                  </div>

                  {/* Lab Action Bar */}
                  <div className="lab-actions-bar">
                    <div className="lab-actions-left">
                      {lab.starter_sql && (
                        <button
                          type="button"
                          className="btn btn-sm btn-outline"
                          onClick={handleLoadScaffold}
                          title="Load the challenge problem scaffold into the SQL Editor"
                        >
                          📥 Load Starter Scaffold
                        </button>
                      )}
                      {lab.hint && (
                        <button
                          type="button"
                          className="btn btn-sm btn-outline"
                          onClick={() => setShowHint(!showHint)}
                          title="Toggle progressive coach hints"
                        >
                          💡 {showHint ? "Hide Hint" : "Need a Hint?"}
                        </button>
                      )}
                      {onRunQuery && (
                        <button
                          type="button"
                          className="btn btn-sm btn-outline"
                          onClick={onRunQuery}
                          title="Execute query and inspect raw results below"
                        >
                          ▶ Run Preview
                        </button>
                      )}
                    </div>

                    <button
                      type="button"
                      className={`btn btn-sm ${isSolved ? "btn-success" : "btn-primary"} btn-grade`}
                      onClick={handleGrade}
                      disabled={isGrading}
                    >
                      {isGrading ? "⏳ Grading Query..." : "🚀 Test & Grade Solution"}
                    </button>
                  </div>

                  {/* Hint Drawer */}
                  {showHint && lab.hint && (
                    <div className="lab-hint-drawer">
                      <div className="hint-label">💡 Teacher's Hint</div>
                      <div className="hint-content">{lab.hint}</div>
                    </div>
                  )}

                  {/* Grading Result Feedback */}
                  {gradingResult && (
                    <div className={`lab-result-card ${gradingResult.passed ? "passed" : "incomplete"}`}>
                      <div className="result-header">
                        <div className="result-title">
                          <span className="result-icon">{gradingResult.passed ? "🎉" : "⚠️"}</span>
                          <h4>{gradingResult.passed ? "Challenge Completed!" : "Check Your Solution"}</h4>
                        </div>
                        <div className="result-score-badge">
                          Score: {gradingResult.score}/100 {gradingResult.xp_earned > 0 ? `(+${gradingResult.xp_earned} XP)` : ""}
                        </div>
                      </div>

                      <p className="result-feedback-text">{gradingResult.feedback}</p>

                      {gradingResult.diagnostics && (
                        <div className="result-diagnostics-grid">
                          <div className={`diag-item ${gradingResult.diagnostics.execution_success ? "success" : "failure"}`}>
                            <span className="diag-icon">{gradingResult.diagnostics.execution_success ? "✓" : "✗"}</span>
                            <span className="diag-text">
                              SQL Execution: {gradingResult.diagnostics.execution_success ? "Success" : "Failed"}
                            </span>
                          </div>

                          <div className={`diag-item ${gradingResult.diagnostics.columns_matched ? "success" : "failure"}`}>
                            <span className="diag-icon">{gradingResult.diagnostics.columns_matched ? "✓" : "✗"}</span>
                            <span className="diag-text">
                              Columns: {gradingResult.diagnostics.columns_matched ? "All Required Present" : `Missing: ${gradingResult.diagnostics.missing_columns.join(", ")}`}
                            </span>
                          </div>

                          <div className={`diag-item ${gradingResult.diagnostics.row_count_valid ? "success" : "failure"}`}>
                            <span className="diag-icon">{gradingResult.diagnostics.row_count_valid ? "✓" : "✗"}</span>
                            <span className="diag-text">
                              Rows: {gradingResult.diagnostics.student_row_count} rows returned (min: {gradingResult.diagnostics.expected_min_rows})
                            </span>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </>
              ) : (
                <div className="lab-empty-state">
                  <div className="empty-icon">📖</div>
                  <h3>Architectural Exploration Lesson</h3>
                  <p>
                    This lesson is designed for in-depth conceptual exploration and guided queries.
                    To practice interactive query challenges with automated grading, select
                    <strong> Lesson 1: Strata & Environments</strong> or <strong>Lesson 2: Container Taxonomy</strong>.
                  </p>
                  <button
                    type="button"
                    className="btn btn-sm btn-outline"
                    onClick={() => setActiveTab("theory")}
                  >
                    ← Return to Lesson Notes
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </article>
  );
};
