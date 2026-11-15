// UTSS Universal Language Analysis & Synthesis Workbench Frontend Controller

const state = {
  databases: [],
  activeDbId: "",
  queries: [],
  activeQueryId: "",
  activeSuite: "tutoring",
  activeLevel: "all",
  searchQuery: "",
  lastResults: null
};

// DOM Element References
const dom = {
  dbSelect: document.getElementById("db-select"),
  dbStatsBadge: document.getElementById("db-stats-badge"),
  btnRefreshDbs: document.getElementById("btn-refresh-dbs"),
  tabTutoring: document.getElementById("tab-tutoring"),
  tabComparative: document.getElementById("tab-comparative"),
  searchInput: document.getElementById("search-input"),
  levelFilters: document.getElementById("level-filters"),
  queryList: document.getElementById("query-list"),
  
  // Tutor Card
  lessonTitle: document.getElementById("lesson-title"),
  lessonLevelBadge: document.getElementById("lesson-level-badge"),
  lessonLangBadge: document.getElementById("lesson-lang-badge"),
  lessonCategoryBadge: document.getElementById("lesson-category-badge"),
  lessonRationale: document.getElementById("lesson-rationale"),
  guidedExperiments: document.getElementById("guided-experiments"),
  
  // SQL Editor
  sqlEditor: document.getElementById("sql-editor"),
  lineNumbers: document.getElementById("line-numbers"),
  btnRunQuery: document.getElementById("btn-run-query"),
  btnResetQuery: document.getElementById("btn-reset-query"),
  btnCopySql: document.getElementById("btn-copy-sql"),
  
  // Stats & Error
  statRowCount: document.getElementById("stat-row-count"),
  statExecutionTime: document.getElementById("stat-execution-time"),
  statDbId: document.getElementById("stat-db-id"),
  badgeTruncated: document.getElementById("badge-truncated"),
  errorBanner: document.getElementById("error-banner"),
  errorMessage: document.getElementById("error-message"),
  btnDownloadCsv: document.getElementById("btn-download-csv"),
  
  // Results Table
  tableHead: document.getElementById("table-head"),
  tableBody: document.getElementById("table-body")
};

// --- Initialization ---
async function init() {
  setupEventListeners();
  await loadDatabases();
  await loadQueries();
}

function setupEventListeners() {
  // DB Switcher: Preserve modified SQL when user switches databases
  dom.dbSelect.addEventListener("change", async (e) => {
    state.activeDbId = e.target.value;
    updateDbStatsBadge();
    const preservedSql = dom.sqlEditor.value.trim();
    const prevQueryId = state.activeQueryId;
    await loadQueries({
      preserveEditor: Boolean(preservedSql),
      preservedSql: preservedSql,
      preferredQueryId: prevQueryId
    });
  });

  dom.btnRefreshDbs.addEventListener("click", () => {
    loadDatabases();
  });

  // Suite Mode Tabs
  dom.tabTutoring.addEventListener("click", () => {
    setSuiteMode("tutoring");
  });

  dom.tabComparative.addEventListener("click", () => {
    setSuiteMode("comparative");
  });

  // Search & Filter
  dom.searchInput.addEventListener("input", (e) => {
    state.searchQuery = e.target.value.toLowerCase();
    renderSidebar();
  });

  dom.levelFilters.addEventListener("click", (e) => {
    if (e.target.classList.contains("pill-btn")) {
      dom.levelFilters.querySelectorAll(".pill-btn").forEach(btn => btn.classList.remove("active"));
      e.target.classList.add("active");
      state.activeLevel = e.target.dataset.level;
      renderSidebar();
    }
  });

  // Tutor Notes Toggle
  const btnToggleTutor = document.getElementById("btn-toggle-tutor");
  const tutorCard = document.getElementById("tutor-card");
  if (btnToggleTutor && tutorCard) {
    btnToggleTutor.addEventListener("click", () => {
      const isCollapsed = tutorCard.classList.toggle("is-collapsed");
      btnToggleTutor.textContent = isCollapsed ? "+ Expand Notes" : "− Collapse Notes";
    });
  }

  // SQL Editor Actions
  dom.btnRunQuery.addEventListener("click", () => executeActiveQuery());
  dom.btnResetQuery.addEventListener("click", () => resetActiveQuery());
  dom.btnCopySql.addEventListener("click", () => copySqlToClipboard());
  dom.btnDownloadCsv.addEventListener("click", () => exportResultsAsCsv());

  // Keyboard shortcut: Ctrl+Enter / Cmd+Enter runs query, Tab indents
  dom.sqlEditor.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      executeActiveQuery();
    } else if (e.key === "Tab") {
      e.preventDefault();
      const start = dom.sqlEditor.selectionStart;
      const end = dom.sqlEditor.selectionEnd;
      dom.sqlEditor.value = dom.sqlEditor.value.substring(0, start) + "  " + dom.sqlEditor.value.substring(end);
      dom.sqlEditor.selectionStart = dom.sqlEditor.selectionEnd = start + 2;
      updateLineNumbers();
    }
  });

  dom.sqlEditor.addEventListener("input", () => {
    updateLineNumbers();
  });

  dom.sqlEditor.addEventListener("scroll", () => {
    dom.lineNumbers.scrollTop = dom.sqlEditor.scrollTop;
  });
}

