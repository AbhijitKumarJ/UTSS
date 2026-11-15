import { DatabaseSync } from "node:sqlite";
import ts from "typescript";
import * as crypto from "node:crypto";
import * as path from "node:path";
import * as fs from "node:fs";

export interface WorkspaceHarvestResult {
  distId: number;
  filesProcessed: number;
  containersHarvested: number;
  symbolsHarvested: number;
  callablesHarvested: number;
  overloadsHarvested: number;
  parametersHarvested: number;
  stateMembersHarvested: number;
  aliasesHarvested: number;
}

export const EMBEDDED_DEMO_WORKSPACE: Record<string, string> = {
  "src/models/order.ts": `// E-Commerce Order domain model
export enum OrderStatus {
  Draft = "DRAFT",
  Pending = "PENDING",
  Paid = "PAID",
  Shipped = "SHIPPED",
  Delivered = "DELIVERED",
  Cancelled = "CANCELLED"
}

export type CustomerId = string;

export interface IOrderLine {
  sku: string;
  quantity: number;
  unitPrice: number;
}

export class Order {
  public readonly id: string;
  public customerId: CustomerId;
  public status: OrderStatus;
  private _secretSecurityToken: string;
  private items: IOrderLine[];

  constructor(id: string, customerId: CustomerId) {
    this.id = id;
    this.customerId = customerId;
    this.status = OrderStatus.Draft;
    this._secretSecurityToken = "tok_" + Math.random();
    this.items = [];
  }

  public addItem(sku: string, quantity: number, unitPrice: number): void {
    this.items.push({ sku, quantity, unitPrice });
  }

  public calculateSubtotal(): number {
    return this.items.reduce((acc, item) => acc + item.quantity * item.unitPrice, 0);
  }

  public get isPaid(): boolean {
    return this.status === OrderStatus.Paid;
  }

  public markPaid(): void {
    this.status = OrderStatus.Paid;
  }
}
`,

  "src/services/order_service.ts": `// Order Processing Engine
import { Order, OrderStatus } from "../models/order.js";

export interface IOrderService {
  processOrder(order: Order): Promise<boolean>;
  streamAuditEvents(): Generator<string, void, unknown>;
}

export class OrderService implements IOrderService {
  private serviceName: string;
  public static readonly VERSION: string = "2.4.0";

  constructor(serviceName: string = "PrimaryEngine") {
    this.serviceName = serviceName;
  }

  public static createDefault(): OrderService {
    return new OrderService("DefaultCommerceEngine");
  }

  public async processOrder(order: Order): Promise<boolean> {
    if (order.status === OrderStatus.Draft) {
      order.markPaid();
      return true;
    }
    return false;
  }

  public *streamAuditEvents(): Generator<string, void, unknown> {
    yield "EVENT_INIT";
    yield "EVENT_RUNNING";
    yield "EVENT_COMPLETE";
  }
}
`,

  "src/index.ts": `// Main library barrel file
export * from "./models/order.js";
export * from "./services/order_service.js";
export { Order as PrimaryOrder } from "./models/order.js";
`,

  "cli_runner.ts": `// Standalone CLI runner
import { Order, OrderStatus } from "./src/models/order.js";
import { OrderService } from "./src/services/order_service.js";

export function main(): void {
  const service = OrderService.createDefault();
  const order = new Order("ord_1001", "cust_99");
  order.addItem("SKU-100", 2, 29.99);
  service.processOrder(order);
}
`
};

export class WorkspaceAstCataloger {
  private db: DatabaseSync;
  private envId: number;

  constructor(db: DatabaseSync, envId: number) {
    this.db = db;
    this.envId = envId;
  }

  public harvestEmbeddedDemo(): WorkspaceHarvestResult {
    const distId = this.ensureDistribution("commerce_engine", "1.0.0", "Embedded TypeScript E-Commerce Workspace");
    return this.harvestVirtualFiles(distId, EMBEDDED_DEMO_WORKSPACE);
  }

