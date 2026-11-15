export type ThemeName = "utss-dark" | "vscode-dark" | "vscode-light" | "monokai";

export interface DatabaseInfo {
  id: string;
  filename: string;
  relative_path: string;
  language: string;
  runtime: string | null;
  version: string | null;
  variant: string | null;
  symbol_count: number;
  container_count: number;
  callable_count: number;
  is_available: boolean;
  tables: string[];
}

export interface LabChallenge {
  objective: string;
  starter_sql?: string;
  solution_sql?: string;
  expected_columns?: string[];
  min_rows?: number;
  max_rows?: number;
  xp_reward?: number;
  hint?: string;
}

export interface GradeLabRequest {
  query_id: string;
  db_id: string;
  student_sql: string;
}

export interface GradeLabDiagnostics {
  execution_success: boolean;
  columns_matched: boolean;
  missing_columns: string[];
  row_count_valid: boolean;
  student_row_count: number;
  expected_min_rows: number;
  expected_row_count?: number | null;
  reference_matched?: boolean;
  error_detail?: string;
}

export interface GradeLabResponse {
  passed: boolean;
  score: number;
  xp_earned: number;
  feedback: string;
  diagnostics: GradeLabDiagnostics;
}

export interface QueryInfo {
  id: string;
  filename: string;
  relative_path: string;
  title: string;
  target_language: string;
  variant_compatibility: string[];
  suite: "tutoring" | "comparative" | string;
  level: "Basic" | "Intermediate" | "Advanced" | string;
  sequence: number;
  category: string;
  pedagogical_rationale: string;
  guided_experiments: string[];
  lab_challenge?: LabChallenge;
  sql: string;
}

export interface ExecuteResponse {
  columns?: string[];
  rows?: any[][];
  row_count?: number;
  has_more?: boolean;
  truncated?: boolean;
  execution_time_ms?: number;
  db_id?: string;
  error?: string;
}

export interface BridgeConcept {
  concept_id: number;
  concept_key: string;
  category: string;
  type_arity: number;
  description: string;
}

export interface BridgeTypeMapping {
  mapping_id: number;
  concept_id: number;
  language: string;
  target_qualified_name: string;
  type_syntax_template: string;
  required_import: string | null;
  memory_model: string;
  nullability_model: string;
  catalog_container_id: number | null;
  catalog_symbol_id: number | null;
  verified_stratum: number | null;
  verification_status: string;
}

export interface BridgeOperationMapping {
  op_mapping_id: number;
  concept_id: number;
  canonical_op: string;
  language: string;
  target_symbol_name: string;
  call_syntax_template: string;
  receiver_pass_kind: string;
  mutates_receiver: number;
  returns_new_value: number;
  catalog_symbol_id: number | null;
  verification_status: string;
}

export interface BridgeLookupResponse {
  concept: BridgeConcept;
  type_mappings: Record<string, BridgeTypeMapping>;
  operation_mappings: Record<string, Record<string, BridgeOperationMapping>>;
  protocol_mappings: Record<string, any>;
}

export interface TranslateRequest {
  source_language: string;
  target_language: string;
  concept_key: string;
  canonical_op?: string;
  receiver?: string;
  args?: string[];
}

export interface TranslateResponse {
  source_language: string;
  target_language: string;
  concept_key: string;
  canonical_op?: string;
  source_expression: string;
  target_expression: string;
  target_type: string;
  required_import: string | null;
  memory_model: string;
  receiver_pass_kind: string;
  impedance_note: string;
}

export interface GraphNode {
  id: string;
  name: string;
  qualified_name: string;
  kind: string;
  visibility?: string;
  stratum?: number;
  symbol_count?: number;
  container_id?: number | null;
  parent_id?: string | null;
  is_external?: boolean;
  is_root?: boolean;
  language?: string;
  syntax_template?: string;
  memory_model?: string;
  nullability_model?: string;
  category?: string;
  description?: string;
  verification_status?: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  relation_kind: "contains" | "extends" | "implements" | "embeds" | "lowers_to" | string;
  label?: string;
}

export interface GraphResponse {
  db_id?: string;
  language?: string;
  concept?: string;
  category?: string;
  description?: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  total_nodes: number;
  total_edges: number;
}

// ----------------------------------------------------------------------------
// Comparative Analysis & Transpiler Impedance Types
// ----------------------------------------------------------------------------

export interface SymbolCensusItem {
  language: string;
  total_symbols: number;
  total_containers: number;
  total_callables: number;
}

export interface MutabilityItem {
  language: string;
  total_members: number;
  constant_members: number;
  immutable_members: number;
  immutability_pct: number;
}

export interface ParameterPassingItem {
  language: string;
  pass_kind: string;
  total_params: number;
}

export interface OverloadingItem {
  language: string;
  total_callables: number;
  overloaded_callables: number;
  max_overload_multiplicity: number;
  avg_overload_multiplicity: number;
}

