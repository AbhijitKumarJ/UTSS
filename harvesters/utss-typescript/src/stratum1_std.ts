import { DatabaseSync } from "node:sqlite";

export interface StdHarvestResult {
  containersHarvested: number;
  symbolsHarvested: number;
  callablesHarvested: number;
  parametersHarvested: number;
}

interface ParamSpec {
  name: string;
  type: string;
  passKind?: string;
  isOptional?: boolean;
  defaultExpr?: string;
}

interface FuncSpec {
  name: string;
  sig: string;
  ret: string;
  isAsync?: boolean;
  doc?: string;
  params: ParamSpec[];
}

interface ClassSpec {
  name: string;
  doc?: string;
  methods: FuncSpec[];
}

interface ModuleSpec {
  name: string;
  doc: string;
  functions?: FuncSpec[];
  classes?: ClassSpec[];
}

export function harvestStratum1Std(
  db: DatabaseSync,
  envId: number,
  isFull: boolean
): StdHarvestResult {
  const distName = "node_stdlib";
  const distVersion = process.versions.node;

  // Insert or get Distribution
  const insertDist = db.prepare(`
    INSERT INTO distributions (
      env_id, stratum, dist_name, dist_version, summary
    ) VALUES (?, 1, ?, ?, ?)
    ON CONFLICT(env_id, stratum, dist_name, dist_version)
    DO UPDATE SET summary = excluded.summary
    RETURNING dist_id;
  `);

  const summary = isFull
    ? "Node.js and ECMAScript Full Standard Distribution (46 native modules)"
    : "Node.js and ECMAScript Curated Tier-1 Standard Modules";

  const distRow = insertDist.get(envId, distName, distVersion, summary) as { dist_id: number };
  const distId = Number(distRow.dist_id);

  // Prepare insertion statements
  const insertContainer = db.prepare(`
    INSERT INTO containers (
      dist_id, parent_container_id, container_kind, qualified_name, short_name, requires_import, visibility, docstring
    ) VALUES (?, ?, ?, ?, ?, 1, 'public', ?)
    ON CONFLICT(dist_id, qualified_name)
    DO UPDATE SET docstring = excluded.docstring
    RETURNING container_id;
  `);

  const insertContainerFacet = db.prepare(`
    INSERT OR REPLACE INTO ts_container_facets (
      container_id, item_kind, is_export, is_default_export, is_ambient, is_abstract
    ) VALUES (?, ?, 1, 0, 1, 0);
  `);

  const insertSymbol = db.prepare(`
    INSERT INTO symbols (
      container_id, name, qualified_name, symbol_kind, visibility, provenance, docstring
    ) VALUES (?, ?, ?, ?, 'public', 'std_item', ?)
    ON CONFLICT(container_id, name)
    DO UPDATE SET symbol_kind = excluded.symbol_kind
    RETURNING symbol_id;
  `);

  const insertSymbolFacet = db.prepare(`
    INSERT OR REPLACE INTO ts_symbol_facets (
      symbol_id, member_kind, access_modifier, is_readonly, is_optional, is_abstract, is_override, is_declare, type_annotation_json, modifiers_json
    ) VALUES (?, ?, 'public', ?, ?, 0, 0, 1, ?, ?);
  `);

  const insertCallable = db.prepare(`
    INSERT OR REPLACE INTO callables (
      symbol_id, is_async, is_generator, is_static, is_class_bound, has_overloads, overload_count, return_type_expr, raw_signature, signature_source
    ) VALUES (?, ?, 0, ?, ?, 0, 0, ?, ?, 'std_metadata');
  `);

  const insertParam = db.prepare(`
    INSERT INTO parameters (
      callable_symbol_id, ordinal, name, pass_kind, type_expr, type_source, default_expr, is_optional
    ) VALUES (?, ?, ?, ?, ?, 'std_metadata', ?, ?);
  `);

  let containersHarvested = 0;
  let symbolsHarvested = 0;
  let callablesHarvested = 0;
  let parametersHarvested = 0;

  function recordFunction(
    containerId: number,
    moduleName: string,
    f: FuncSpec,
    isMethod = false,
    isStatic = false,
    parentClassName?: string
  ) {
    const qName = parentClassName
      ? `${moduleName}::${parentClassName}.${f.name}`
      : `${moduleName}::${f.name}`;

    const symKind = isMethod ? "method" : "function";
    const symRow = insertSymbol.get(
      containerId,
      f.name,
      qName,
      symKind,
      f.doc || `Standard library ${symKind} '${f.name}'`
    ) as { symbol_id: number };
    const symId = Number(symRow.symbol_id);
    symbolsHarvested++;

    insertSymbolFacet.run(
      symId,
      symKind,
      0,
      0,
      JSON.stringify({ returnType: f.ret }),
      JSON.stringify(isStatic ? ["static", "declare"] : ["declare"])
    );

    insertCallable.run(
      symId,
      f.isAsync ? 1 : 0,
      isStatic ? 1 : 0,
      parentClassName ? 1 : 0,
      f.ret,
      f.sig
    );
    callablesHarvested++;

    let ord = 0;
    for (const p of f.params) {
      insertParam.run(
        symId,
        ord++,
        p.name,
        p.passKind || (p.isOptional ? "optional" : "val"),
        p.type,
        p.defaultExpr || null,
        p.isOptional ? 1 : 0
      );
      parametersHarvested++;
    }
  }

  function recordClass(containerId: number, moduleName: string, c: ClassSpec) {
    const classQName = `${moduleName}::${c.name}`;
    const classRow = insertContainer.get(
      distId,
      containerId,
      "class",
      classQName,
      c.name,
      c.doc || `Standard library class '${c.name}'`
    ) as { container_id: number };
    const classContainerId = Number(classRow.container_id);
    containersHarvested++;

    insertContainerFacet.run(classContainerId, "class");

    const symRow = insertSymbol.get(
      containerId,
      c.name,
      classQName,
      "class",
      c.doc || `Standard library class '${c.name}'`
    ) as { symbol_id: number };
    const symId = Number(symRow.symbol_id);
    symbolsHarvested++;

    insertSymbolFacet.run(symId, "constructor", 0, 0, JSON.stringify({ className: c.name }), JSON.stringify(["declare"]));

    for (const m of c.methods) {
      recordFunction(classContainerId, moduleName, m, true, false, c.name);
    }
  }

  function recordModule(m: ModuleSpec) {
    const modRow = insertContainer.get(
      distId,
      null,
      "module",
      m.name,
      m.name,
      m.doc
    ) as { container_id: number };
    const modContainerId = Number(modRow.container_id);
    containersHarvested++;

    insertContainerFacet.run(modContainerId, "module");

    if (m.functions) {
      for (const f of m.functions) {
        recordFunction(modContainerId, m.name, f);
      }
    }

    if (m.classes) {
      for (const c of m.classes) {
        recordClass(modContainerId, m.name, c);
      }
    }
  }

  // Define Recommended Tier-1 Modules
  const recommendedModules: ModuleSpec[] = [
    {
      name: "node:fs",
      doc: "Node.js File System module for POSIX and Windows file I/O operations",
      functions: [
        {
          name: "readFileSync",
          sig: "readFileSync(path: PathOrFileDescriptor, options?: { encoding?: BufferEncoding; flag?: string } | BufferEncoding): string | Buffer",
          ret: "string | Buffer",
          params: [
            { name: "path", type: "PathOrFileDescriptor" },
            { name: "options", type: "{ encoding?: BufferEncoding; flag?: string } | BufferEncoding", isOptional: true }
          ]
        },
        {
          name: "writeFileSync",
          sig: "writeFileSync(file: PathOrFileDescriptor, data: string | NodeJS.ArrayBufferView, options?: WriteFileOptions): void",
          ret: "void",
          params: [
            { name: "file", type: "PathOrFileDescriptor" },
            { name: "data", type: "string | NodeJS.ArrayBufferView" },
            { name: "options", type: "WriteFileOptions", isOptional: true }
          ]
        },
        {
          name: "existsSync",
          sig: "existsSync(path: PathLike): boolean",
          ret: "boolean",
          params: [{ name: "path", type: "PathLike" }]
        },
        {
          name: "statSync",
          sig: "statSync(path: PathLike, options?: StatSyncOptions): Stats",
          ret: "Stats",
          params: [
            { name: "path", type: "PathLike" },
            { name: "options", type: "StatSyncOptions", isOptional: true }
          ]
        },
        {
          name: "readdirSync",
          sig: "readdirSync(path: PathLike, options?: { encoding?: BufferEncoding; withFileTypes?: boolean }): string[] | Dirent[]",
          ret: "string[] | Dirent[]",
          params: [
            { name: "path", type: "PathLike" },
            { name: "options", type: "{ encoding?: BufferEncoding; withFileTypes?: boolean }", isOptional: true }
          ]
        },
        {
          name: "mkdirSync",
          sig: "mkdirSync(path: PathLike, options?: MakeDirectoryOptions): string | undefined",
          ret: "string | undefined",
          params: [
            { name: "path", type: "PathLike" },
            { name: "options", type: "MakeDirectoryOptions", isOptional: true }
          ]
        },
        {
          name: "rmSync",
          sig: "rmSync(path: PathLike, options?: RmOptions): void",
          ret: "void",
          params: [
            { name: "path", type: "PathLike" },
            { name: "options", type: "RmOptions", isOptional: true }
          ]
        }
      ]
    },
    {
      name: "node:fs/promises",
      doc: "Node.js File System promises API for asynchronous non-blocking I/O",
      functions: [
        {
          name: "readFile",
          sig: "readFile(path: PathLike | FileHandle, options?: { encoding?: BufferEncoding; flag?: string } | BufferEncoding): Promise<string | Buffer>",
          ret: "Promise<string | Buffer>",
          isAsync: true,
          params: [
            { name: "path", type: "PathLike | FileHandle" },
            { name: "options", type: "{ encoding?: BufferEncoding; flag?: string } | BufferEncoding", isOptional: true }
          ]
        },
        {
          name: "writeFile",
          sig: "writeFile(file: PathLike | FileHandle, data: string | Uint8Array, options?: WriteFileOptions): Promise<void>",
          ret: "Promise<void>",
          isAsync: true,
          params: [
            { name: "file", type: "PathLike | FileHandle" },
            { name: "data", type: "string | Uint8Array" },
            { name: "options", type: "WriteFileOptions", isOptional: true }
          ]
        },
        {
          name: "stat",
          sig: "stat(path: PathLike, options?: StatOptions): Promise<Stats>",
          ret: "Promise<Stats>",
          isAsync: true,
          params: [
            { name: "path", type: "PathLike" },
            { name: "options", type: "StatOptions", isOptional: true }
          ]
        },
        {
          name: "mkdir",
          sig: "mkdir(path: PathLike, options?: MakeDirectoryOptions): Promise<string | undefined>",
          ret: "Promise<string | undefined>",
          isAsync: true,
          params: [
            { name: "path", type: "PathLike" },
            { name: "options", type: "MakeDirectoryOptions", isOptional: true }
          ]
        }
      ]
    },
    {
      name: "node:path",
      doc: "Node.js Path utilities for handling and transforming file paths",
      functions: [
        {
          name: "join",
          sig: "join(...paths: string[]): string",
          ret: "string",
          params: [{ name: "paths", type: "string[]", passKind: "rest" }]
        },
        {
          name: "resolve",
          sig: "resolve(...paths: string[]): string",
          ret: "string",
          params: [{ name: "paths", type: "string[]", passKind: "rest" }]
        },
        {
          name: "basename",
          sig: "basename(path: string, suffix?: string): string",
          ret: "string",
          params: [
            { name: "path", type: "string" },
            { name: "suffix", type: "string", isOptional: true }
          ]
        },
        {
          name: "dirname",
          sig: "dirname(path: string): string",
          ret: "string",
          params: [{ name: "path", type: "string" }]
        },
        {
          name: "extname",
          sig: "extname(path: string): string",
          ret: "string",
          params: [{ name: "path", type: "string" }]
        },
        {
          name: "normalize",
          sig: "normalize(path: string): string",
          ret: "string",
          params: [{ name: "path", type: "string" }]
        },
        {
          name: "isAbsolute",
          sig: "isAbsolute(path: string): boolean",
          ret: "boolean",
          params: [{ name: "path", type: "string" }]
        },
        {
          name: "relative",
          sig: "relative(from: string, to: string): string",
          ret: "string",
          params: [
            { name: "from", type: "string" },
            { name: "to", type: "string" }
          ]
        }
      ]
    },
    {
      name: "node:events",
      doc: "Node.js event emitter pattern and asynchronous event handling",
      classes: [
        {
          name: "EventEmitter",
          doc: "Node.js EventEmitter class for pub/sub asynchronous patterns",
          methods: [
            {
              name: "on",
              sig: "on(eventName: string | symbol, listener: (...args: any[]) => void): this",
              ret: "this",
              params: [
                { name: "eventName", type: "string | symbol" },
                { name: "listener", type: "(...args: any[]) => void" }
              ]
            },
            {
              name: "once",
              sig: "once(eventName: string | symbol, listener: (...args: any[]) => void): this",
              ret: "this",
              params: [
                { name: "eventName", type: "string | symbol" },
                { name: "listener", type: "(...args: any[]) => void" }
              ]
            },
            {
              name: "emit",
              sig: "emit(eventName: string | symbol, ...args: any[]): boolean",
              ret: "boolean",
              params: [
                { name: "eventName", type: "string | symbol" },
                { name: "args", type: "any[]", passKind: "rest" }
              ]
            },
            {
              name: "removeListener",
              sig: "removeListener(eventName: string | symbol, listener: (...args: any[]) => void): this",
              ret: "this",
              params: [
                { name: "eventName", type: "string | symbol" },
                { name: "listener", type: "(...args: any[]) => void" }
              ]
            },
            {
              name: "listenerCount",
              sig: "listenerCount(eventName: string | symbol): number",
              ret: "number",
              params: [{ name: "eventName", type: "string | symbol" }]
            }
          ]
        }
      ]
    },
    {
      name: "node:crypto",
      doc: "Node.js Cryptographic functionality including OpenSSL wrappers",
      functions: [
        {
          name: "randomBytes",
          sig: "randomBytes(size: number, callback?: (err: Error | null, buf: Buffer) => void): Buffer",
          ret: "Buffer",
          params: [
            { name: "size", type: "number" },
            { name: "callback", type: "(err: Error | null, buf: Buffer) => void", isOptional: true }
          ]
        },
        {
          name: "randomUUID",
          sig: "randomUUID(): string",
          ret: "string",
          params: []
        },
        {
          name: "createHash",
          sig: "createHash(algorithm: string, options?: HashOptions): Hash",
          ret: "Hash",
          params: [
            { name: "algorithm", type: "string" },
            { name: "options", type: "HashOptions", isOptional: true }
          ]
        },
        {
          name: "createHmac",
          sig: "createHmac(algorithm: string, key: BinaryLike | KeyObject, options?: HmacOptions): Hmac",
          ret: "Hmac",
          params: [
            { name: "algorithm", type: "string" },
            { name: "key", type: "BinaryLike | KeyObject" },
            { name: "options", type: "HmacOptions", isOptional: true }
          ]
        }
      ]
    },
    {
      name: "node:stream",
      doc: "Node.js stream processing primitives: Readable, Writable, Transform",
      functions: [
        {
          name: "pipeline",
          sig: "pipeline(...streams: any[]): Promise<void>",
          ret: "Promise<void>",
          isAsync: true,
          params: [{ name: "streams", type: "any[]", passKind: "rest" }]
        }
      ],
      classes: [
        {
          name: "Readable",
          doc: "Stream reader interface",
          methods: [
            {
              name: "read",
              sig: "read(size?: number): any",
              ret: "any",
              params: [{ name: "size", type: "number", isOptional: true }]
            },
            {
              name: "pipe",
              sig: "pipe<T extends NodeJS.WritableStream>(destination: T, options?: { end?: boolean }): T",
              ret: "T",
              params: [
                { name: "destination", type: "T" },
                { name: "options", type: "{ end?: boolean }", isOptional: true }
              ]
            }
          ]
        },
        {
          name: "Writable",
          doc: "Stream writer interface",
          methods: [
            {
              name: "write",
              sig: "write(chunk: any, encoding?: BufferEncoding, cb?: (error: Error | null | undefined) => void): boolean",
              ret: "boolean",
              params: [
                { name: "chunk", type: "any" },
                { name: "encoding", type: "BufferEncoding", isOptional: true },
                { name: "cb", type: "(error: Error | null | undefined) => void", isOptional: true }
              ]
            },
            {
              name: "end",
              sig: "end(cb?: () => void): this",
              ret: "this",
              params: [{ name: "cb", type: "() => void", isOptional: true }]
            }
          ]
        }
      ]
    },
    {
      name: "node:buffer",
      doc: "Node.js Buffer binary buffer manipulation and conversion",
      classes: [
        {
          name: "Buffer",
          doc: "Buffer instance representing raw memory allocated outside V8 heap",
          methods: [
            {
              name: "from",
              sig: "from(arrayBuffer: WithImplicitCoercion<ArrayBuffer | SharedArrayBuffer>, byteOffset?: number, length?: number): Buffer",
              ret: "Buffer",
              params: [
                { name: "arrayBuffer", type: "ArrayBuffer | SharedArrayBuffer" },
                { name: "byteOffset", type: "number", isOptional: true },
                { name: "length", type: "number", isOptional: true }
              ]
            },
            {
              name: "alloc",
              sig: "alloc(size: number, fill?: string | Buffer | number, encoding?: BufferEncoding): Buffer",
              ret: "Buffer",
              params: [
                { name: "size", type: "number" },
                { name: "fill", type: "string | Buffer | number", isOptional: true },
                { name: "encoding", type: "BufferEncoding", isOptional: true }
              ]
            },
            {
              name: "byteLength",
              sig: "byteLength(string: string | NodeJS.ArrayBufferView | ArrayBuffer | SharedArrayBuffer, encoding?: BufferEncoding): number",
              ret: "number",
              params: [
                { name: "string", type: "string | ArrayBuffer" },
                { name: "encoding", type: "BufferEncoding", isOptional: true }
              ]
            }
          ]
        }
      ]
    },
    {
      name: "node:util",
      doc: "Node.js internal utility functions: promisify, format, inspect",
      functions: [
        {
          name: "promisify",
          sig: "promisify<TCustom extends Function>(fn: TCustom): TCustom",
          ret: "Function",
          params: [{ name: "fn", type: "Function" }]
        },
        {
          name: "format",
          sig: "format(format?: any, ...param: any[]): string",
          ret: "string",
          params: [
            { name: "format", type: "any", isOptional: true },
            { name: "param", type: "any[]", passKind: "rest" }
          ]
        },
        {
          name: "inspect",
          sig: "inspect(object: any, options?: InspectOptions): string",
          ret: "string",
          params: [
            { name: "object", type: "any" },
            { name: "options", type: "InspectOptions", isOptional: true }
          ]
        }
      ]
    },
    {
      name: "node:os",
      doc: "Node.js operating-system-related utility methods and properties",
      functions: [
        { name: "platform", sig: "platform(): NodeJS.Platform", ret: "NodeJS.Platform", params: [] },
        { name: "arch", sig: "arch(): string", ret: "string", params: [] },
        { name: "cpus", sig: "cpus(): CpuInfo[]", ret: "CpuInfo[]", params: [] },
        { name: "totalmem", sig: "totalmem(): number", ret: "number", params: [] },
        { name: "freemem", sig: "freemem(): number", ret: "number", params: [] },
        { name: "homedir", sig: "homedir(): string", ret: "string", params: [] },
        { name: "tmpdir", sig: "tmpdir(): string", ret: "string", params: [] }
      ]
    },
    {
      name: "node:http",
      doc: "Node.js HTTP server and client implementation",
      functions: [
        {
          name: "createServer",
          sig: "createServer(requestListener?: RequestListener): Server",
          ret: "Server",
          params: [{ name: "requestListener", type: "RequestListener", isOptional: true }]
        },
        {
          name: "request",
          sig: "request(url: string | URL, options?: RequestOptions, cb?: (res: IncomingMessage) => void): ClientRequest",
          ret: "ClientRequest",
          params: [
            { name: "url", type: "string | URL" },
            { name: "options", type: "RequestOptions", isOptional: true },
            { name: "cb", type: "(res: IncomingMessage) => void", isOptional: true }
          ]
        }
      ]
    },
    {
      name: "node:process",
      doc: "Node.js current process control and information object",
      functions: [
        { name: "cwd", sig: "cwd(): string", ret: "string", params: [] },
        { name: "exit", sig: "exit(code?: number): never", ret: "never", params: [{ name: "code", type: "number", isOptional: true }] },
        { name: "uptime", sig: "uptime(): number", ret: "number", params: [] },
        { name: "memoryUsage", sig: "memoryUsage(): NodeJS.MemoryUsage", ret: "NodeJS.MemoryUsage", params: [] }
      ]
    }
  ];

  for (const m of recommendedModules) {
    recordModule(m);
  }

  // If full standard library requested, add all remaining 35+ native modules
  if (isFull) {
    const additionalModules = [
      "node:assert", "node:async_hooks", "node:child_process", "node:cluster",
      "node:console", "node:constants", "node:dgram", "node:diagnostics_channel",
      "node:dns", "node:domain", "node:http2", "node:https", "node:inspector",
      "node:module", "node:net", "node:perf_hooks", "node:punycode",
      "node:querystring", "node:readline", "node:repl", "node:sqlite",
      "node:stream/promises", "node:string_decoder", "node:test", "node:timers",
      "node:timers/promises", "node:tls", "node:trace_events", "node:tty",
      "node:url", "node:v8", "node:vm", "node:wasi", "node:worker_threads", "node:zlib"
    ];

    for (const modName of additionalModules) {
      recordModule({
        name: modName,
        doc: `Node.js native standard library module '${modName}'`,
        functions: [
          {
            name: "default",
            sig: `export default from '${modName}'`,
            ret: "any",
            params: []
          }
        ]
      });
    }
  }

  return {
    containersHarvested,
    symbolsHarvested,
    callablesHarvested,
    parametersHarvested
  };
}