  public harvestDirectory(workspaceDir: string, distName = "workspace", distVersion = "0.1.0"): WorkspaceHarvestResult {
    const distId = this.ensureDistribution(distName, distVersion, `Workspace harvested from ${workspaceDir}`);
    const files: Record<string, string> = {};

    const findFiles = (dir: string) => {
      const entries = fs.readdirSync(dir, { withFileTypes: true });
      for (const entry of entries) {
        const fullPath = path.join(dir, entry.name);
        if (entry.isDirectory()) {
          if (!["node_modules", ".git", "dist", "target", "bin", "obj"].includes(entry.name)) {
            findFiles(fullPath);
          }
        } else if (entry.isFile() && (entry.name.endsWith(".ts") || entry.name.endsWith(".tsx") || entry.name.endsWith(".js"))) {
          const relPath = path.relative(workspaceDir, fullPath).replace(/\\/g, "/");
          files[relPath] = fs.readFileSync(fullPath, "utf-8");
        }
      }
    };

    findFiles(workspaceDir);
    return this.harvestVirtualFiles(distId, files);
  }

  private ensureDistribution(distName: string, distVersion: string, summary: string): number {
    const insertDist = this.db.prepare(`
      INSERT INTO distributions (
        env_id, stratum, dist_name, dist_version, summary
      ) VALUES (?, 3, ?, ?, ?)
      ON CONFLICT(env_id, stratum, dist_name, dist_version)
      DO UPDATE SET summary = excluded.summary
      RETURNING dist_id;
    `);

    const distRow = insertDist.get(this.envId, distName, distVersion, summary) as { dist_id: number };
    return Number(distRow.dist_id);
  }