function updateLineNumbers() {
  const lines = dom.sqlEditor.value.split("\n").length;
  dom.lineNumbers.textContent = Array.from({ length: lines }, (_, i) => i + 1).join("\n");
}

function setSuiteMode(suite) {
  state.activeSuite = suite;
  dom.tabTutoring.classList.toggle("active", suite === "tutoring");
  dom.tabComparative.classList.toggle("active", suite === "comparative");
  loadQueries();
}

// --- Data Fetching ---
async function loadDatabases() {
  try {
    const res = await fetch("/api/dbs");
    const dbs = await res.json();
    state.databases = dbs;

    dom.dbSelect.innerHTML = "";
    if (dbs.length === 0) {
      dom.dbSelect.innerHTML = "<option value=''>No databases found in dbs/</option>";
      return;
    }

    dbs.forEach(db => {
      const opt = document.createElement("option");
      opt.value = db.id;
      const langLabel = db.language !== "unknown" ? db.language.toUpperCase() : "Custom";
      const symLabel = db.symbol_count ? ` (${db.symbol_count.toLocaleString()} symbols)` : "";
      opt.textContent = `${langLabel}: ${db.id}${symLabel}`;
      dom.dbSelect.appendChild(opt);
    });

    if (!state.activeDbId && dbs.length > 0) {
      state.activeDbId = dbs[0].id;
    }
    dom.dbSelect.value = state.activeDbId;
    updateDbStatsBadge();
  } catch (err) {
    showError("Failed to discover databases: " + err.message);
  }
}

function updateDbStatsBadge() {
  const currentDb = state.databases.find(d => d.id === state.activeDbId);
  if (currentDb) {
    const syms = currentDb.symbol_count ? `${currentDb.symbol_count.toLocaleString()} symbols` : "SQLite DB";
    dom.dbStatsBadge.textContent = `${currentDb.language || 'DB'} • ${syms}`;
    dom.statDbId.textContent = currentDb.id;
  }
}

async function loadQueries(options = {}) {
  try {
    const url = `/api/queries?db_id=${encodeURIComponent(state.activeDbId)}&suite=${encodeURIComponent(state.activeSuite)}`;
    const res = await fetch(url);
    const queries = await res.json();
    state.queries = queries;

    renderSidebar();

    // If options specify to preserve editor SQL across database switch
    if (options.preserveEditor && options.preservedSql) {
      dom.sqlEditor.value = options.preservedSql;
      updateLineNumbers();

      const matchingQuery = queries.find(q => q.id === options.preferredQueryId);
      if (matchingQuery) {
        state.activeQueryId = matchingQuery.id;
        updateTutorCard(matchingQuery);
      }
      executeActiveQuery();
    } else if (queries.length > 0) {
      selectQuery(queries[0].id);
    } else {
      clearWorkspace();
    }
  } catch (err) {
    showError("Failed to load curriculum queries: " + err.message);
  }
}

