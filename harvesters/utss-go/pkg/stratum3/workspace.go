package stratum3

import (
	"bytes"
	"crypto/sha256"
	"database/sql"
	"encoding/hex"
	"fmt"
	"go/ast"
	"go/format"
	"go/parser"
	"go/token"
	"os"
	"path/filepath"
	"strings"
)

type WorkspaceHarvestResult struct {
	DistID              int64
	FilesProcessed      int
	ContainersHarvested int
	SymbolsHarvested    int
	CallablesHarvested  int
	ParametersHarvested int
	StateMembersHarvested int
	AliasesHarvested    int
}

var EmbeddedDemoWorkspace = map[string]string{
	"models/order.go": `package models

type OrderStatus string

const (
	StatusDraft     OrderStatus = "DRAFT"
	StatusPending   OrderStatus = "PENDING"
	StatusPaid      OrderStatus = "PAID"
	StatusShipped   OrderStatus = "SHIPPED"
	StatusDelivered OrderStatus = "DELIVERED"
	StatusCancelled OrderStatus = "CANCELLED"
)

type CustomerID string

type OrderLine struct {
	SKU       string
	Quantity  int
	UnitPrice float64
}

type Order struct {
	ID          string
	CustomerID  CustomerID
	Status      OrderStatus
	items       []OrderLine
	secretToken string
}

func NewOrder(id string, customerID CustomerID) *Order {
	return &Order{
		ID:          id,
		CustomerID:  customerID,
		Status:      StatusDraft,
		items:       make([]OrderLine, 0),
		secretToken: "sec_tok_101",
	}
}

func (o *Order) AddItem(sku string, quantity int, unitPrice float64) {
	o.items = append(o.items, OrderLine{
		SKU:       sku,
		Quantity:  quantity,
		UnitPrice: unitPrice,
	})
}

func (o *Order) CalculateSubtotal() float64 {
	total := 0.0
	for _, item := range o.items {
		total += float64(item.Quantity) * item.UnitPrice
	}
	return total
}

func (o *Order) IsPaid() bool {
	return o.Status == StatusPaid
}

func (o *Order) MarkPaid() {
	o.Status = StatusPaid
}
`,

	"services/order_service.go": `package services

import "commerce_engine/models"

type IOrderService interface {
	ProcessOrder(order *models.Order) (bool, error)
	StreamAuditEvents() []string
}

type OrderService struct {
	ServiceName string
}

func NewOrderService(name string) *OrderService {
	return &OrderService{ServiceName: name}
}

func (s *OrderService) ProcessOrder(order *models.Order) (bool, error) {
	if order.Status == models.StatusDraft {
		order.MarkPaid()
		return true, nil
	}
	return false, nil
}

func (s *OrderService) StreamAuditEvents() []string {
	return []string{"EVENT_INIT", "EVENT_RUNNING", "EVENT_COMPLETE"}
}
`,

	"main.go": `package main

import (
	"commerce_engine/models"
	"commerce_engine/services"
	"fmt"
)

func main() {
	svc := services.NewOrderService("MainEngine")
	ord := models.NewOrder("ord_1001", "cust_99")
	ord.AddItem("SKU-100", 2, 29.99)
	ok, _ := svc.ProcessOrder(ord)
	fmt.Printf("Order processed: %v, Subtotal: %.2f\n", ok, ord.CalculateSubtotal())
}
`,
}

type WorkspaceAstCataloger struct {
	db    *sql.DB
	envID int64
}

func NewWorkspaceAstCataloger(db *sql.DB, envID int64) *WorkspaceAstCataloger {
	return &WorkspaceAstCataloger{db: db, envID: envID}
}

func (c *WorkspaceAstCataloger) HarvestEmbeddedDemo() (*WorkspaceHarvestResult, error) {
	distID, err := c.ensureDistribution("commerce_engine", "1.0.0", "Embedded Go E-Commerce Workspace")
	if err != nil {
		return nil, err
	}
	return c.harvestFiles(distID, EmbeddedDemoWorkspace)
}