  private harvestVirtualFiles(distId: number, files: Record<string, string>): WorkspaceHarvestResult {
    let filesProcessed = 0;
    let containersHarvested = 0;
    let symbolsHarvested = 0;
    let callablesHarvested = 0;
    let overloadsHarvested = 0;
    let parametersHarvested = 0;
    let stateMembersHarvested = 0;
    let aliasesHarvested = 0;

    // Prepared statements
    const insertContainer = this.db.prepare(`
      INSERT INTO containers (
        dist_id, parent_container_id, container_kind, qualified_name, short_name, requires_import, visibility, physical_path, sha256_hash, start_line, start_col, end_line, end_col, docstring
      ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(dist_id, qualified_name)
      DO UPDATE SET sha256_hash = excluded.sha256_hash
      RETURNING container_id;
    `);

    const insertContainerFacet = this.db.prepare(`
      INSERT OR REPLACE INTO ts_container_facets (
        container_id, item_kind, is_export, is_default_export, is_ambient, is_abstract, type_params_json, heritage_clauses_json, modifiers_json
      ) VALUES (?, ?, ?, ?, 0, ?, ?, ?, ?);
    `);

    const insertSymbol = this.db.prepare(`
      INSERT INTO symbols (
        container_id, origin_container_id, name, qualified_name, symbol_kind, visibility, provenance, start_line, start_col, end_line, end_col, docstring
      ) VALUES (?, ?, ?, ?, ?, ?, 'ast_defined', ?, ?, ?, ?, ?)
      ON CONFLICT(container_id, name)
      DO UPDATE SET symbol_kind = excluded.symbol_kind
      RETURNING symbol_id;
    `);

    const insertSymbolFacet = this.db.prepare(`
      INSERT OR REPLACE INTO ts_symbol_facets (
        symbol_id, member_kind, access_modifier, is_readonly, is_optional, is_abstract, is_override, is_declare, type_annotation_json, modifiers_json
      ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?);
    `);

    const insertCallable = this.db.prepare(`
      INSERT OR REPLACE INTO callables (
        symbol_id, is_async, is_generator, is_static, is_class_bound, has_overloads, overload_count, type_params_json, return_type_expr, raw_signature, signature_source
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'ts_ast');
    `);

    const insertCallableOverload = this.db.prepare(`
      INSERT INTO callable_overloads (
        callable_symbol_id, overload_ordinal, type_params_json, return_type_expr, raw_signature
      ) VALUES (?, ?, ?, ?, ?);
    `);

    const insertParam = this.db.prepare(`
      INSERT INTO parameters (
        callable_symbol_id, overload_id, ordinal, name, pass_kind, type_expr, type_source, default_expr, is_optional
      ) VALUES (?, ?, ?, ?, ?, ?, 'ts_ast', ?, ?);
    `);

    const insertStateMember = this.db.prepare(`
      INSERT OR REPLACE INTO state_members (
        symbol_id, declared_type_expr, runtime_type_name, is_constant, is_mutable, literal_value_repr, access_mode
      ) VALUES (?, ?, ?, ?, ?, ?, ?);
    `);

    const insertAlias = this.db.prepare(`
      INSERT OR REPLACE INTO symbol_aliases (
        source_container_id, exposed_name, target_module_name, target_symbol_name, alias_kind, is_in_dunder_all
      ) VALUES (?, ?, ?, ?, ?, ?);
    `);

    for (const [filePath, content] of Object.entries(files)) {
      filesProcessed++;
      const sha256 = crypto.createHash("sha256").update(content).digest("hex");
      const sourceFile = ts.createSourceFile(
        filePath,
        content,
        ts.ScriptTarget.Latest,
        true,
        filePath.endsWith(".tsx") ? ts.ScriptKind.TSX : ts.ScriptKind.TS
      );

      const moduleQName = filePath.replace(/\.[jt]sx?$/, "").replace(/\//g, "::");
      const fileSpan = getSpan(sourceFile, sourceFile);

      // Insert module container
      const modRow = insertContainer.get(
        distId,
        null,
        "module",
        moduleQName,
        path.basename(filePath),
        "public",
        filePath,
        sha256,
        fileSpan.startLine,
        fileSpan.startCol,
        fileSpan.endLine,
        fileSpan.endCol,
        `TypeScript module '${filePath}'`
      ) as { container_id: number };
      const modContainerId = Number(modRow.container_id);
      containersHarvested++;

      insertContainerFacet.run(modContainerId, "module", 1, 0, 0, null, null, null);

      // Walk Top-Level AST Nodes
      ts.forEachChild(sourceFile, (node) => {
        // 1. Class Declarations
        if (ts.isClassDeclaration(node) && node.name) {
          const className = node.name.text;
          const classQName = `${moduleQName}::${className}`;
          const span = getSpan(sourceFile, node);
          const isExport = hasModifier(node, ts.SyntaxKind.ExportKeyword);
          const isAbstract = hasModifier(node, ts.SyntaxKind.AbstractKeyword);
          const visibility = getAccessModifier(node);

          const heritage = node.heritageClauses?.map((h) => h.getText(sourceFile)) || [];
          const typeParams = node.typeParameters?.map((tp) => tp.getText(sourceFile)) || [];

          const classRow = insertContainer.get(
            distId,
            modContainerId,
            "class",
            classQName,
            className,
            visibility,
            filePath,
            null,
            span.startLine,
            span.startCol,
            span.endLine,
            span.endCol,
            `Class ${className}`
          ) as { container_id: number };
          const classContainerId = Number(classRow.container_id);
          containersHarvested++;

          insertContainerFacet.run(
            classContainerId,
            "class",
            isExport ? 1 : 0,
            hasModifier(node, ts.SyntaxKind.DefaultKeyword) ? 1 : 0,
            isAbstract ? 1 : 0,
            typeParams.length > 0 ? JSON.stringify(typeParams) : null,
            heritage.length > 0 ? JSON.stringify(heritage) : null,
            JSON.stringify(getModifierNames(node))
          );

          // Also register Class as a symbol in the parent module
          const symRow = insertSymbol.get(
            modContainerId,
            classContainerId,
            className,
            classQName,
            "class",
            visibility,
            span.startLine,
            span.startCol,
            span.endLine,
            span.endCol,
            `Class ${className}`
          ) as { symbol_id: number };
          const symId = Number(symRow.symbol_id);
          symbolsHarvested++;

          insertSymbolFacet.run(
            symId,
            "class",
            visibility,
            0,
            0,
            isAbstract ? 1 : 0,
            0,
            JSON.stringify({ heritage }),
            JSON.stringify(getModifierNames(node))
          );

          // Walk Class Members
          node.members.forEach((member) => {
            const memberSpan = getSpan(sourceFile, member);
            const memberVis = getAccessModifier(member);
            const isStatic = hasModifier(member, ts.SyntaxKind.StaticKeyword);
            const isReadonly = hasModifier(member, ts.SyntaxKind.ReadonlyKeyword);
            const isAsync = hasModifier(member, ts.SyntaxKind.AsyncKeyword);
            const isGenerator = !!(member as ts.FunctionLikeDeclaration).asteriskToken;

            // A. Class Constructor
            if (ts.isConstructorDeclaration(member)) {
              const ctorName = "constructor";
              const ctorQName = `${classQName}::constructor`;
              const ctorSymRow = insertSymbol.get(
                classContainerId,
                classContainerId,
                ctorName,
                ctorQName,
                "constructor",
                memberVis,
                memberSpan.startLine,
                memberSpan.startCol,
                memberSpan.endLine,
                memberSpan.endCol,
                `Constructor for ${className}`
              ) as { symbol_id: number };
              const ctorSymId = Number(ctorSymRow.symbol_id);
              symbolsHarvested++;

              insertSymbolFacet.run(
                ctorSymId,
                "constructor",
                memberVis,
                0,
                0,
                0,
                0,
                JSON.stringify({ returnType: className }),
                JSON.stringify(getModifierNames(member))
              );

              insertCallable.run(
                ctorSymId,
                0,
                0,
                0,
                1,
                0,
                0,
                null,
                className,
                member.getText(sourceFile).split("{")[0].trim()
              );
              callablesHarvested++;

              let pOrd = 0;
              for (const param of member.parameters) {
                const pName = param.name.getText(sourceFile);
                const pType = param.type ? param.type.getText(sourceFile) : "any";
                const pOpt = !!param.questionToken || !!param.initializer;
                const pPass = param.dotDotDotToken ? "rest" : pOpt ? "optional" : "val";
                const pDef = param.initializer ? param.initializer.getText(sourceFile) : null;

                insertParam.run(ctorSymId, null, pOrd++, pName, pPass, pType, pDef, pOpt ? 1 : 0);
                parametersHarvested++;
              }
            }

            // B. Class Method
            else if (ts.isMethodDeclaration(member) && member.name) {
              const methodName = member.name.getText(sourceFile);
              const methodQName = `${classQName}::${methodName}`;
              const retType = member.type ? member.type.getText(sourceFile) : "void";

              const mSymRow = insertSymbol.get(
                classContainerId,
                classContainerId,
                methodName,
                methodQName,
                "method",
                memberVis,
                memberSpan.startLine,
                memberSpan.startCol,
                memberSpan.endLine,
                memberSpan.endCol,
                `Method ${methodName}`
              ) as { symbol_id: number };
              const mSymId = Number(mSymRow.symbol_id);
              symbolsHarvested++;

              insertSymbolFacet.run(
                mSymId,
                "method",
                memberVis,
                isReadonly ? 1 : 0,
                member.questionToken ? 1 : 0,
                hasModifier(member, ts.SyntaxKind.AbstractKeyword) ? 1 : 0,
                hasModifier(member, ts.SyntaxKind.OverrideKeyword) ? 1 : 0,
                JSON.stringify({ returnType: retType }),
                JSON.stringify(getModifierNames(member))
              );

              insertCallable.run(
                mSymId,
                isAsync ? 1 : 0,
                isGenerator ? 1 : 0,
                isStatic ? 1 : 0,
                1,
                0,
                0,
                null,
                retType,
                member.getText(sourceFile).split("{")[0].trim()
              );
              callablesHarvested++;

              let pOrd = 0;
              for (const param of member.parameters) {
                const pName = param.name.getText(sourceFile);
                const pType = param.type ? param.type.getText(sourceFile) : "any";
                const pOpt = !!param.questionToken || !!param.initializer;
                const pPass = param.dotDotDotToken ? "rest" : pOpt ? "optional" : "val";
                const pDef = param.initializer ? param.initializer.getText(sourceFile) : null;

                insertParam.run(mSymId, null, pOrd++, pName, pPass, pType, pDef, pOpt ? 1 : 0);
                parametersHarvested++;
              }
            }

            // C. Class Property
            else if (ts.isPropertyDeclaration(member) && member.name) {
              const propName = member.name.getText(sourceFile);
              const propQName = `${classQName}::${propName}`;
              const propType = member.type ? member.type.getText(sourceFile) : "any";

              const pSymRow = insertSymbol.get(
                classContainerId,
                classContainerId,
                propName,
                propQName,
                "property",
                memberVis,
                memberSpan.startLine,
                memberSpan.startCol,
                memberSpan.endLine,
                memberSpan.endCol,
                `Property ${propName}`
              ) as { symbol_id: number };
              const pSymId = Number(pSymRow.symbol_id);
              symbolsHarvested++;

              insertSymbolFacet.run(
                pSymId,
                "property",
                memberVis,
                isReadonly ? 1 : 0,
                member.questionToken ? 1 : 0,
                0,
                0,
                JSON.stringify({ type: propType }),
                JSON.stringify(getModifierNames(member))
              );

              const isConst = isReadonly || isStatic;
              insertStateMember.run(
                pSymId,
                propType,
                "property",
                isConst ? 1 : 0,
                isConst ? 0 : 1,
                member.initializer ? member.initializer.getText(sourceFile) : null,
                isReadonly ? "read_only" : "read_write"
              );
              stateMembersHarvested++;
            }

            // D. Get / Set Accessor
            else if (ts.isGetAccessor(member) && member.name) {
              const propName = member.name.getText(sourceFile);
              const propQName = `${classQName}::${propName}`;
              const propType = member.type ? member.type.getText(sourceFile) : "any";

              const gSymRow = insertSymbol.get(
                classContainerId,
                classContainerId,
                propName,
                propQName,
                "getter",
                memberVis,
                memberSpan.startLine,
                memberSpan.startCol,
                memberSpan.endLine,
                memberSpan.endCol,
                `Getter ${propName}`
              ) as { symbol_id: number };
              const gSymId = Number(gSymRow.symbol_id);
              symbolsHarvested++;

              insertSymbolFacet.run(
                gSymId,
                "getter",
                memberVis,
                1,
                0,
                0,
                0,
                JSON.stringify({ type: propType }),
                JSON.stringify(getModifierNames(member))
              );

              insertStateMember.run(
                gSymId,
                propType,
                "getter",
                1,
                0,
                null,
                "read_only"
              );
              stateMembersHarvested++;
            }
          });
        }

        // 2. Interface Declarations
        else if (ts.isInterfaceDeclaration(node)) {
          const ifaceName = node.name.text;
          const ifaceQName = `${moduleQName}::${ifaceName}`;
          const span = getSpan(sourceFile, node);
          const isExport = hasModifier(node, ts.SyntaxKind.ExportKeyword);
          const heritage = node.heritageClauses?.map((h) => h.getText(sourceFile)) || [];
          const typeParams = node.typeParameters?.map((tp) => tp.getText(sourceFile)) || [];

          const ifaceRow = insertContainer.get(
            distId,
            modContainerId,
            "interface",
            ifaceQName,
            ifaceName,
            "public",
            filePath,
            null,
            span.startLine,
            span.startCol,
            span.endLine,
            span.endCol,
            `Interface ${ifaceName}`
          ) as { container_id: number };
          const ifaceContainerId = Number(ifaceRow.container_id);
          containersHarvested++;

          insertContainerFacet.run(
            ifaceContainerId,
            "interface",
            isExport ? 1 : 0,
            0,
            0,
            typeParams.length > 0 ? JSON.stringify(typeParams) : null,
            heritage.length > 0 ? JSON.stringify(heritage) : null,
            JSON.stringify(getModifierNames(node))
          );

          const symRow = insertSymbol.get(
            modContainerId,
            ifaceContainerId,
            ifaceName,
            ifaceQName,
            "interface",
            "public",
            span.startLine,
            span.startCol,
            span.endLine,
            span.endCol,
            `Interface ${ifaceName}`
          ) as { symbol_id: number };
          const symId = Number(symRow.symbol_id);
          symbolsHarvested++;

          insertSymbolFacet.run(
            symId,
            "interface",
            "public",
            0,
            0,
            0,
            0,
            JSON.stringify({ heritage }),
            JSON.stringify(getModifierNames(node))
          );

          // Walk Interface Members
          node.members.forEach((member) => {
            const memberSpan = getSpan(sourceFile, member);
            if (ts.isPropertySignature(member) && member.name) {
              const pName = member.name.getText(sourceFile);
              const pQName = `${ifaceQName}::${pName}`;
              const pType = member.type ? member.type.getText(sourceFile) : "any";
              const isReadonly = hasModifier(member, ts.SyntaxKind.ReadonlyKeyword);

              const pSymRow = insertSymbol.get(
                ifaceContainerId,
                ifaceContainerId,
                pName,
                pQName,
                "property",
                "public",
                memberSpan.startLine,
                memberSpan.startCol,
                memberSpan.endLine,
                memberSpan.endCol,
                `Interface member ${pName}`
              ) as { symbol_id: number };
              const pSymId = Number(pSymRow.symbol_id);
              symbolsHarvested++;

              insertSymbolFacet.run(
                pSymId,
                "property",
                "public",
                isReadonly ? 1 : 0,
                member.questionToken ? 1 : 0,
                0,
                0,
                JSON.stringify({ type: pType }),
                JSON.stringify(getModifierNames(member))
              );

              insertStateMember.run(
                pSymId,
                pType,
                "interface_property",
                isReadonly ? 1 : 0,
                isReadonly ? 0 : 1,
                null,
                isReadonly ? "read_only" : "read_write"
              );
              stateMembersHarvested++;
            } else if (ts.isMethodSignature(member) && member.name) {
              const mName = member.name.getText(sourceFile);
              const mQName = `${ifaceQName}::${mName}`;
              const retType = member.type ? member.type.getText(sourceFile) : "void";

              const mSymRow = insertSymbol.get(
                ifaceContainerId,
                ifaceContainerId,
                mName,
                mQName,
                "method",
                "public",
                memberSpan.startLine,
                memberSpan.startCol,
                memberSpan.endLine,
                memberSpan.endCol,
                `Interface method ${mName}`
              ) as { symbol_id: number };
              const mSymId = Number(mSymRow.symbol_id);
              symbolsHarvested++;

              insertSymbolFacet.run(
                mSymId,
                "method",
                "public",
                0,
                member.questionToken ? 1 : 0,
                1,
                0,
                JSON.stringify({ returnType: retType }),
                JSON.stringify(getModifierNames(member))
              );

              insertCallable.run(
                mSymId,
                0,
                0,
                0,
                1,
                0,
                0,
                null,
                retType,
                member.getText(sourceFile).trim()
              );
              callablesHarvested++;

              let pOrd = 0;
              for (const param of member.parameters) {
                const pName = param.name.getText(sourceFile);
                const pType = param.type ? param.type.getText(sourceFile) : "any";
                const pOpt = !!param.questionToken;
                insertParam.run(mSymId, null, pOrd++, pName, pOpt ? "optional" : "val", pType, null, pOpt ? 1 : 0);
                parametersHarvested++;
              }
            }
          });
        }

        // 3. Enum Declarations
        else if (ts.isEnumDeclaration(node)) {
          const enumName = node.name.text;
          const enumQName = `${moduleQName}::${enumName}`;
          const span = getSpan(sourceFile, node);
          const isExport = hasModifier(node, ts.SyntaxKind.ExportKeyword);

          const enumRow = insertContainer.get(
            distId,
            modContainerId,
            "enum",
            enumQName,
            enumName,
            "public",
            filePath,
            null,
            span.startLine,
            span.startCol,
            span.endLine,
            span.endCol,
            `Enum ${enumName}`
          ) as { container_id: number };
          const enumContainerId = Number(enumRow.container_id);
          containersHarvested++;

          insertContainerFacet.run(
            enumContainerId,
            "enum",
            isExport ? 1 : 0,
            0,
            0,
            null,
            null,
            JSON.stringify(getModifierNames(node))
          );

          const symRow = insertSymbol.get(
            modContainerId,
            enumContainerId,
            enumName,
            enumQName,
            "enum",
            "public",
            span.startLine,
            span.startCol,
            span.endLine,
            span.endCol,
            `Enum ${enumName}`
          ) as { symbol_id: number };
          const symId = Number(symRow.symbol_id);
          symbolsHarvested++;

          insertSymbolFacet.run(
            symId,
            "enum",
            "public",
            1,
            0,
            0,
            0,
            JSON.stringify({ enumName }),
            JSON.stringify(getModifierNames(node))
          );

          // Enum Members
          node.members.forEach((m) => {
            const mName = m.name.getText(sourceFile);
            const mQName = `${enumQName}::${mName}`;
            const mSpan = getSpan(sourceFile, m);

            const mSymRow = insertSymbol.get(
              enumContainerId,
              enumContainerId,
              mName,
              mQName,
              "enum_member",
              "public",
              mSpan.startLine,
              mSpan.startCol,
              mSpan.endLine,
              mSpan.endCol,
              `Enum variant ${mName}`
            ) as { symbol_id: number };
            const mSymId = Number(mSymRow.symbol_id);
            symbolsHarvested++;

            insertSymbolFacet.run(
              mSymId,
              "enum_member",
              "public",
              1,
              0,
              0,
              0,
              null,
              null
            );

            insertStateMember.run(
              mSymId,
              enumName,
              "enum_member",
              1,
              0,
              m.initializer ? m.initializer.getText(sourceFile) : null,
              "read_only"
            );
            stateMembersHarvested++;
          });
        }

        // 4. Type Alias Declarations
        else if (ts.isTypeAliasDeclaration(node)) {
          const typeName = node.name.text;
          const typeQName = `${moduleQName}::${typeName}`;
          const span = getSpan(sourceFile, node);
          const isExport = hasModifier(node, ts.SyntaxKind.ExportKeyword);
          const typeExpr = node.type.getText(sourceFile);

          const symRow = insertSymbol.get(
            modContainerId,
            null,
            typeName,
            typeQName,
            "type_alias",
            isExport ? "public" : "private",
            span.startLine,
            span.startCol,
            span.endLine,
            span.endCol,
            `Type alias ${typeName} = ${typeExpr}`
          ) as { symbol_id: number };
          const symId = Number(symRow.symbol_id);
          symbolsHarvested++;

          insertSymbolFacet.run(
            symId,
            "type_alias",
            "public",
            1,
            0,
            0,
            0,
            JSON.stringify({ typeExpr }),
            JSON.stringify(getModifierNames(node))
          );
        }

        // 5. Function Declarations
        else if (ts.isFunctionDeclaration(node) && node.name) {
          const funcName = node.name.text;
          const funcQName = `${moduleQName}::${funcName}`;
          const span = getSpan(sourceFile, node);
          const isExport = hasModifier(node, ts.SyntaxKind.ExportKeyword);
          const isAsync = hasModifier(node, ts.SyntaxKind.AsyncKeyword);
          const isGenerator = !!node.asteriskToken;
          const retType = node.type ? node.type.getText(sourceFile) : "void";

          const symRow = insertSymbol.get(
            modContainerId,
            null,
            funcName,
            funcQName,
            "function",
            isExport ? "public" : "private",
            span.startLine,
            span.startCol,
            span.endLine,
            span.endCol,
            `Function ${funcName}`
          ) as { symbol_id: number };
          const symId = Number(symRow.symbol_id);
          symbolsHarvested++;

          insertSymbolFacet.run(
            symId,
            "function",
            isExport ? "public" : "private",
            0,
            0,
            0,
            0,
            JSON.stringify({ returnType: retType }),
            JSON.stringify(getModifierNames(node))
          );

          insertCallable.run(
            symId,
            isAsync ? 1 : 0,
            isGenerator ? 1 : 0,
            1,
            0,
            0,
            0,
            null,
            retType,
            node.getText(sourceFile).split("{")[0].trim()
          );
          callablesHarvested++;

          let pOrd = 0;
          for (const param of node.parameters) {
            const pName = param.name.getText(sourceFile);
            const pType = param.type ? param.type.getText(sourceFile) : "any";
            const pOpt = !!param.questionToken || !!param.initializer;
            const pPass = param.dotDotDotToken ? "rest" : pOpt ? "optional" : "val";
            const pDef = param.initializer ? param.initializer.getText(sourceFile) : null;

            insertParam.run(symId, null, pOrd++, pName, pPass, pType, pDef, pOpt ? 1 : 0);
            parametersHarvested++;
          }
        }

        // 6. Variable Statements (Top-Level Constants & Variables)
        else if (ts.isVariableStatement(node)) {
          const isExport = hasModifier(node, ts.SyntaxKind.ExportKeyword);
          const isConst = !!(node.declarationList.flags & ts.NodeFlags.Const);

          node.declarationList.declarations.forEach((decl) => {
            if (ts.isIdentifier(decl.name)) {
              const varName = decl.name.text;
              const varQName = `${moduleQName}::${varName}`;
              const span = getSpan(sourceFile, decl);
              const varType = decl.type ? decl.type.getText(sourceFile) : "any";

              const symRow = insertSymbol.get(
                modContainerId,
                null,
                varName,
                varQName,
                isConst ? "constant" : "variable",
                isExport ? "public" : "private",
                span.startLine,
                span.startCol,
                span.endLine,
                span.endCol,
                `${isConst ? "Constant" : "Variable"} ${varName}`
              ) as { symbol_id: number };
              const symId = Number(symRow.symbol_id);
              symbolsHarvested++;

              insertSymbolFacet.run(
                symId,
                "variable",
                isExport ? "public" : "private",
                isConst ? 1 : 0,
                0,
                0,
                0,
                JSON.stringify({ type: varType }),
                JSON.stringify(isConst ? ["const"] : ["let"])
              );

              insertStateMember.run(
                symId,
                varType,
                isConst ? "constant" : "variable",
                isConst ? 1 : 0,
                isConst ? 0 : 1,
                decl.initializer ? decl.initializer.getText(sourceFile) : null,
                isConst ? "read_only" : "read_write"
              );
              stateMembersHarvested++;
            }
          });
        }

        // 7. Export Declarations (Re-exports & Barrel Files)
        else if (ts.isExportDeclaration(node)) {
          const modSpecifier = node.moduleSpecifier ? node.moduleSpecifier.getText(sourceFile).replace(/['"]/g, "") : "";
          if (node.exportClause && ts.isNamedExports(node.exportClause)) {
            node.exportClause.elements.forEach((el) => {
              const exposedName = el.name.text;
              const targetName = el.propertyName ? el.propertyName.text : exposedName;
              insertAlias.run(
                modContainerId,
                exposedName,
                modSpecifier,
                targetName,
                "export_reexport",
                1
              );
              aliasesHarvested++;
            });
          } else if (!node.exportClause && modSpecifier) {
            // export * from "..."
            insertAlias.run(
              modContainerId,
              `* from ${modSpecifier}`,
              modSpecifier,
              "*",
              "export_star",
              1
            );
            aliasesHarvested++;
          }
        }

        // 8. Import Declarations
        else if (ts.isImportDeclaration(node)) {
          const modSpecifier = node.moduleSpecifier.getText(sourceFile).replace(/['"]/g, "");
          if (node.importClause?.namedBindings && ts.isNamedImports(node.importClause.namedBindings)) {
            node.importClause.namedBindings.elements.forEach((el) => {
              const exposedName = el.name.text;
              const targetName = el.propertyName ? el.propertyName.text : exposedName;
              insertAlias.run(
                modContainerId,
                exposedName,
                modSpecifier,
                targetName,
                "import_alias",
                0
              );
              aliasesHarvested++;
            });
          }
        }
      });
    }

    return {
      distId,
      filesProcessed,
      containersHarvested,
      symbolsHarvested,
      callablesHarvested,
      overloadsHarvested,
      parametersHarvested,
      stateMembersHarvested,
      aliasesHarvested
    };
  }
}

function getSpan(sourceFile: ts.SourceFile, node: ts.Node): {
  startLine: number;
  startCol: number;
  endLine: number;
  endCol: number;
} {
  const start = sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile));
  const end = sourceFile.getLineAndCharacterOfPosition(node.getEnd());
  return {
    startLine: start.line + 1,
    startCol: start.character + 1,
    endLine: end.line + 1,
    endCol: end.character + 1
  };
}

function hasModifier(node: ts.Node, kind: ts.SyntaxKind): boolean {
  return !!ts.getModifiers(node as ts.HasModifiers)?.some((m) => m.kind === kind);
}

function getAccessModifier(node: ts.Node): string {
  const modifiers = ts.getModifiers(node as ts.HasModifiers);
  if (!modifiers) return "public";
  if (modifiers.some((m) => m.kind === ts.SyntaxKind.PrivateKeyword)) return "private";
  if (modifiers.some((m) => m.kind === ts.SyntaxKind.ProtectedKeyword)) return "protected";
  return "public";
}

function getModifierNames(node: ts.Node): string[] {
  const modifiers = ts.getModifiers(node as ts.HasModifiers);
  if (!modifiers) return [];
  return modifiers.map((m) => ts.SyntaxKind[m.kind]);
}