// --- Sidebar Rendering ---
function renderSidebar() {
  dom.queryList.innerHTML = "";

  const filtered = state.queries.filter(q => {
    const matchesLevel = state.activeLevel === "all" || q.level.toLowerCase() === state.activeLevel.toLowerCase();
    const matchesSearch = !state.searchQuery ||
      q.title.toLowerCase().includes(state.searchQuery) ||
      (q.category && q.category.toLowerCase().includes(state.searchQuery));
    return matchesLevel && matchesSearch;
  });

  if (filtered.length === 0) {
    dom.queryList.innerHTML = "<div class='loading-state'>No matching queries found.</div>";
    return;
  }

  filtered.forEach(q => {
    const card = document.createElement("div");
    card.className = "query-card" + (q.id === state.activeQueryId ? " active" : "");
    card.onclick = () => selectQuery(q.id);

    const top = document.createElement("div");
    top.className = "query-card-top";

    const seq = document.createElement("span");
    seq.className = "query-sequence";
    seq.textContent = `LESSON ${q.sequence}`;

    const level = document.createElement("span");
    level.className = "query-level-pill";
    level.textContent = q.level;

    top.appendChild(seq);
    top.appendChild(level);

    const title = document.createElement("div");
    title.className = "query-card-title";
    title.textContent = q.title;

    const cat = document.createElement("div");
    cat.className = "query-card-cat";
    cat.textContent = q.category || q.suite;

    card.appendChild(top);
    card.appendChild(title);
    card.appendChild(cat);

    dom.queryList.appendChild(card);
  });
}

// --- Query Selection & Rationale Display ---
function updateTutorCard(q) {
  // Update active card styling
  document.querySelectorAll(".query-card").forEach(el => el.classList.remove("active"));
  const activeEl = Array.from(document.querySelectorAll(".query-card")).find(
    el => el.querySelector(".query-card-title")?.textContent === q.title
  );
  if (activeEl) activeEl.classList.add("active");

  // Populate Tutor Card
  dom.lessonTitle.textContent = q.title;
  dom.lessonLevelBadge.textContent = q.level;
  dom.lessonLangBadge.textContent = q.target_language.toUpperCase();
  dom.lessonCategoryBadge.textContent = q.category || q.suite;
  dom.lessonRationale.textContent = q.pedagogical_rationale || "No rationale specified.";

  // Populate Guided Experiments
  dom.guidedExperiments.innerHTML = "";
  if (q.guided_experiments && q.guided_experiments.length > 0) {
    q.guided_experiments.forEach(exp => {
      const li = document.createElement("li");
      li.textContent = exp;
      dom.guidedExperiments.appendChild(li);
    });
  } else {
    const li = document.createElement("li");
    li.textContent = "Try modifying the WHERE, JOIN, or GROUP BY clauses to explore specific records.";
    dom.guidedExperiments.appendChild(li);
  }
}

function selectQuery(queryId) {
  state.activeQueryId = queryId;
  const q = state.queries.find(item => item.id === queryId);
  if (!q) return;

  updateTutorCard(q);

  // Populate SQL Editor
  dom.sqlEditor.value = q.sql.trim();
  updateLineNumbers();

  // Run automatically on selection
  executeActiveQuery();
}

function clearWorkspace() {
  dom.lessonTitle.textContent = "No queries in this suite";
  dom.lessonRationale.textContent = "Switch mode or select another database from the dropdown.";
  dom.guidedExperiments.innerHTML = "<li>No experiments available.</li>";
  dom.sqlEditor.value = "";
  updateLineNumbers();
}