func (c *WorkspaceAstCataloger) HarvestDirectory(dirPath, distName, distVersion string) (*WorkspaceHarvestResult, error) {
	distID, err := c.ensureDistribution(distName, distVersion, "Workspace harvested from "+dirPath)
	if err != nil {
		return nil, err
	}

	files := make(map[string]string)
	err = filepath.Walk(dirPath, func(path string, info os.FileInfo, walkErr error) error {
		if walkErr != nil || info.IsDir() {
			if info != nil && info.IsDir() && (info.Name() == "vendor" || info.Name() == ".git") {
				return filepath.SkipDir
			}
			return nil
		}
		if strings.HasSuffix(path, ".go") && !strings.HasSuffix(path, "_test.go") {
			rel, _ := filepath.Rel(dirPath, path)
			content, readErr := os.ReadFile(path)
			if readErr == nil {
				files[filepath.ToSlash(rel)] = string(content)
			}
		}
		return nil
	})
	if err != nil {
		return nil, err
	}

	return c.harvestFiles(distID, files)
}

func (c *WorkspaceAstCataloger) ensureDistribution(distName, distVersion, summary string) (int64, error) {
	insDist := `
		INSERT INTO distributions (env_id, stratum, dist_name, dist_version, summary)
		VALUES (?, 3, ?, ?, ?)
		ON CONFLICT(env_id, stratum, dist_name, dist_version)
		DO UPDATE SET summary = excluded.summary;
	`
	if _, err := c.db.Exec(insDist, c.envID, distName, distVersion, summary); err != nil {
		return 0, fmt.Errorf("failed to insert workspace distribution: %w", err)
	}

	var distID int64
	err := c.db.QueryRow("SELECT dist_id FROM distributions WHERE env_id=? AND stratum=3 AND dist_name=?;", c.envID, distName).Scan(&distID)
	return distID, err
}

