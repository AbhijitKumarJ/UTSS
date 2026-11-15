package tests

import (
	"database/sql"
	"testing"

	_ "modernc.org/sqlite"

	"utss-go/pkg/schema"
	"utss-go/pkg/stratum0"
	"utss-go/pkg/stratum1"
	"utss-go/pkg/stratum3"
)

func TestSchemaInitAndReset(t *testing.T) {
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("Failed to open in-memory sqlite: %v", err)
	}
	defer db.Close()

	if err := schema.InitSchema(db); err != nil {
		t.Fatalf("Failed to init schema: %v", err)
	}

	rows, err := db.Query("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
	if err != nil {
		t.Fatalf("Failed to query tables: %v", err)
	}
	defer rows.Close()

	tableMap := make(map[string]bool)
	for rows.Next() {
		var name string
		rows.Scan(&name)
		tableMap[name] = true
	}

	for _, expected := range schema.ExpectedTables {
		if !tableMap[expected] {
			t.Errorf("Missing expected table: %s", expected)
		}
	}

	// Test Reset
	if err := schema.ResetSchema(db); err != nil {
		t.Fatalf("Failed to reset schema: %v", err)
	}
}

func TestStratum0Ambient(t *testing.T) {
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("Failed to open sqlite: %v", err)
	}
	defer db.Close()

	if err := schema.InitSchema(db); err != nil {
		t.Fatalf("Failed to init schema: %v", err)
	}

	res, err := stratum0.HarvestStratum0Ambient(db)
	if err != nil {
		t.Fatalf("HarvestStratum0Ambient failed: %v", err)
	}

	if res.KeywordCount != 25 {
		t.Errorf("Expected 25 keywords, got %d", res.KeywordCount)
	}
	if res.PrimitiveCount != 22 {
		t.Errorf("Expected 22 primitives, got %d", res.PrimitiveCount)
	}
	if res.ConstantCount != 4 {
		t.Errorf("Expected 4 constants, got %d", res.ConstantCount)
	}
	if res.BuiltinCount != 18 {
		t.Errorf("Expected 18 builtins, got %d", res.BuiltinCount)
	}

	// Check specific symbol
	var symKind string
	err = db.QueryRow("SELECT symbol_kind FROM symbols WHERE name='func';").Scan(&symKind)
	if err != nil || symKind != "keyword" {
		t.Errorf("Symbol 'func' expected keyword, got %s (err: %v)", symKind, err)
	}

	err = db.QueryRow("SELECT symbol_kind FROM symbols WHERE name='append';").Scan(&symKind)
	if err != nil || symKind != "function" {
		t.Errorf("Symbol 'append' expected function, got %s (err: %v)", symKind, err)
	}
}

func TestStratum1Std(t *testing.T) {
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("Failed to open sqlite: %v", err)
	}
	defer db.Close()

	if err := schema.InitSchema(db); err != nil {
		t.Fatalf("Failed to init schema: %v", err)
	}

	res0, err := stratum0.HarvestStratum0Ambient(db)
	if err != nil {
		t.Fatalf("Stratum 0 harvest failed: %v", err)
	}

	res1, err := stratum1.HarvestStratum1Std(db, res0.EnvID, false)
	if err != nil {
		t.Fatalf("HarvestStratum1Std failed: %v", err)
	}

	if res1.ContainersHarvested < 10 {
		t.Errorf("Expected >= 10 stdlib containers, got %d", res1.ContainersHarvested)
	}
	if res1.SymbolsHarvested < 15 {
		t.Errorf("Expected >= 15 stdlib symbols, got %d", res1.SymbolsHarvested)
	}
	if res1.CallablesHarvested < 10 {
		t.Errorf("Expected >= 10 stdlib callables, got %d", res1.CallablesHarvested)
	}

	// Check fmt.Println
	var sig string
	err = db.QueryRow("SELECT raw_signature FROM callables cal JOIN symbols s ON cal.symbol_id=s.symbol_id WHERE s.name='Println';").Scan(&sig)
	if err != nil || sig == "" {
		t.Errorf("Failed to query fmt.Println callable: %v", err)
	}
}

func TestStratum3Workspace(t *testing.T) {
	db, err := sql.Open("sqlite", ":memory:")
	if err != nil {
		t.Fatalf("Failed to open sqlite: %v", err)
	}
	defer db.Close()

	if err := schema.InitSchema(db); err != nil {
		t.Fatalf("Failed to init schema: %v", err)
	}

	res0, err := stratum0.HarvestStratum0Ambient(db)
	if err != nil {
		t.Fatalf("Stratum 0 harvest failed: %v", err)
	}

	cataloger := stratum3.NewWorkspaceAstCataloger(db, res0.EnvID)
	res3, err := cataloger.HarvestEmbeddedDemo()
	if err != nil {
		t.Fatalf("HarvestEmbeddedDemo failed: %v", err)
	}

	if res3.FilesProcessed != 3 {
		t.Errorf("Expected 3 files processed, got %d", res3.FilesProcessed)
	}
	if res3.ContainersHarvested < 6 {
		t.Errorf("Expected >= 6 containers, got %d", res3.ContainersHarvested)
	}
	if res3.SymbolsHarvested < 20 {
		t.Errorf("Expected >= 20 symbols, got %d", res3.SymbolsHarvested)
	}
	if res3.CallablesHarvested < 8 {
		t.Errorf("Expected >= 8 callables, got %d", res3.CallablesHarvested)
	}

	// Check Order struct container & coordinates
	var kind string
	var startLine, endLine int
	err = db.QueryRow("SELECT container_kind, start_line, end_line FROM containers WHERE short_name='Order' AND container_kind='struct';").Scan(&kind, &startLine, &endLine)
	if err != nil {
		t.Fatalf("Order struct container not found: %v", err)
	}
	if startLine <= 0 || endLine < startLine {
		t.Errorf("Invalid coordinates for Order struct: %d-%d", startLine, endLine)
	}

	// Check pointer receiver method AddItem on *Order
	var recKind, recType string
	err = db.QueryRow(`
		SELECT sf.receiver_kind, sf.receiver_type
		FROM symbols s
		JOIN go_symbol_facets sf ON sf.symbol_id = s.symbol_id
		WHERE s.name = 'AddItem';
	`).Scan(&recKind, &recType)
	if err != nil {
		t.Fatalf("AddItem method not found: %v", err)
	}
	if recKind != "pointer" || recType != "*Order" {
		t.Errorf("Expected pointer receiver *Order, got kind=%s, type=%s", recKind, recType)
	}

	// Check interface method ProcessOrder in IOrderService
	var mKind string
	err = db.QueryRow(`
		SELECT s.symbol_kind
		FROM symbols s
		JOIN containers c ON s.container_id = c.container_id
		WHERE s.name = 'ProcessOrder' AND c.short_name = 'IOrderService';
	`).Scan(&mKind)
	if err != nil || mKind != "interface_method" {
		t.Errorf("Expected interface_method ProcessOrder in IOrderService, got %s (err: %v)", mKind, err)
	}
}
