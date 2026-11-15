import { DatabaseSync } from "node:sqlite";
import ts from "typescript";

export interface HarvestResult {
  envId: number;
  distId: number;
  containerId: number;
  keywordCount: number;
  primitiveCount: number;
  utilityTypeCount: number;
  globalCount: number;
}

export function harvestStratum0Ambient(db: DatabaseSync): HarvestResult {
  const nodeVersion = process.versions.node;
  const [nodeMajor, nodeMinor, nodePatch] = nodeVersion.split(".").map((n) => parseInt(n, 10) || 0);
  const tsVersion = ts.version || "5.7.3";
  const platform = `${process.arch}-${process.platform}`;

  // 1. Insert or get Environment
  const insertEnv = db.prepare(`
    INSERT INTO environments (
      language, runtime_name, language_version,
      version_major, version_minor, version_micro,
      platform_triplet, sys_platform, executable_path
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(language, runtime_name, language_version, platform_triplet, executable_path)
    DO UPDATE SET captured_at = CURRENT_TIMESTAMP
    RETURNING env_id;
  `);

  const envRow = insertEnv.get(
    "typescript",
    "node",
    tsVersion,
    nodeMajor,
    nodeMinor,
    nodePatch,
    platform,
    process.platform,
    process.execPath
  ) as { env_id: number };

  const envId = Number(envRow.env_id);

  // 2. Insert Distribution for Stratum 0 (<ambient>)
  const insertDist = db.prepare(`
    INSERT INTO distributions (
      env_id, stratum, dist_name, dist_version, summary
    ) VALUES (?, 0, '<ambient>', ?, 'TypeScript and ECMAScript ambient scope: keywords, primitives, utility types, and standard globals')
    ON CONFLICT(env_id, stratum, dist_name, dist_version)
    DO UPDATE SET summary = excluded.summary
    RETURNING dist_id;
  `);

  const distRow = insertDist.get(envId, tsVersion) as { dist_id: number };
  const distId = Number(distRow.dist_id);

  // 3. Insert Container for <ambient>
  const insertContainer = db.prepare(`
    INSERT INTO containers (
      dist_id, container_kind, qualified_name, short_name, requires_import, visibility, docstring
    ) VALUES (?, 'ambient_scope', '<ambient>', '<ambient>', 0, 'public', 'TypeScript and ECMAScript root ambient scope')
    ON CONFLICT(dist_id, qualified_name)
    DO UPDATE SET docstring = excluded.docstring
    RETURNING container_id;
  `);

  const containerRow = insertContainer.get(distId) as { container_id: number };
  const containerId = Number(containerRow.container_id);

  // 3b. Insert Container Facet
  const insertContainerFacet = db.prepare(`
    INSERT OR REPLACE INTO ts_container_facets (
      container_id, item_kind, is_export, is_default_export, is_ambient, is_abstract
    ) VALUES (?, 'ambient_scope', 0, 0, 1, 0);
  `);
  insertContainerFacet.run(containerId);

  // Prepare symbol insertion statements
  const insertSymbol = db.prepare(`
    INSERT INTO symbols (
      container_id, name, qualified_name, symbol_kind, visibility, provenance, docstring
    ) VALUES (?, ?, ?, ?, 'public', ?, ?)
    ON CONFLICT(container_id, name)
    DO UPDATE SET symbol_kind = excluded.symbol_kind
    RETURNING symbol_id;
  `);

  const insertSymbolFacet = db.prepare(`
    INSERT OR REPLACE INTO ts_symbol_facets (
      symbol_id, member_kind, access_modifier, is_readonly, is_optional, is_abstract, is_override, is_declare, type_annotation_json, modifiers_json
    ) VALUES (?, ?, 'public', ?, 0, 0, 0, 1, ?, ?);
  `);

  const insertCallable = db.prepare(`
    INSERT OR REPLACE INTO callables (
      symbol_id, is_async, is_generator, is_static, is_class_bound, has_overloads, overload_count, type_params_json, return_type_expr, raw_signature, signature_source
    ) VALUES (?, ?, 0, 1, 0, 0, 0, ?, ?, ?, 'ambient');
  `);

  const insertParam = db.prepare(`
    INSERT INTO parameters (
      callable_symbol_id, ordinal, name, pass_kind, type_expr, type_source, default_expr, is_optional
    ) VALUES (?, ?, ?, ?, ?, 'ambient', ?, ?);
  `);

  const insertStateMember = db.prepare(`
    INSERT OR REPLACE INTO state_members (
      symbol_id, declared_type_expr, runtime_type_name, is_constant, is_mutable, literal_value_repr, access_mode
    ) VALUES (?, ?, ?, ?, ?, ?, ?);
  `);

  // --- A. KEYWORDS ---
  const strictKeywords = [
    "break", "case", "catch", "class", "const", "continue", "debugger", "default",
    "delete", "do", "else", "export", "extends", "false", "finally", "for",
    "function", "if", "import", "in", "instanceof", "new", "null", "return",
    "super", "switch", "this", "throw", "true", "try", "typeof", "var",
    "void", "while", "with"
  ];

  const contextualKeywords = [
    "abstract", "any", "as", "asserts", "async", "await", "bigint", "boolean",
    "constructor", "declare", "enum", "from", "get", "implements", "infer",
    "interface", "is", "keyof", "module", "namespace", "never", "number",
    "object", "override", "package", "private", "protected", "public",
    "readonly", "satisfies", "set", "string", "symbol", "type", "undefined",
    "unique", "unknown", "using", "yield"
  ];

  let keywordCount = 0;
  for (const kw of [...new Set([...strictKeywords, ...contextualKeywords])]) {
    const symRow = insertSymbol.get(
      containerId,
      kw,
      `<ambient>::${kw}`,
      "keyword",
      "ambient_keyword",
      `TypeScript / ECMAScript keyword '${kw}'`
    ) as { symbol_id: number };
    const symId = Number(symRow.symbol_id);
    insertSymbolFacet.run(symId, "keyword", 1, null, JSON.stringify(["keyword"]));
    keywordCount++;
  }

  // --- B. PRIMITIVE TYPES ---
  const primitives = [
    { name: "string", doc: "Primitive string type representing textual UTF-16 data" },
    { name: "number", doc: "Primitive number type representing double-precision 64-bit IEEE 754 float" },
    { name: "boolean", doc: "Primitive boolean type (true or false)" },
    { name: "bigint", doc: "Primitive arbitrary-precision integer type" },
    { name: "symbol", doc: "Primitive unique and immutable identifier type" },
    { name: "undefined", doc: "Primitive type for uninitialized or missing values" },
    { name: "null", doc: "Primitive type representing intentional absence of object value" },
    { name: "any", doc: "TypeScript escape hatch type disabling type checking" },
    { name: "unknown", doc: "TypeScript type-safe counterpart of any requiring narrowing" },
    { name: "never", doc: "TypeScript bottom type representing values that never occur" },
    { name: "void", doc: "Return type indicating absence of return value" },
    { name: "object", doc: "TypeScript type representing any non-primitive value" }
  ];

  let primitiveCount = 0;
  for (const prim of primitives) {
    const symRow = insertSymbol.get(
      containerId,
      prim.name,
      `<ambient>::${prim.name}`,
      "primitive_type",
      "ambient_primitive",
      prim.doc
    ) as { symbol_id: number };
    const symId = Number(symRow.symbol_id);
    insertSymbolFacet.run(symId, "primitive", 1, JSON.stringify({ type: prim.name }), JSON.stringify(["primitive"]));
    primitiveCount++;
  }

  // --- C. UTILITY TYPES ---
  const utilityTypes = [
    { name: "Partial", params: '["T"]', doc: "Constructs a type with all properties of T set to optional" },
    { name: "Required", params: '["T"]', doc: "Constructs a type with all properties of T set to required" },
    { name: "Readonly", params: '["T"]', doc: "Constructs a type with all properties of T set to readonly" },
    { name: "Record", params: '["K extends keyof any", "T"]', doc: "Constructs an object type whose keys are K and values are T" },
    { name: "Pick", params: '["T", "K extends keyof T"]', doc: "Constructs a type by picking keys K from type T" },
    { name: "Omit", params: '["T", "K extends keyof any"]', doc: "Constructs a type by picking all properties from T and then removing K" },
    { name: "Exclude", params: '["T", "U"]', doc: "Excludes from T those types that are assignable to U" },
    { name: "Extract", params: '["T", "U"]', doc: "Extracts from T those types that are assignable to U" },
    { name: "NonNullable", params: '["T"]', doc: "Constructs a type by excluding null and undefined from T" },
    { name: "Parameters", params: '["T extends (...args: any) => any"]', doc: "Obtains the parameters of a function type in a tuple" },
    { name: "ConstructorParameters", params: '["T extends abstract new (...args: any) => any"]', doc: "Obtains parameters of a constructor function type" },
    { name: "ReturnType", params: '["T extends (...args: any) => any"]', doc: "Obtains the return type of a function type" },
    { name: "InstanceType", params: '["T extends abstract new (...args: any) => any"]', doc: "Obtains the instance type of a constructor function type" },
    { name: "ThisParameterType", params: '["T"]', doc: "Extracts the type of the this parameter of a function type" },
    { name: "OmitThisParameter", params: '["T"]', doc: "Removes the this parameter from a function type" },
    { name: "ThisType", params: '["T"]', doc: "Marker for contextual this type in object literals" },
    { name: "Uppercase", params: '["S extends string"]', doc: "Convert string literal type to uppercase" },
    { name: "Lowercase", params: '["S extends string"]', doc: "Convert string literal type to lowercase" },
    { name: "Capitalize", params: '["S extends string"]', doc: "Convert first character of string literal type to uppercase" },
    { name: "Uncapitalize", params: '["S extends string"]', doc: "Convert first character of string literal type to lowercase" },
    { name: "Awaited", params: '["T"]', doc: "Recursively unwraps Promise types" }
  ];

  let utilityTypeCount = 0;
  for (const util of utilityTypes) {
    const symRow = insertSymbol.get(
      containerId,
      util.name,
      `<ambient>::${util.name}`,
      "utility_type",
      "ambient_utility_type",
      util.doc
    ) as { symbol_id: number };
    const symId = Number(symRow.symbol_id);
    insertSymbolFacet.run(symId, "type_alias", 1, JSON.stringify({ typeParams: util.params }), JSON.stringify(["type"]));
    utilityTypeCount++;
  }

  // --- D. GLOBAL RUNTIME BUILTINS & FUNCTIONS ---
  const singletons = [
    { name: "globalThis", type: "typeof globalThis", doc: "Universal global scope object" },
    { name: "console", type: "Console", doc: "Console debugging facility" },
    { name: "Math", type: "Math", doc: "Mathematical constants and functions" },
    { name: "JSON", type: "JSON", doc: "JavaScript Object Notation serializer/parser" },
    { name: "Reflect", type: "typeof Reflect", doc: "Methods for interceptable JavaScript operations" },
    { name: "Atomics", type: "Atomics", doc: "Atomic operations on SharedArrayBuffer" },
    { name: "Intl", type: "typeof Intl", doc: "ECMAScript Internationalization API namespace" }
  ];

  const standardConstructors = [
    "Object", "Function", "Boolean", "Symbol", "Error", "AggregateError",
    "EvalError", "RangeError", "ReferenceError", "SyntaxError", "TypeError", "URIError",
    "Number", "BigInt", "Date", "String", "RegExp", "Array", "Int8Array", "Uint8Array",
    "Uint8ClampedArray", "Int16Array", "Uint16Array", "Int32Array", "Uint32Array",
    "Float32Array", "Float64Array", "BigInt64Array", "BigUint64Array", "Map", "Set",
    "WeakMap", "WeakSet", "ArrayBuffer", "SharedArrayBuffer", "DataView", "Promise", "Proxy"
  ];

  const globalFunctions = [
    { name: "eval", sig: "eval(script: string): any", ret: "any", params: [{ name: "script", type: "string" }] },
    { name: "isFinite", sig: "isFinite(number: number): boolean", ret: "boolean", params: [{ name: "number", type: "number" }] },
    { name: "isNaN", sig: "isNaN(number: number): boolean", ret: "boolean", params: [{ name: "number", type: "number" }] },
    { name: "parseFloat", sig: "parseFloat(string: string): number", ret: "number", params: [{ name: "string", type: "string" }] },
    { name: "parseInt", sig: "parseInt(string: string, radix?: number): number", ret: "number", params: [{ name: "string", type: "string" }, { name: "radix", type: "number", opt: true }] },
    { name: "decodeURI", sig: "decodeURI(encodedURI: string): string", ret: "string", params: [{ name: "encodedURI", type: "string" }] },
    { name: "decodeURIComponent", sig: "decodeURIComponent(encodedURIComponent: string): string", ret: "string", params: [{ name: "encodedURIComponent", type: "string" }] },
    { name: "encodeURI", sig: "encodeURI(uri: string): string", ret: "string", params: [{ name: "uri", type: "string" }] },
    { name: "encodeURIComponent", sig: "encodeURIComponent(uriComponent: string): string", ret: "string", params: [{ name: "uriComponent", type: "string" }] },
    { name: "structuredClone", sig: "structuredClone<T>(value: T, options?: StructuredSerializeOptions): T", ret: "T", params: [{ name: "value", type: "T" }, { name: "options", type: "StructuredSerializeOptions", opt: true }] },
    { name: "fetch", sig: "fetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response>", ret: "Promise<Response>", isAsync: 1, params: [{ name: "input", type: "RequestInfo | URL" }, { name: "init", type: "RequestInit", opt: true }] },
    { name: "setTimeout", sig: "setTimeout(handler: TimerHandler, timeout?: number, ...args: any[]): NodeJS.Timeout", ret: "NodeJS.Timeout", params: [{ name: "handler", type: "TimerHandler" }, { name: "timeout", type: "number", opt: true }] },
    { name: "clearTimeout", sig: "clearTimeout(id?: NodeJS.Timeout): void", ret: "void", params: [{ name: "id", type: "NodeJS.Timeout", opt: true }] },
    { name: "setInterval", sig: "setInterval(handler: TimerHandler, timeout?: number, ...args: any[]): NodeJS.Timeout", ret: "NodeJS.Timeout", params: [{ name: "handler", type: "TimerHandler" }, { name: "timeout", type: "number", opt: true }] },
    { name: "clearInterval", sig: "clearInterval(id?: NodeJS.Timeout): void", ret: "void", params: [{ name: "id", type: "NodeJS.Timeout", opt: true }] },
    { name: "queueMicrotask", sig: "queueMicrotask(callback: () => void): void", ret: "void", params: [{ name: "callback", type: "() => void" }] }
  ];

  let globalCount = 0;

  for (const s of singletons) {
    const symRow = insertSymbol.get(
      containerId,
      s.name,
      `<ambient>::${s.name}`,
      "constant",
      "ambient_builtin",
      s.doc
    ) as { symbol_id: number };
    const symId = Number(symRow.symbol_id);
    insertSymbolFacet.run(symId, "variable", 1, JSON.stringify({ type: s.type }), JSON.stringify(["const"]));
    insertStateMember.run(symId, s.type, s.name, 1, 0, null, "read_only");
    globalCount++;
  }

  for (const c of standardConstructors) {
    const symRow = insertSymbol.get(
      containerId,
      c,
      `<ambient>::${c}`,
      "class",
      "ambient_builtin",
      `Standard JavaScript built-in constructor '${c}'`
    ) as { symbol_id: number };
    const symId = Number(symRow.symbol_id);
    insertSymbolFacet.run(symId, "constructor", 0, JSON.stringify({ name: c }), JSON.stringify(["declare"]));
    insertCallable.run(symId, 0, null, `${c}Constructor`, `new ${c}(...args: any[])`);
    globalCount++;
  }

  for (const f of globalFunctions) {
    const symRow = insertSymbol.get(
      containerId,
      f.name,
      `<ambient>::${f.name}`,
      "function",
      "ambient_builtin",
      `Global function '${f.name}'`
    ) as { symbol_id: number };
    const symId = Number(symRow.symbol_id);
    insertSymbolFacet.run(symId, "function", 0, JSON.stringify({ returnType: f.ret }), JSON.stringify(["declare"]));
    insertCallable.run(symId, f.isAsync || 0, null, f.ret, f.sig);
    let ord = 0;
    for (const p of f.params) {
      insertParam.run(symId, ord++, p.name, p.opt ? "optional" : "val", p.type, null, p.opt ? 1 : 0);
    }
    globalCount++;
  }

  return {
    envId,
    distId,
    containerId,
    keywordCount,
    primitiveCount,
    utilityTypeCount,
    globalCount
  };
}