func (c *WorkspaceAstCataloger) harvestFiles(distID int64, files map[string]string) (*WorkspaceHarvestResult, error) {
	res := &WorkspaceHarvestResult{DistID: distID}

	// Prepare statements
	stmtCont, err := c.db.Prepare(`
		INSERT INTO containers (
			dist_id, parent_container_id, container_kind, qualified_name, short_name, requires_import, visibility, physical_path, sha256_hash, start_line, start_col, end_line, end_col, docstring
		) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT(dist_id, qualified_name)
		DO UPDATE SET sha256_hash = excluded.sha256_hash
		RETURNING container_id;
	`)
	if err != nil {
		return nil, err
	}
	defer stmtCont.Close()

	stmtContFacet, err := c.db.Prepare(`
		INSERT OR REPLACE INTO go_container_facets (container_id, package_name, item_kind, type_params_json, embedded_fields_json, is_exported)
		VALUES (?, ?, ?, ?, ?, ?);
	`)
	if err != nil {
		return nil, err
	}
	defer stmtContFacet.Close()

	stmtSym, err := c.db.Prepare(`
		INSERT INTO symbols (
			container_id, origin_container_id, name, qualified_name, symbol_kind, visibility, provenance, start_line, start_col, end_line, end_col, docstring
		) VALUES (?, ?, ?, ?, ?, ?, 'ast_defined', ?, ?, ?, ?, ?)
		ON CONFLICT(container_id, name)
		DO UPDATE SET symbol_kind = excluded.symbol_kind
		RETURNING symbol_id;
	`)
	if err != nil {
		return nil, err
	}
	defer stmtSym.Close()

	stmtSymFacet, err := c.db.Prepare(`
		INSERT OR REPLACE INTO go_symbol_facets (symbol_id, member_kind, receiver_kind, receiver_type, is_exported, is_variadic, signature_json)
		VALUES (?, ?, ?, ?, ?, ?, ?);
	`)
	if err != nil {
		return nil, err
	}
	defer stmtSymFacet.Close()

	stmtCal, err := c.db.Prepare(`
		INSERT OR REPLACE INTO callables (
			symbol_id, is_async, is_generator, is_static, is_class_bound, has_overloads, overload_count, return_type_expr, raw_signature, signature_source
		) VALUES (?, 0, 0, ?, ?, 0, 0, ?, ?, 'go_ast');
	`)
	if err != nil {
		return nil, err
	}
	defer stmtCal.Close()

	stmtParam, err := c.db.Prepare(`
		INSERT INTO parameters (
			callable_symbol_id, ordinal, name, pass_kind, type_expr, type_source, is_optional
		) VALUES (?, ?, ?, ?, ?, 'go_ast', ?);
	`)
	if err != nil {
		return nil, err
	}
	defer stmtParam.Close()

	stmtState, err := c.db.Prepare(`
		INSERT OR REPLACE INTO state_members (
			symbol_id, declared_type_expr, runtime_type_name, is_constant, is_mutable, literal_value_repr, access_mode
		) VALUES (?, ?, ?, ?, ?, ?, ?);
	`)
	if err != nil {
		return nil, err
	}
	defer stmtState.Close()

	stmtAlias, err := c.db.Prepare(`
		INSERT OR REPLACE INTO symbol_aliases (
			source_container_id, exposed_name, target_module_name, target_symbol_name, alias_kind, is_in_dunder_all
		) VALUES (?, ?, ?, ?, ?, ?);
	`)
	if err != nil {
		return nil, err
	}
	defer stmtAlias.Close()

	fset := token.NewFileSet()
	pkgContainers := make(map[string]int64)

	for filePath, content := range files {
		res.FilesProcessed++

		hash := sha256.Sum256([]byte(content))
		shaStr := hex.EncodeToString(hash[:])

		fileNode, parseErr := parser.ParseFile(fset, filePath, content, parser.ParseComments)
		if parseErr != nil {
			return nil, fmt.Errorf("failed to parse %s: %w", filePath, parseErr)
		}

		pkgName := fileNode.Name.Name
		pkgQName := filepath.ToSlash(filepath.Dir(filePath))
		if pkgQName == "." {
			pkgQName = pkgName
		}

		// Ensure Package Container
		pkgCID, exists := pkgContainers[pkgQName]
		if !exists {
			err := stmtCont.QueryRow(distID, sql.NullInt64{}, "package", pkgQName, pkgName, "public", filePath, shaStr, 1, 1, 0, 0, "Go package "+pkgName).Scan(&pkgCID)
			if err != nil {
				return nil, err
			}
			pkgContainers[pkgQName] = pkgCID
			res.ContainersHarvested++
			stmtContFacet.Exec(pkgCID, pkgName, "package", nil, nil, 1)
		}

		// Imports
		for _, imp := range fileNode.Imports {
			impPath := strings.Trim(imp.Path.Value, `"`)
			aliasName := filepath.Base(impPath)
			if imp.Name != nil {
				aliasName = imp.Name.Name
			}
			stmtAlias.Exec(pkgCID, aliasName, impPath, "*", "package_import", 1)
			res.AliasesHarvested++
		}

		// Top-level declarations
		for _, decl := range fileNode.Decls {
			switch d := decl.(type) {
			case *ast.GenDecl:
				for _, spec := range d.Specs {
					switch s := spec.(type) {
					case *ast.TypeSpec:
						typeName := s.Name.Name
						typeQName := pkgQName + "." + typeName
						isExp := ast.IsExported(typeName)
						vis := "private"
						if isExp {
							vis = "public"
						}

						startPos := fset.Position(s.Pos())
						endPos := fset.Position(s.End())

						kind := "type"
						switch s.Type.(type) {
						case *ast.StructType:
							kind = "struct"
						case *ast.InterfaceType:
							kind = "interface"
						}

						var typeCID int64
						err := stmtCont.QueryRow(distID, pkgCID, kind, typeQName, typeName, vis, filePath, shaStr, startPos.Line, startPos.Column, endPos.Line, endPos.Column, kind+" "+typeName).Scan(&typeCID)
						if err != nil {
							return nil, err
						}
						res.ContainersHarvested++
						stmtContFacet.Exec(typeCID, pkgName, kind, nil, nil, boolToInt(isExp))

						var symID int64
						err = stmtSym.QueryRow(pkgCID, typeCID, typeName, typeQName, "type", vis, startPos.Line, startPos.Column, endPos.Line, endPos.Column, kind+" "+typeName).Scan(&symID)
						if err != nil {
							return nil, err
						}
						res.SymbolsHarvested++
						stmtSymFacet.Exec(symID, "type", "none", nil, boolToInt(isExp), 0, `["type"]`)

						// Struct Fields
						if st, ok := s.Type.(*ast.StructType); ok && st.Fields != nil {
							for _, f := range st.Fields.List {
								fStart := fset.Position(f.Pos())
								fEnd := fset.Position(f.End())
								fTypeStr := exprString(f.Type)

								if len(f.Names) == 0 {
									// Embedded field
									embeddedName := exprString(f.Type)
									var fSymID int64
									stmtSym.QueryRow(typeCID, typeCID, embeddedName, typeQName+"."+embeddedName, "struct_field", "public", fStart.Line, fStart.Column, fEnd.Line, fEnd.Column, "Embedded "+embeddedName).Scan(&fSymID)
									res.SymbolsHarvested++
									stmtSymFacet.Exec(fSymID, "field", "none", nil, 1, 0, `["embedded"]`)
									stmtState.Exec(fSymID, fTypeStr, "embedded", 0, 1, nil, "read_write")
									res.StateMembersHarvested++
								} else {
									for _, fn := range f.Names {
										fName := fn.Name
										fExp := ast.IsExported(fName)
										fVis := "private"
										if fExp {
											fVis = "public"
										}

										var fSymID int64
										err = stmtSym.QueryRow(typeCID, typeCID, fName, typeQName+"."+fName, "struct_field", fVis, fStart.Line, fStart.Column, fEnd.Line, fEnd.Column, "Field "+fName).Scan(&fSymID)
										if err != nil {
											continue
										}
										res.SymbolsHarvested++
										stmtSymFacet.Exec(fSymID, "field", "none", nil, boolToInt(fExp), 0, `["field"]`)
										stmtState.Exec(fSymID, fTypeStr, "field", 0, 1, nil, fVis+"_read_write")
										res.StateMembersHarvested++
									}
								}
							}
						}

						// Interface Methods
						if it, ok := s.Type.(*ast.InterfaceType); ok && it.Methods != nil {
							for _, m := range it.Methods.List {
								mStart := fset.Position(m.Pos())
								mEnd := fset.Position(m.End())
								for _, mn := range m.Names {
									mName := mn.Name
									mExp := ast.IsExported(mName)
									mVis := "private"
									if mExp {
										mVis = "public"
									}

									var mSymID int64
									err = stmtSym.QueryRow(typeCID, typeCID, mName, typeQName+"."+mName, "interface_method", mVis, mStart.Line, mStart.Column, mEnd.Line, mEnd.Column, "Interface method "+mName).Scan(&mSymID)
									if err != nil {
										continue
									}
									res.SymbolsHarvested++
									stmtSymFacet.Exec(mSymID, "method", "none", nil, boolToInt(mExp), 0, `["interface_method"]`)

									if ft, ok := m.Type.(*ast.FuncType); ok {
										sigStr := funcTypeString(mName, ft)
										retStr := resultsString(ft.Results)
										stmtCal.Exec(mSymID, 0, 1, retStr, sigStr)
										res.CallablesHarvested++
										addParams(stmtParam, mSymID, ft.Params, fset, &res.ParametersHarvested)
									}
								}
							}
						}

					case *ast.ValueSpec:
						vKind := "variable"
						if d.Tok == token.CONST {
							vKind = "constant"
						}
						vStart := fset.Position(s.Pos())
						vEnd := fset.Position(s.End())
						vTypeStr := ""
						if s.Type != nil {
							vTypeStr = exprString(s.Type)
						}

						for idx, vn := range s.Names {
							vName := vn.Name
							vExp := ast.IsExported(vName)
							vVis := "private"
							if vExp {
								vVis = "public"
							}
							vQName := pkgQName + "." + vName

							valRepr := ""
							if idx < len(s.Values) {
								valRepr = exprString(s.Values[idx])
							}

							var symID int64
							err := stmtSym.QueryRow(pkgCID, sql.NullInt64{}, vName, vQName, vKind, vVis, vStart.Line, vStart.Column, vEnd.Line, vEnd.Column, vKind+" "+vName).Scan(&symID)
							if err != nil {
								continue
							}
							res.SymbolsHarvested++
							stmtSymFacet.Exec(symID, vKind, "none", nil, boolToInt(vExp), 0, fmt.Sprintf(`["%s"]`, vKind))
							stmtState.Exec(symID, vTypeStr, vKind, boolToInt(d.Tok == token.CONST), boolToInt(d.Tok == token.VAR), valRepr, "read_only")
							res.StateMembersHarvested++
						}
					}
				}

			case *ast.FuncDecl:
				fnName := d.Name.Name
				fnStart := fset.Position(d.Pos())
				fnEnd := fset.Position(d.End())
				isExp := ast.IsExported(fnName)
				vis := "private"
				if isExp {
					vis = "public"
				}

				sigStr := funcDeclString(d)
				retStr := resultsString(d.Type.Results)

				if d.Recv == nil {
					// Free function in package
					fnQName := pkgQName + "." + fnName
					var symID int64
					err := stmtSym.QueryRow(pkgCID, sql.NullInt64{}, fnName, fnQName, "function", vis, fnStart.Line, fnStart.Column, fnEnd.Line, fnEnd.Column, "Function "+fnName).Scan(&symID)
					if err != nil {
						continue
					}
					res.SymbolsHarvested++
					stmtSymFacet.Exec(symID, "func", "none", nil, boolToInt(isExp), isVariadic(d.Type), `["func"]`)
					stmtCal.Exec(symID, 1, 0, retStr, sigStr)
					res.CallablesHarvested++
					addParams(stmtParam, symID, d.Type.Params, fset, &res.ParametersHarvested)
				} else {
					// Method on receiver
					recvType := receiverTypeName(d.Recv)
					recvKind := "value"
					if strings.HasPrefix(recvType, "*") {
						recvKind = "pointer"
					}
					cleanRecvType := strings.TrimPrefix(recvType, "*")
					targetCID := pkgCID

					// Look up container for receiver struct if it exists
					var customCID int64
					err := c.db.QueryRow("SELECT container_id FROM containers WHERE dist_id=? AND short_name=?;", distID, cleanRecvType).Scan(&customCID)
					if err == nil && customCID > 0 {
						targetCID = customCID
					}

					methodQName := pkgQName + "." + cleanRecvType + "." + fnName
					var symID int64
					err = stmtSym.QueryRow(targetCID, targetCID, fnName, methodQName, "method", vis, fnStart.Line, fnStart.Column, fnEnd.Line, fnEnd.Column, "Method "+fnName).Scan(&symID)
					if err != nil {
						continue
					}
					res.SymbolsHarvested++
					stmtSymFacet.Exec(symID, "method", recvKind, recvType, boolToInt(isExp), isVariadic(d.Type), `["method"]`)
					stmtCal.Exec(symID, 0, 1, retStr, sigStr)
					res.CallablesHarvested++
					addParams(stmtParam, symID, d.Type.Params, fset, &res.ParametersHarvested)
				}
			}
		}
	}

	return res, nil
}

