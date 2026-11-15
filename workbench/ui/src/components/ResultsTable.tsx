import React from "react";
import { ExecuteResponse } from "../types";

interface ResultsTableProps {
  result: ExecuteResponse | null;
  isLoading: boolean;
  activeDbId: string;
}

export const ResultsTable: React.FC<ResultsTableProps> = ({
  result,
  isLoading,
  activeDbId
}) => {
  const handleExportCsv = () => {
    if (!result || !result.columns || !result.rows || result.rows.length === 0) return;

    const escapeCsvCell = (val: any): string => {
      if (val === null || val === undefined) return "";
      const str = typeof val === "object" ? JSON.stringify(val) : String(val);
      if (str.includes(",") || str.includes('"') || str.includes("\n") || str.includes("\r")) {
        return `"${str.replace(/"/g, '""')}"`;
      }
      return str;
    };

    const headerLine = result.columns.map(escapeCsvCell).join(",");
    const rowLines = result.rows.map(row => row.map(escapeCsvCell).join(","));
    const csvContent = [headerLine, ...rowLines].join("\r\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `query_results_${activeDbId}_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  if (isLoading) {
    return (
      <div id="results-table" className="table-container">
        <div className="table-status-bar">
          <div className="stats-group">
            <span className="stat-item loading-text">Running query against <strong>{activeDbId}</strong>...</span>
          </div>
        </div>
        <div className="table-placeholder">
          <div className="spinner"></div>
          <p>Executing SQL query against read-only SQLite database...</p>
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div id="results-table" className="table-container">
        <div className="table-placeholder">
          <p>Select a lesson query or write SQL above and press <strong>▶ Run Query</strong> (or <code>Ctrl+Enter</code>).</p>
        </div>
      </div>
    );
  }

  if (result.error) {
    return (
      <div id="results-table" className="table-container">
        <div className="error-banner">
          <div className="error-title">⚠️ Query Execution Error</div>
          <pre className="error-message">{result.error}</pre>
        </div>
      </div>
    );
  }

  const columns = result.columns || [];
  const rows = result.rows || [];

  return (
    <div id="results-table" className="table-container">
      <div className="table-status-bar">
        <div className="stats-group">
          <span className="stat-item">
            Rows: <strong>{result.row_count ?? rows.length}</strong>
          </span>
          {result.execution_time_ms !== undefined && (
            <span className="stat-item">
              Duration: <strong>{result.execution_time_ms.toFixed(2)} ms</strong>
            </span>
          )}
          <span className="stat-item">
            Target DB: <code className="target-db-badge">{result.db_id || activeDbId}</code>
          </span>
          {(result.has_more || result.truncated) && (
            <span className="stat-item badge badge-warning">
              Preview limited to 500 rows
            </span>
          )}
        </div>
        <button
          className="btn btn-secondary btn-sm"
          onClick={handleExportCsv}
          disabled={rows.length === 0}
          title="Download current result table as CSV"
        >
          ⬇ Download CSV
        </button>
      </div>

      <div
        className="table-scroll"
        tabIndex={0}
        role="region"
        aria-label="Query results data table"
      >
        {rows.length === 0 ? (
          <div className="table-placeholder">
            <p>Query executed successfully, but returned 0 rows.</p>
          </div>
        ) : (
          <table className="results-table">
            <thead>
              <tr>
                <th scope="col" className="row-num-col">#</th>
                {columns.map((col, idx) => (
                  <th key={idx} scope="col">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, rIdx) => (
                <tr key={rIdx}>
                  <td className="row-num-cell">{rIdx + 1}</td>
                  {row.map((val, cIdx) => (
                    <td key={cIdx}>
                      {val === null || val === undefined ? (
                        <span className="null-value">NULL</span>
                      ) : typeof val === "boolean" ? (
                        val ? "TRUE" : "FALSE"
                      ) : typeof val === "object" ? (
                        JSON.stringify(val)
                      ) : (
                        String(val)
                      )}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
};
