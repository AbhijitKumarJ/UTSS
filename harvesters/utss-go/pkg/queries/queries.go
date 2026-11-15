package queries

import (
	"database/sql"
	"fmt"
	"strings"
)

func PrintSpectrumSummary(db *sql.DB) error {
	fmt.Println("\n=== Spectrum Summary by Stratum ===")
	query := `
		SELECT
			d.stratum,
			d.dist_name,
			d.dist_version,
			COUNT(DISTINCT c.container_id) AS total_containers,
			COUNT(DISTINCT s.symbol_id) AS total_symbols,
			COUNT(DISTINCT cal.symbol_id) AS total_callables,
			COUNT(DISTINCT p.param_id) AS total_parameters,
			COUNT(DISTINCT a.alias_id) AS total_aliases
		FROM distributions d
		LEFT JOIN containers c ON c.dist_id = d.dist_id
		LEFT JOIN symbols s ON s.container_id = c.container_id
		LEFT JOIN callables cal ON cal.symbol_id = s.symbol_id
		LEFT JOIN parameters p ON p.callable_symbol_id = cal.symbol_id
		LEFT JOIN symbol_aliases a ON a.source_container_id = c.container_id
		GROUP BY d.dist_id
		ORDER BY d.stratum, d.dist_name;
	`
	rows, err := db.Query(query)
	if err != nil {
		return err
	}
	defer rows.Close()

	fmt.Printf("%-9s %-20s %-14s %-13s %-11s %-12s %-13s %-10s\n",
		"Stratum", "Distribution", "Version", "Containers", "Symbols", "Callables", "Parameters", "Aliases")
	fmt.Println(strings.Repeat("-", 104))

	for rows.Next() {
		var stratum int
		var distName, distVer string
		var containers, symbols, callables, parameters, aliases int
		if err := rows.Scan(&stratum, &distName, &distVer, &containers, &symbols, &callables, &parameters, &aliases); err != nil {
			return err
		}
		fmt.Printf("%-9d %-20s %-14s %-13d %-11d %-12d %-13d %-10d\n",
			stratum, distName, distVer, containers, symbols, callables, parameters, aliases)
	}
	return nil
}

func PrintAmbientSummary(db *sql.DB) error {
	fmt.Println("\n=== Stratum 0 Ambient Summary ===")
	query := `
		SELECT
			s.symbol_kind,
			COUNT(*) AS item_count,
			GROUP_CONCAT(s.name, ', ') AS sample_items
		FROM symbols s
		JOIN containers c ON s.container_id = c.container_id
		JOIN distributions d ON c.dist_id = d.dist_id
		WHERE d.stratum = 0
		GROUP BY s.symbol_kind
		ORDER BY item_count DESC;
	`
	rows, err := db.Query(query)
	if err != nil {
		return err
	}
	defer rows.Close()

	fmt.Printf("%-18s %-12s %s\n", "Symbol Kind", "Count", "Sample Items")
	fmt.Println(strings.Repeat("-", 80))

	for rows.Next() {
		var kind string
		var count int
		var samples string
		if err := rows.Scan(&kind, &count, &samples); err != nil {
			return err
		}
		if len(samples) > 50 {
			samples = samples[:47] + "..."
		}
		fmt.Printf("%-18s %-12d %s\n", kind, count, samples)
	}
	return nil
}

func PrintStdlibSummary(db *sql.DB) error {
	fmt.Println("\n=== Stratum 1 Standard Library Breakdown ===")
	query := `
		SELECT
			c.qualified_name AS module_name,
			c.container_kind,
			COUNT(s.symbol_id) AS symbol_count,
			COUNT(cal.symbol_id) AS callable_count
		FROM containers c
		JOIN distributions d ON c.dist_id = d.dist_id
		LEFT JOIN symbols s ON s.container_id = c.container_id
		LEFT JOIN callables cal ON cal.symbol_id = s.symbol_id
		WHERE d.stratum = 1
		GROUP BY c.container_id
		ORDER BY symbol_count DESC, c.qualified_name;
	`
	rows, err := db.Query(query)
	if err != nil {
		return err
	}
	defer rows.Close()

	fmt.Printf("%-24s %-16s %-14s %-12s\n", "Package", "Container Kind", "Symbols", "Callables")
	fmt.Println(strings.Repeat("-", 70))

	for rows.Next() {
		var pkg, kind string
		var syms, calls int
		if err := rows.Scan(&pkg, &kind, &syms, &calls); err != nil {
			return err
		}
		fmt.Printf("%-24s %-16s %-14d %-12d\n", pkg, kind, syms, calls)
	}
	return nil
}