func boolToInt(b bool) int {
	if b {
		return 1
	}
	return 0
}

func exprString(e ast.Expr) string {
	if e == nil {
		return ""
	}
	var buf bytes.Buffer
	format.Node(&buf, token.NewFileSet(), e)
	return buf.String()
}

func funcDeclString(d *ast.FuncDecl) string {
	var buf bytes.Buffer
	format.Node(&buf, token.NewFileSet(), d)
	lines := strings.Split(buf.String(), "\n")
	if len(lines) > 0 {
		return strings.Split(lines[0], "{")[0]
	}
	return ""
}

func funcTypeString(name string, ft *ast.FuncType) string {
	var buf bytes.Buffer
	format.Node(&buf, token.NewFileSet(), ft)
	return name + strings.TrimPrefix(buf.String(), "func")
}

func resultsString(fields *ast.FieldList) string {
	if fields == nil || len(fields.List) == 0 {
		return "void"
	}
	var types []string
	for _, f := range fields.List {
		t := exprString(f.Type)
		if len(f.Names) > 1 {
			for range f.Names {
				types = append(types, t)
			}
		} else {
			types = append(types, t)
		}
	}
	if len(types) == 1 {
		return types[0]
	}
	return "(" + strings.Join(types, ", ") + ")"
}

func receiverTypeName(recv *ast.FieldList) string {
	if recv == nil || len(recv.List) == 0 {
		return ""
	}
	return exprString(recv.List[0].Type)
}

func isVariadic(ft *ast.FuncType) int {
	if ft.Params == nil || len(ft.Params.List) == 0 {
		return 0
	}
	last := ft.Params.List[len(ft.Params.List)-1]
	if _, ok := last.Type.(*ast.Ellipsis); ok {
		return 1
	}
	return 0
}

func addParams(stmtParam *sql.Stmt, symID int64, params *ast.FieldList, fset *token.FileSet, counter *int) {
	if params == nil {
		return
	}
	ord := 0
	for _, p := range params.List {
		pType := exprString(p.Type)
		pass := "val"
		if strings.HasPrefix(pType, "*") {
			pass = "pointer"
		} else if strings.HasPrefix(pType, "[]") {
			pass = "slice"
		} else if strings.HasPrefix(pType, "...") {
			pass = "variadic"
		}

		if len(p.Names) == 0 {
			stmtParam.Exec(symID, ord, fmt.Sprintf("arg%d", ord), pass, pType, 0)
			ord++
			*counter++
		} else {
			for _, pn := range p.Names {
				stmtParam.Exec(symID, ord, pn.Name, pass, pType, 0)
				ord++
				*counter++
			}
		}
	}
}
