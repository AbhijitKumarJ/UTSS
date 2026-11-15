export interface EnvironmentRecord {
  env_id?: number;
  language: string;
  runtime_name: string;
  language_version: string;
  version_major: number;
  version_minor: number;
  version_micro: number;
  platform_triplet: string;
  sys_platform: string;
  executable_path: string;
  captured_at?: string;
}

export interface DistributionRecord {
  dist_id?: number;
  env_id: number;
  stratum: number;
  dist_name: string;
  dist_version: string;
  summary?: string | null;
}

export interface ContainerRecord {
  container_id?: number;
  dist_id: number;
  parent_container_id?: number | null;
  container_kind: string;
  qualified_name: string;
  short_name: string;
  requires_import: number;
  visibility: string;
  is_hidden: number;
  physical_path?: string | null;
  stub_path?: string | null;
  sha256_hash?: string | null;
  start_line?: number | null;
  start_col?: number | null;
  end_line?: number | null;
  end_col?: number | null;
  docstring?: string | null;
}

export interface SymbolRecord {
  symbol_id?: number;
  container_id: number;
  origin_container_id?: number | null;
  name: string;
  qualified_name: string;
  symbol_kind: string;
  visibility: string;
  provenance: string;
  is_hidden: number;
  start_line?: number | null;
  start_col?: number | null;
  end_line?: number | null;
  end_col?: number | null;
  docstring?: string | null;
}

export interface CallableRecord {
  symbol_id: number;
  is_async: number;
  is_generator: number;
  is_static: number;
  is_class_bound: number;
  has_overloads: number;
  overload_count: number;
  type_params_json?: string | null;
  return_type_expr?: string | null;
  raw_signature?: string | null;
  signature_source: string;
}

export interface CallableOverloadRecord {
  overload_id?: number;
  callable_symbol_id: number;
  overload_ordinal: number;
  type_params_json?: string | null;
  return_type_expr?: string | null;
  raw_signature: string;
}

export interface ParameterRecord {
  param_id?: number;
  callable_symbol_id: number;
  overload_id?: number | null;
  ordinal: number;
  name: string;
  pass_kind: string;
  type_expr?: string | null;
  type_source?: string | null;
  default_expr?: string | null;
  is_optional: number;
}

export interface StateMemberRecord {
  symbol_id: number;
  declared_type_expr?: string | null;
  runtime_type_name: string;
  is_constant: number;
  is_mutable: number;
  literal_value_repr?: string | null;
  access_mode: string;
}

export interface SymbolAliasRecord {
  alias_id?: number;
  source_container_id: number;
  exposed_name: string;
  target_module_name: string;
  target_symbol_name: string;
  alias_kind: string;
  is_in_dunder_all: number;
}

export interface TsContainerFacetRecord {
  container_id: number;
  item_kind: string;
  is_export: number;
  is_default_export: number;
  is_ambient: number;
  is_abstract: number;
  type_params_json?: string | null;
  heritage_clauses_json?: string | null;
  modifiers_json?: string | null;
}

export interface TsSymbolFacetRecord {
  symbol_id: number;
  member_kind: string;
  access_modifier: string;
  is_readonly: number;
  is_optional: number;
  is_abstract: number;
  is_override: number;
  is_declare: number;
  type_annotation_json?: string | null;
  modifiers_json?: string | null;
}