export interface ErrorHandlingItem {
  language: string;
  exception_types_count: number;
  result_error_callables_count: number;
}

export type PairwiseImpedanceMatrix = Record<string, Record<string, number>>;

export interface ComparativeAnalysisData {
  variant: string;
  languages: string[];
  symbol_census: SymbolCensusItem[];
  mutability_matrix: MutabilityItem[];
  parameter_passing: Record<string, Record<string, number>>;
  overloading_metrics: OverloadingItem[];
  error_handling: ErrorHandlingItem[];
  pairwise_impedance: PairwiseImpedanceMatrix;
}

// ----------------------------------------------------------------------------
// AST Transpiler Engine & Provenance Types
// ----------------------------------------------------------------------------

export type TargetLanguage = "csharp" | "rust" | "typescript" | "cpp" | "go";

export interface ProvenanceRecord {
  construct: string;
  concept_key: string;
  target_language: string;
  resolved_target: string;
  verification_status: string;
  catalog_container_id?: number | null;
  catalog_symbol_id?: number | null;
  catalog_signature?: string | null;
  receiver_pass_kind?: string | null;
}

export interface TargetSynthesisOutput {
  language: TargetLanguage;
  imports: string[];
  statements: string[];
  source_code: string;
  provenance_trace: ProvenanceRecord[];
}

export interface TranspileSnippetResponse {
  source_python: string;
  targets: Record<TargetLanguage, TargetSynthesisOutput>;
}

export interface AstFlowNode {
  id: string;
  node_type: string;
  label: string;
  line_start?: number | null;
  line_end?: number | null;
  col_offset?: number | null;
  ir_concept?: string | null;
  source_snippet?: string;
  lowering_previews: Record<string, string>;
  children: AstFlowNode[];
}

export interface AstFlowResponse {
  root: AstFlowNode;
  node_count: number;
  max_depth: number;
  concepts_detected: string[];
}

export interface CompilerPassInfo {
  pass_id: string;
  name: string;
  stage: string;
  status: string;
  summary: string;
  metrics: Record<string, any>;
  artifacts: Record<string, any>;
}

export interface CompilerPipelineResponse {
  source_code: string;
  target_language: TargetLanguage | string;
  passes: CompilerPassInfo[];
}

// ----------------------------------------------------------------------------
// Stdlib Taxonomy & Unmapped Ecosystem Types
// ----------------------------------------------------------------------------

export interface UnmappedTaxonomyCandidate {
  language: string;
  qualified_name: string;
  short_name: string;
  domain: string;
  entity_kind: string;
  public_methods: number;
  proposed_concept: string;
  impedance_risk: "LOW" | "MEDIUM" | "HIGH";
  impedance_notes: string;
}

export interface LanguageCoverageStats {
  total_containers: number;
  mapped_count: number;
  unmapped_count: number;
  coverage_pct: number;
  sample_unmapped: UnmappedTaxonomyCandidate[];
}

export interface StdlibCoverageResponse {
  languages: Record<string, LanguageCoverageStats>;
  domain_distribution: Record<string, number>;
  total_unmapped_candidates: number;
  unmapped_candidates: UnmappedTaxonomyCandidate[];
}

// ----------------------------------------------------------------------------
// Custom Rule Playground & Empirical Impedance Types
// ----------------------------------------------------------------------------

export interface CustomRuleTestRequest {
  python_code: string;
  target_language: TargetLanguage | string;
  rule_name: string;
  base_concept_key: string;
  target_type_name: string;
  type_syntax_template: string;
  required_import?: string;
  memory_model: string;
  nullability_model: string;
  custom_operations: Record<string, string>;
}

export interface CustomRuleScoreFactors {
  memory_safety: number;
  mutability_contract: number;
  import_resolution: number;
  template_integrity: number;
}

export interface CustomRuleTestResponse {
  rule_name: string;
  target_language: string;
  source_python: string;
  emitted_code: string;
  injected_imports: string[];
  impedance_score: number;
  impedance_risk: "LOW" | "MEDIUM" | "HIGH";
  score_factors: CustomRuleScoreFactors;
  diagnostics: string[];
}

// ----------------------------------------------------------------------------
// Curriculum Lab Stats & Certificate Types
// ----------------------------------------------------------------------------

export interface LabChallengeSummary {
  id: string;
  title: string;
  suite: string;
  level: string;
  category: string;
  xp_reward: number;
  objective: string;
}

export interface LabStatsResponse {
  total_challenges: number;
  total_xp_available: number;
  challenges: LabChallengeSummary[];
}

export interface CertificateBadge {
  title: string;
  icon: string;
}

export interface CertificateResponse {
  student_name: string;
  issue_date: string;
  total_solved: number;
  total_challenges: number;
  total_xp_earned: number;
  total_xp_available: number;
  mastery_tier: string;
  completion_ratio: number;
  verification_token: string;
  badges: CertificateBadge[];
  is_graduated: boolean;
}