// --- Query Execution ---
async function executeActiveQuery() {
  const sql = dom.sqlEditor.value.trim();
  if (!sql) {
    showError("SQL query is empty.");
    return;
  }
  if (!state.activeDbId) {
    showError("No active database selected.");
    return;
  }

  hideError();
  dom.btnRunQuery.disabled = true;
  dom.btnRunQuery.textContent = "Executing...";

  try {
    const res = await fetch("/api/execute", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ db_id: state.activeDbId, sql: sql })
    });

    const data = await res.json();

    if (data.error) {
      showError(data.error);
      renderTable([], []);
      updateStats(0, 0, false);
      dom.btnDownloadCsv.disabled = true;
    } else {
      hideError();
      state.lastResults = data;
      updateStats(data.row_count, data.execution_time_ms, data.has_more);
      renderTable(data.columns, data.rows);
      dom.btnDownloadCsv.disabled = data.rows.length === 0;
    }
  } catch (err) {
    showError("Network/Server execution error: " + err.message);
  } finally {
    dom.btnRunQuery.disabled = false;
    dom.btnRunQuery.textContent = "▶ Run Query";
  }
}

function resetActiveQuery() {
  const q = state.queries.find(item => item.id === state.activeQueryId);
  if (q) {
    dom.sqlEditor.value = q.sql.trim();
    updateLineNumbers();
    executeActiveQuery();
  }
}

function copySqlToClipboard() {
  navigator.clipboard.writeText(dom.sqlEditor.value);
  const orig = dom.btnCopySql.textContent;
  dom.btnCopySql.textContent = "✓ Copied!";
  setTimeout(() => dom.btnCopySql.textContent = orig, 1500);
}

// --- Stats & Table Rendering ---
function updateStats(rowCount, timeMs, isTruncated) {
  dom.statRowCount.textContent = (rowCount || 0).toLocaleString();
  dom.statExecutionTime.textContent = `${timeMs || 0} ms`;
  dom.badgeTruncated.classList.toggle("hidden", !isTruncated);
}

function renderTable(columns, rows) {
  dom.tableHead.innerHTML = "";
  dom.tableBody.innerHTML = "";

  if (!columns || columns.length === 0) {
    const th = document.createElement("th");
    th.textContent = "No columns returned";
    dom.tableHead.appendChild(th);

    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.className = "empty-state";
    td.textContent = "No records found.";
    tr.appendChild(td);
    dom.tableBody.appendChild(tr);
    return;
  }

  // Header
  columns.forEach(col => {
    const th = document.createElement("th");
    th.textContent = col;
    dom.tableHead.appendChild(th);
  });

  // Body
  if (rows.length === 0) {
    const tr = document.createElement("tr");
    const td = document.createElement("td");
    td.colSpan = columns.length;
    td.className = "empty-state";
    td.textContent = "Query executed successfully. 0 rows returned.";
    tr.appendChild(td);
    dom.tableBody.appendChild(tr);
    return;
  }

  rows.forEach(row => {
    const tr = document.createElement("tr");
    row.forEach(val => {
      const td = document.createElement("td");
      if (val === null || val === undefined) {
        td.className = "null-value";
        td.textContent = "NULL";
      } else {
        td.textContent = typeof val === "object" ? JSON.stringify(val) : String(val);
      }
      tr.appendChild(td);
    });
    dom.tableBody.appendChild(tr);
  });
}

function showError(msg) {
  dom.errorMessage.textContent = msg;
  dom.errorBanner.classList.remove("hidden");
}

function hideError() {
  dom.errorBanner.classList.add("hidden");
}

// --- Client-side CSV Blob Exporter ---
function exportResultsAsCsv() {
  if (!state.lastResults || !state.lastResults.columns || state.lastResults.rows.length === 0) {
    return;
  }

  const cols = state.lastResults.columns;
  const rows = state.lastResults.rows;

  const escapeCell = (cell) => {
    if (cell === null || cell === undefined) return "";
    const str = String(cell);
    if (str.includes(",") || str.includes('"') || str.includes("\n")) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  };

  const csvContent = [
    cols.map(escapeCell).join(","),
    ...rows.map(row => row.map(escapeCell).join(","))
  ].join("\n");

  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `utss_export_${state.activeDbId}_${Date.now()}.csv`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

// Start application
window.addEventListener("DOMContentLoaded", init);
