import {
  DatabaseInfo,
  QueryInfo,
  ExecuteResponse,
  BridgeConcept,
  BridgeLookupResponse,
  TranslateRequest,
  TranslateResponse,
  GraphResponse,
  ComparativeAnalysisData,
  TranspileSnippetResponse,
  GradeLabRequest,
  GradeLabResponse,
  AstFlowResponse,
  CompilerPipelineResponse,
  StdlibCoverageResponse,
  CustomRuleTestRequest,
  CustomRuleTestResponse,
  LabStatsResponse,
  CertificateResponse
} from "./types";

export async function fetchDatabases(): Promise<DatabaseInfo[]> {
  const res = await fetch("/api/dbs");
  if (!res.ok) throw new Error(`Failed to load databases (${res.status})`);
  return res.json();
}

export async function fetchQueries(dbId?: string, suite: string = "tutoring"): Promise<QueryInfo[]> {
  const params = new URLSearchParams({ suite });
  if (dbId) params.append("db_id", dbId);
  const res = await fetch(`/api/queries?${params.toString()}`);
  if (!res.ok) throw new Error(`Failed to load queries (${res.status})`);
  return res.json();
}

export async function executeQuery(dbId: string, sql: string, limit: number = 500): Promise<ExecuteResponse> {
  const res = await fetch("/api/execute", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ db_id: dbId, sql, limit })
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const errorMsg = data.error || data.detail || `Server error (${res.status})`;
    return {
      error: typeof errorMsg === "string" ? errorMsg : JSON.stringify(errorMsg),
      db_id: dbId
    };
  }
  return data;
}

export async function fetchBridgeConcepts(category?: string): Promise<BridgeConcept[]> {
  const url = category ? `/api/bridge/concepts?category=${encodeURIComponent(category)}` : "/api/bridge/concepts";
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed to load bridge concepts (${res.status})`);
  return res.json();
}

export async function fetchBridgeLookup(conceptKey: string): Promise<BridgeLookupResponse> {
  const res = await fetch(`/api/bridge/lookup?concept_key=${encodeURIComponent(conceptKey)}`);
  if (!res.ok) throw new Error(`Failed to lookup concept '${conceptKey}' (${res.status})`);
  return res.json();
}

export async function translateBridge(req: TranslateRequest): Promise<TranslateResponse> {
  const res = await fetch("/api/bridge/translate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req)
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Translation failed (${res.status})`);
  }
  return data;
}

export async function fetchContainerGraph(dbId: string): Promise<GraphResponse> {
  const res = await fetch(`/api/graph/containers?db_id=${encodeURIComponent(dbId)}`);
  if (!res.ok) throw new Error(`Failed to load container graph (${res.status})`);
  return res.json();
}

export async function fetchInheritanceGraph(dbId: string): Promise<GraphResponse> {
  const res = await fetch(`/api/graph/inheritance?db_id=${encodeURIComponent(dbId)}`);
  if (!res.ok) throw new Error(`Failed to load inheritance graph (${res.status})`);
  return res.json();
}

export async function fetchConceptCluster(conceptKey: string): Promise<GraphResponse> {
  const res = await fetch(`/api/graph/concept-cluster?concept_key=${encodeURIComponent(conceptKey)}`);
  if (!res.ok) throw new Error(`Failed to load concept cluster (${res.status})`);
  return res.json();
}

export async function fetchComparativeAnalysis(variant: string = "recommended"): Promise<ComparativeAnalysisData> {
  const res = await fetch(`/api/analysis/comparative?variant=${encodeURIComponent(variant)}`);
  if (!res.ok) throw new Error(`Failed to load comparative analysis (${res.status})`);
  return res.json();
}

export async function fetchAnalysisReport(variant: string = "recommended"): Promise<string> {
  const res = await fetch(`/api/analysis/report?variant=${encodeURIComponent(variant)}`);
  if (!res.ok) throw new Error(`Failed to load analysis report (${res.status})`);
  return res.text();
}

export async function transpileSnippet(
  pythonCode: string,
  targetLanguages?: string[]
): Promise<TranspileSnippetResponse> {
  const res = await fetch("/api/bridge/transpile", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      python_code: pythonCode,
      target_languages: targetLanguages
    })
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Transpilation failed (${res.status})`);
  }
  return res.json();
}

export async function gradeLabQuery(req: GradeLabRequest): Promise<GradeLabResponse> {
  const res = await fetch("/api/lab/grade", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req)
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Lab grading failed (${res.status})`);
  }
  return data;
}

export async function fetchAstFlow(pythonCode: string): Promise<AstFlowResponse> {
  const res = await fetch("/api/bridge/ast-flow", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ python_code: pythonCode })
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const errorMsg = data.detail?.message || data.detail || `AST Flow failed (${res.status})`;
    throw new Error(typeof errorMsg === "string" ? errorMsg : JSON.stringify(errorMsg));
  }
  return data;
}

export async function fetchCompilerPipeline(pythonCode: string, targetLanguage: string = "rust"): Promise<CompilerPipelineResponse> {
  const res = await fetch("/api/bridge/pipeline-passes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ python_code: pythonCode, target_language: targetLanguage })
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const errorMsg = data.detail?.message || data.detail || `Compiler pipeline failed (${res.status})`;
    throw new Error(typeof errorMsg === "string" ? errorMsg : JSON.stringify(errorMsg));
  }
  return data;
}

export async function exportProjectScaffold(
  pythonCode: string,
  target: string,
  projectName?: string
): Promise<Blob> {
  const res = await fetch("/api/bridge/export-project", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      python_code: pythonCode,
      target,
      project_name: projectName || "rosetta_transpiled",
    }),
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({ detail: "Export failed" }));
    throw new Error(data.detail || "Failed to export project archive");
  }
  return await res.blob();
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

export async function fetchStdlibCoverage(): Promise<StdlibCoverageResponse> {
  const res = await fetch("/api/bridge/stdlib-coverage");
  if (!res.ok) {
    throw new Error(`Failed to load stdlib coverage (${res.status})`);
  }
  return await res.json();
}

export async function crawlStdlib(): Promise<StdlibCoverageResponse> {
  const res = await fetch("/api/bridge/crawl-stdlib", { method: "POST" });
  if (!res.ok) {
    throw new Error(`Failed to run stdlib harvest (${res.status})`);
  }
  return await res.json();
}

export async function testCustomTranspilationRule(req: CustomRuleTestRequest): Promise<CustomRuleTestResponse> {
  const res = await fetch("/api/bridge/test-custom-rule", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Custom rule test failed (${res.status})`);
  }
  return data;
}

export async function fetchLabStats(): Promise<LabStatsResponse> {
  const res = await fetch("/api/lab/stats");
  if (!res.ok) {
    throw new Error(`Failed to load lab statistics (${res.status})`);
  }
  return await res.json();
}

export async function generateCertificate(
  studentName: string,
  completedQueryIds: string[]
): Promise<CertificateResponse> {
  const res = await fetch("/api/lab/certificate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      student_name: studentName,
      completed_query_ids: completedQueryIds
    }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || `Failed to generate certificate (${res.status})`);
  }
  return data;
}






