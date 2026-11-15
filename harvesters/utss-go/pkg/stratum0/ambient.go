package stratum0

import (
	"database/sql"
	"fmt"
	"os/exec"
	"runtime"
	"strconv"
	"strings"
)

type HarvestResult struct {
	EnvID          int64
	DistID         int64
	ContainerID    int64
	KeywordCount   int
	PrimitiveCount int
	ConstantCount  int
	BuiltinCount   int
}

func HarvestStratum0Ambient(db *sql.DB) (*HarvestResult, error) {
	res := &HarvestResult{}

	goVer := runtime.Version()
	parts := strings.Split(strings.TrimPrefix(goVer, "go"), ".")
	major, minor, patch := 1, 0, 0
	if len(parts) >= 1 {
		major, _ = strconv.Atoi(parts[0])
	}
	if len(parts) >= 2 {
		minor, _ = strconv.Atoi(parts[1])
	}
	if len(parts) >= 3 {
		patch, _ = strconv.Atoi(parts[2])
	}

	execPath, err := exec.LookPath("go")
	if err != nil {
		execPath = "/home/abhijit/.local/go/bin/go"
	}

	triplet := fmt.Sprintf("%s-%s", runtime.GOOS, runtime.GOARCH)

	// 1. Insert Environment
	insEnv := `
		INSERT INTO environments (
			language, runtime_name, language_version, version_major, version_minor, version_micro, platform_triplet, sys_platform, executable_path
		) VALUES ('go', 'gc', ?, ?, ?, ?, ?, ?, ?)
		ON CONFLICT(language, runtime_name, language_version, platform_triplet, executable_path)
		DO UPDATE SET captured_at = CURRENT_TIMESTAMP;
	`
	if _, err := db.Exec(insEnv, goVer, major, minor, patch, triplet, runtime.GOOS, execPath); err != nil {
		return nil, fmt.Errorf("failed to insert environment: %w", err)
	}

	err = db.QueryRow("SELECT env_id FROM environments WHERE language='go' AND runtime_name='gc' AND language_version=?;", goVer).Scan(&res.EnvID)
	if err != nil {
		return nil, fmt.Errorf("failed to get env_id: %w", err)
	}

	// 2. Insert Distribution
	insDist := `
		INSERT INTO distributions (env_id, stratum, dist_name, dist_version, summary)
		VALUES (?, 0, '<ambient>', ?, 'Go specification predeclared keywords, fundamental types, constants, and builtins')
		ON CONFLICT(env_id, stratum, dist_name, dist_version)
		DO UPDATE SET summary = excluded.summary;
	`
	if _, err := db.Exec(insDist, res.EnvID, goVer); err != nil {
		return nil, fmt.Errorf("failed to insert distribution: %w", err)
	}

	err = db.QueryRow("SELECT dist_id FROM distributions WHERE env_id=? AND stratum=0 AND dist_name='<ambient>';", res.EnvID).Scan(&res.DistID)
	if err != nil {
		return nil, fmt.Errorf("failed to get dist_id: %w", err)
	}

	// 3. Insert Container
	insCont := `
		INSERT INTO containers (dist_id, container_kind, qualified_name, short_name, requires_import, visibility, docstring)
		VALUES (?, 'ambient_scope', '<ambient>', '<ambient>', 0, 'public', 'Go language specification predeclared ambient scope')
		ON CONFLICT(dist_id, qualified_name)
		DO UPDATE SET docstring = excluded.docstring;
	`
	if _, err := db.Exec(insCont, res.DistID); err != nil {
		return nil, fmt.Errorf("failed to insert container: %w", err)
	}

	err = db.QueryRow("SELECT container_id FROM containers WHERE dist_id=? AND qualified_name='<ambient>';", res.DistID).Scan(&res.ContainerID)
	if err != nil {
		return nil, fmt.Errorf("failed to get container_id: %w", err)
	}

	// Container Facet
	insContFacet := `
		INSERT OR REPLACE INTO go_container_facets (container_id, package_name, item_kind, is_exported)
		VALUES (?, '<ambient>', 'ambient_scope', 1);
	`
	if _, err := db.Exec(insContFacet, res.ContainerID); err != nil {
		return nil, fmt.Errorf("failed to insert container facet: %w", err)
	}

	// Prepare reusable queries
	stmtSym, err := db.Prepare(`
		INSERT INTO symbols (container_id, name, qualified_name, symbol_kind, visibility, provenance, docstring)
		VALUES (?, ?, ?, ?, 'public', ?, ?)
		ON CONFLICT(container_id, name)
		DO UPDATE SET symbol_kind = excluded.symbol_kind
		RETURNING symbol_id;
	`)
	if err != nil {
		return nil, err
	}
	defer stmtSym.Close()

	stmtSymFacet, err := db.Prepare(`
		INSERT OR REPLACE INTO go_symbol_facets (symbol_id, member_kind, receiver_kind, is_exported, is_variadic, signature_json)
		VALUES (?, ?, 'none', 1, ?, ?);
	`)
	if err != nil {
		return nil, err
	}
	defer stmtSymFacet.Close()

	stmtCal, err := db.Prepare(`
		INSERT OR REPLACE INTO callables (symbol_id, is_async, is_generator, is_static, is_class_bound, has_overloads, overload_count, return_type_expr, raw_signature, signature_source)
		VALUES (?, 0, 0, 1, 0, 0, 0, ?, ?, 'ambient');
	`)
	if err != nil {
		return nil, err
	}
	defer stmtCal.Close()

	stmtParam, err := db.Prepare(`
		INSERT INTO parameters (callable_symbol_id, ordinal, name, pass_kind, type_expr, type_source, is_optional)
		VALUES (?, ?, ?, ?, ?, 'ambient', ?);
	`)
	if err != nil {
		return nil, err
	}
	defer stmtParam.Close()

	stmtState, err := db.Prepare(`
		INSERT OR REPLACE INTO state_members (symbol_id, declared_type_expr, runtime_type_name, is_constant, is_mutable, literal_value_repr, access_mode)
		VALUES (?, ?, ?, ?, ?, ?, 'read_only');
	`)
	if err != nil {
		return nil, err
	}
	defer stmtState.Close()

	// A. 25 Go Keywords
	keywords := []string{
		"break", "case", "chan", "const", "continue", "default", "defer", "else",
		"fallthrough", "for", "func", "go", "goto", "if", "import", "interface",
		"map", "package", "range", "return", "select", "struct", "switch", "type", "var",
	}

	for _, kw := range keywords {
		var symID int64
		err := stmtSym.QueryRow(res.ContainerID, kw, "<ambient>::"+kw, "keyword", "ambient_keyword", fmt.Sprintf("Go keyword '%s'", kw)).Scan(&symID)
		if err != nil {
			return nil, err
		}
		if _, err := stmtSymFacet.Exec(symID, "keyword", 0, `["keyword"]`); err != nil {
			return nil, err
		}
		res.KeywordCount++
	}

	// B. 22 Predeclared Types
	primitives := []struct {
		name string
		doc  string
	}{
		{"bool", "Boolean type capable of holding true or false"},
		{"byte", "Alias for uint8"},
		{"complex64", "Complex numbers with float32 real and imaginary parts"},
		{"complex128", "Complex numbers with float64 real and imaginary parts"},
		{"error", "Predeclared interface type for representing an error condition"},
		{"float32", "32-bit IEEE 754 floating-point numbers"},
		{"float64", "64-bit IEEE 754 floating-point numbers"},
		{"int", "Signed integer type of at least 32 bits (usually 64 on 64-bit platforms)"},
		{"int8", "Signed 8-bit integers (-128 to 127)"},
		{"int16", "Signed 16-bit integers"},
		{"int32", "Signed 32-bit integers"},
		{"int64", "Signed 64-bit integers"},
		{"rune", "Alias for int32 representing a Unicode code point"},
		{"string", "Immutable sequence of bytes representing text"},
		{"uint", "Unsigned integer type of at least 32 bits"},
		{"uint8", "Unsigned 8-bit integers (0 to 255)"},
		{"uint16", "Unsigned 16-bit integers"},
		{"uint32", "Unsigned 32-bit integers"},
		{"uint64", "Unsigned 64-bit integers"},
		{"uintptr", "Unsigned integer large enough to store an uninterpreted pointer"},
		{"any", "Alias for interface{} representing any type"},
		{"comparable", "Interface implemented by all strictly comparable types"},
	}

	for _, p := range primitives {
		var symID int64
		err := stmtSym.QueryRow(res.ContainerID, p.name, "<ambient>::"+p.name, "primitive_type", "ambient_primitive", p.doc).Scan(&symID)
		if err != nil {
			return nil, err
		}
		if _, err := stmtSymFacet.Exec(symID, "primitive", 0, `["primitive"]`); err != nil {
			return nil, err
		}
		res.PrimitiveCount++
	}

	// C. 4 Predeclared Constants & Identifiers
	constants := []struct {
		name string
		val  string
		doc  string
	}{
		{"true", "true", "Boolean true constant"},
		{"false", "false", "Boolean false constant"},
		{"iota", "0", "Successive untyped integer constant in const declarations"},
		{"nil", "nil", "Predeclared identifier representing zero value for pointer, channel, func, interface, map, or slice"},
	}

	for _, c := range constants {
		var symID int64
		err := stmtSym.QueryRow(res.ContainerID, c.name, "<ambient>::"+c.name, "constant", "ambient_builtin", c.doc).Scan(&symID)
		if err != nil {
			return nil, err
		}
		if _, err := stmtSymFacet.Exec(symID, "const", 0, `["predeclared_const"]`); err != nil {
			return nil, err
		}
		if _, err := stmtState.Exec(symID, "untyped", "constant", 1, 0, c.val); err != nil {
			return nil, err
		}
		res.ConstantCount++
	}

	// D. 18 Predeclared Built-in Functions
	builtins := []struct {
		name    string
		sig     string
		ret     string
		isVar   int
		doc     string
		params  []struct{ name, typ, pass string; opt int }
	}{
		{"append", "func append(slice []Type, elems ...Type) []Type", "[]Type", 1, "Appends elements to the end of a slice", []struct{ name, typ, pass string; opt int }{{"slice", "[]Type", "slice", 0}, {"elems", "...Type", "variadic", 1}}},
		{"cap", "func cap(v Type) int", "int", 0, "Returns the capacity of v according to its type", []struct{ name, typ, pass string; opt int }{{"v", "Type", "val", 0}}},
		{"clear", "func clear[T ~[]Type | ~map[Type]Type1](t T)", "void", 0, "Clears all elements of a map or slice", []struct{ name, typ, pass string; opt int }{{"t", "T", "val", 0}}},
		{"close", "func close(c chan<- Type)", "void", 0, "Closes a channel", []struct{ name, typ, pass string; opt int }{{"c", "chan<- Type", "val", 0}}},
		{"complex", "func complex(r, i FloatType) ComplexType", "ComplexType", 0, "Constructs a complex value from real and imaginary parts", []struct{ name, typ, pass string; opt int }{{"r", "FloatType", "val", 0}, {"i", "FloatType", "val", 0}}},
		{"copy", "func copy(dst, src []Type) int", "int", 0, "Copies elements from a source slice to destination", []struct{ name, typ, pass string; opt int }{{"dst", "[]Type", "slice", 0}, {"src", "[]Type", "slice", 0}}},
		{"delete", "func delete(m map[Type]Type1, key Type)", "void", 0, "Deletes the element with the specified key from the map", []struct{ name, typ, pass string; opt int }{{"m", "map[Type]Type1", "val", 0}, {"key", "Type", "val", 0}}},
		{"imag", "func imag(c ComplexType) FloatType", "FloatType", 0, "Returns the imaginary part of the complex number c", []struct{ name, typ, pass string; opt int }{{"c", "ComplexType", "val", 0}}},
		{"len", "func len(v Type) int", "int", 0, "Returns the length of v according to its type", []struct{ name, typ, pass string; opt int }{{"v", "Type", "val", 0}}},
		{"make", "func make(t Type, size ...IntegerType) Type", "Type", 1, "Allocates and initializes an object of slice, map, or chan", []struct{ name, typ, pass string; opt int }{{"t", "Type", "val", 0}, {"size", "...IntegerType", "variadic", 1}}},
		{"max", "func max[T cmp.Ordered](x T, y ...T) T", "T", 1, "Returns the maximum value among arguments", []struct{ name, typ, pass string; opt int }{{"x", "T", "val", 0}, {"y", "...T", "variadic", 1}}},
		{"min", "func min[T cmp.Ordered](x T, y ...T) T", "T", 1, "Returns the minimum value among arguments", []struct{ name, typ, pass string; opt int }{{"x", "T", "val", 0}, {"y", "...T", "variadic", 1}}},
		{"new", "func new(Type) *Type", "*Type", 0, "Allocates zeroed memory for a new value of specified type", []struct{ name, typ, pass string; opt int }{{"Type", "Type", "val", 0}}},
		{"panic", "func panic(v any)", "void", 0, "Stops the normal execution of the current goroutine", []struct{ name, typ, pass string; opt int }{{"v", "any", "val", 0}}},
		{"print", "func print(args ...Type)", "void", 1, "Formats arguments in an implementation-specific way to standard error", []struct{ name, typ, pass string; opt int }{{"args", "...Type", "variadic", 1}}},
		{"println", "func println(args ...Type)", "void", 1, "Formats arguments like print, appending spaces and a newline", []struct{ name, typ, pass string; opt int }{{"args", "...Type", "variadic", 1}}},
		{"real", "func real(c ComplexType) FloatType", "FloatType", 0, "Returns the real part of the complex number c", []struct{ name, typ, pass string; opt int }{{"c", "ComplexType", "val", 0}}},
		{"recover", "func recover() any", "any", 0, "Manages behavior of a panicking goroutine", nil},
	}

	for _, b := range builtins {
		var symID int64
		err := stmtSym.QueryRow(res.ContainerID, b.name, "<ambient>::"+b.name, "function", "ambient_builtin", b.doc).Scan(&symID)
		if err != nil {
			return nil, err
		}
		if _, err := stmtSymFacet.Exec(symID, "builtin", b.isVar, fmt.Sprintf(`{"returnType":"%s"}`, b.ret)); err != nil {
			return nil, err
		}
		if _, err := stmtCal.Exec(symID, b.ret, b.sig); err != nil {
			return nil, err
		}
		for ord, p := range b.params {
			if _, err := stmtParam.Exec(symID, ord, p.name, p.pass, p.typ, p.opt); err != nil {
				return nil, err
			}
		}
		res.BuiltinCount++
	}

	return res, nil
}