func PrintWorkspaceSymbols(db *sql.DB) error {
	fmt.Println("\n=== Stratum 3 Workspace Symbols & AST Coordinates ===")
	query := `
		SELECT
			c.qualified_name AS container,
			s.name AS symbol_name,
			s.symbol_kind,
			f.member_kind,
			f.receiver_kind,
			COALESCE(f.receiver_type, ''),
			COALESCE(s.start_line, 0),
			COALESCE(s.start_col, 0),
			COALESCE(s.end_line, 0),
			COALESCE(s.end_col, 0),
			COALESCE(cal.raw_signature, ''),
			COALESCE(cal.return_type_expr, '')
		FROM symbols s
		JOIN containers c ON s.container_id = c.container_id
		JOIN distributions d ON c.dist_id = d.dist_id
		LEFT JOIN go_symbol_facets f ON f.symbol_id = s.symbol_id
		LEFT JOIN callables cal ON cal.symbol_id = s.symbol_id
		WHERE d.stratum = 3
		ORDER BY c.qualified_name, s.start_line, s.name;
	`
	rows, err := db.Query(query)
	if err != nil {
		return err
	}
	defer rows.Close()

	fmt.Printf("%-26s %-20s %-12s %-10s %-12s %-18s %s\n",
		"Container", "Symbol", "Kind", "Receiver", "Span (L:C)", "Return Type", "Signature")
	fmt.Println(strings.Repeat("-", 120))

	for rows.Next() {
		var container, sym, kind, mKind, rKind, rType, sig, ret string
		var sLine, sCol, eLine, eCol int
		if err := rows.Scan(&container, &sym, &kind, &mKind, &rKind, &rType, &sLine, &sCol, &eLine, &eCol, &sig, &ret); err != nil {
			return err
		}
		span := fmt.Sprintf("L%d:C%d-L%d:C%d", sLine, sCol, eLine, eCol)
		recStr := rKind
		if rType != "" {
			recStr = rType
		}
		if len(sig) > 40 {
			sig = sig[:37] + "..."
		}
		fmt.Printf("%-26s %-20s %-12s %-10s %-12s %-18s %s\n",
			container, sym, kind, recStr, span, ret, sig)
	}
	return nil
}

func PrintGoFacets(db *sql.DB) error {
	fmt.Println("\n=== Go Container & Symbol Fidelity Facets ===")
	query := `
		SELECT
			c.qualified_name AS container,
			cf.package_name,
			cf.item_kind,
			s.name AS symbol,
			sf.member_kind,
			sf.receiver_kind,
			COALESCE(sf.receiver_type, 'none'),
			sf.is_exported,
			sf.is_variadic
		FROM symbols s
		JOIN containers c ON s.container_id = c.container_id
		JOIN go_container_facets cf ON cf.container_id = c.container_id
		JOIN go_symbol_facets sf ON sf.symbol_id = s.symbol_id
		ORDER BY c.qualified_name, s.name
		LIMIT 30;
	`
	rows, err := db.Query(query)
	if err != nil {
		return err
	}
	defer rows.Close()

	fmt.Printf("%-26s %-14s %-12s %-20s %-12s %-12s %-10s %-9s\n",
		"Container", "Package", "Kind", "Symbol", "Member Kind", "Receiver", "Exported", "Variadic")
	fmt.Println(strings.Repeat("-", 115))

	for rows.Next() {
		var container, pkg, kind, sym, mKind, rKind, rType string
		var isExp, isVar int
		if err := rows.Scan(&container, &pkg, &kind, &sym, &mKind, &rKind, &rType, &isExp, &isVar); err != nil {
			return err
		}
		expStr := "no"
		if isExp == 1 {
			expStr = "yes"
		}
		varStr := "no"
		if isVar == 1 {
			varStr = "yes"
		}
		fmt.Printf("%-26s %-14s %-12s %-20s %-12s %-12s %-10s %-9s\n",
			container, pkg, kind, sym, mKind, rType, expStr, varStr)
	}
	return nil
}
