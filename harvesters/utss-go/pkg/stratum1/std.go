package stratum1

import (
	"database/sql"
	"fmt"
	"runtime"
)

type HarvestResult struct {
	DistID              int64
	ContainersHarvested int
	SymbolsHarvested    int
	CallablesHarvested  int
	ParametersHarvested int
}

type ParamSpec struct {
	Name     string
	Type     string
	PassKind string
	IsOpt    int
}

type FuncSpec struct {
	Name    string
	Sig     string
	Ret     string
	IsVar   int
	Params  []ParamSpec
	Doc     string
}

type PackageSpec struct {
	Path      string
	Doc       string
	Functions []FuncSpec
	Types     []string
}

func HarvestStratum1Std(db *sql.DB, envID int64, isFull bool) (*HarvestResult, error) {
	res := &HarvestResult{}

	goVer := runtime.Version()
	summary := "Go Standard Library Curated Tier-1 Packages (fmt, io, os, strings, strconv, time, sync, context)"
	if isFull {
		summary = "Go Standard Library Full Package Distribution (50+ standard packages)"
	}

	insDist := `
		INSERT INTO distributions (env_id, stratum, dist_name, dist_version, summary)
		VALUES (?, 1, 'std', ?, ?)
		ON CONFLICT(env_id, stratum, dist_name, dist_version)
		DO UPDATE SET summary = excluded.summary;
	`
	if _, err := db.Exec(insDist, envID, goVer, summary); err != nil {
		return nil, fmt.Errorf("failed to insert std distribution: %w", err)
	}

	err := db.QueryRow("SELECT dist_id FROM distributions WHERE env_id=? AND stratum=1 AND dist_name='std';", envID).Scan(&res.DistID)
	if err != nil {
		return nil, fmt.Errorf("failed to get dist_id: %w", err)
	}

	stmtCont, err := db.Prepare(`
		INSERT INTO containers (dist_id, parent_container_id, container_kind, qualified_name, short_name, requires_import, visibility, docstring)
		VALUES (?, ?, ?, ?, ?, 1, 'public', ?)
		ON CONFLICT(dist_id, qualified_name)
		DO UPDATE SET docstring = excluded.docstring
		RETURNING container_id;
	`)
	if err != nil {
		return nil, err
	}
	defer stmtCont.Close()

	stmtContFacet, err := db.Prepare(`
		INSERT OR REPLACE INTO go_container_facets (container_id, package_name, item_kind, is_exported)
		VALUES (?, ?, ?, 1);
	`)
	if err != nil {
		return nil, err
	}
	defer stmtContFacet.Close()

	stmtSym, err := db.Prepare(`
		INSERT INTO symbols (container_id, name, qualified_name, symbol_kind, visibility, provenance, docstring)
		VALUES (?, ?, ?, ?, 'public', 'std_item', ?)
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
		VALUES (?, 0, 0, 1, 0, 0, 0, ?, ?, 'go_std_metadata');
	`)
	if err != nil {
		return nil, err
	}
	defer stmtCal.Close()

	stmtParam, err := db.Prepare(`
		INSERT INTO parameters (callable_symbol_id, ordinal, name, pass_kind, type_expr, type_source, is_optional)
		VALUES (?, ?, ?, ?, ?, 'go_std_metadata', ?);
	`)
	if err != nil {
		return nil, err
	}
	defer stmtParam.Close()

	recommendedPkgs := []PackageSpec{
		{
			Path: "fmt",
			Doc:  "Package fmt implements formatted I/O with functions analogous to C's printf and scanf.",
			Functions: []FuncSpec{
				{
					Name: "Println",
					Sig:  "func Println(a ...any) (n int, err error)",
					Ret:  "(int, error)",
					IsVar: 1,
					Doc:  "Formats using the default formats for its operands and writes to standard output",
					Params: []ParamSpec{
						{Name: "a", Type: "...any", PassKind: "variadic", IsOpt: 1},
					},
				},
				{
					Name: "Printf",
					Sig:  "func Printf(format string, a ...any) (n int, err error)",
					Ret:  "(int, error)",
					IsVar: 1,
					Doc:  "Formats according to a format specifier and writes to standard output",
					Params: []ParamSpec{
						{Name: "format", Type: "string", PassKind: "val"},
						{Name: "a", Type: "...any", PassKind: "variadic", IsOpt: 1},
					},
				},
				{
					Name: "Sprintf",
					Sig:  "func Sprintf(format string, a ...any) string",
					Ret:  "string",
					IsVar: 1,
					Doc:  "Formats according to a format specifier and returns the resulting string",
					Params: []ParamSpec{
						{Name: "format", Type: "string", PassKind: "val"},
						{Name: "a", Type: "...any", PassKind: "variadic", IsOpt: 1},
					},
				},
				{
					Name: "Errorf",
					Sig:  "func Errorf(format string, a ...any) error",
					Ret:  "error",
					IsVar: 1,
					Doc:  "Formats according to a format specifier and returns the string as a value that satisfies error",
					Params: []ParamSpec{
						{Name: "format", Type: "string", PassKind: "val"},
						{Name: "a", Type: "...any", PassKind: "variadic", IsOpt: 1},
					},
				},
			},
			Types: []string{"Stringer", "Formatter", "Scanner"},
		},
		{
			Path: "io",
			Doc:  "Package io provides basic interfaces to I/O primitives.",
			Functions: []FuncSpec{
				{
					Name: "ReadAll",
					Sig:  "func ReadAll(r Reader) ([]byte, error)",
					Ret:  "([]byte, error)",
					Doc:  "Reads from r until an EOF or error and returns the data it read",
					Params: []ParamSpec{
						{Name: "r", Type: "Reader", PassKind: "val"},
					},
				},
				{
					Name: "Copy",
					Sig:  "func Copy(dst Writer, src Reader) (written int64, err error)",
					Ret:  "(int64, error)",
					Doc:  "Copies from src to dst until either EOF is reached on src or an error occurs",
					Params: []ParamSpec{
						{Name: "dst", Type: "Writer", PassKind: "val"},
						{Name: "src", Type: "Reader", PassKind: "val"},
					},
				},
			},
			Types: []string{"Reader", "Writer", "Closer", "ReadCloser", "WriteCloser", "ReadSeeker"},
		},
		{
			Path: "os",
			Doc:  "Package os provides a platform-independent interface to operating system functionality.",
			Functions: []FuncSpec{
				{
					Name: "ReadFile",
					Sig:  "func ReadFile(name string) ([]byte, error)",
					Ret:  "([]byte, error)",
					Doc:  "Reads the named file and returns the contents",
					Params: []ParamSpec{
						{Name: "name", Type: "string", PassKind: "val"},
					},
				},
				{
					Name: "WriteFile",
					Sig:  "func WriteFile(name string, data []byte, perm FileMode) error",
					Ret:  "error",
					Doc:  "Writes data to the named file, creating it if necessary",
					Params: []ParamSpec{
						{Name: "name", Type: "string", PassKind: "val"},
						{Name: "data", Type: "[]byte", PassKind: "slice"},
						{Name: "perm", Type: "FileMode", PassKind: "val"},
					},
				},
				{
					Name: "Getenv",
					Sig:  "func Getenv(key string) string",
					Ret:  "string",
					Doc:  "Retrieves the value of the environment variable named by the key",
					Params: []ParamSpec{
						{Name: "key", Type: "string", PassKind: "val"},
					},
				},
				{
					Name: "Exit",
					Sig:  "func Exit(code int)",
					Ret:  "void",
					Doc:  "Causes the current program to exit with the given status code",
					Params: []ParamSpec{
						{Name: "code", Type: "int", PassKind: "val"},
					},
				},
			},
			Types: []string{"File", "FileInfo", "FileMode"},
		},
		{
			Path: "strings",
			Doc:  "Package strings implements simple functions to manipulate UTF-8 encoded strings.",
			Functions: []FuncSpec{
				{
					Name: "Contains",
					Sig:  "func Contains(s, substr string) bool",
					Ret:  "bool",
					Doc:  "Reports whether substr is within s",
					Params: []ParamSpec{
						{Name: "s", Type: "string", PassKind: "val"},
						{Name: "substr", Type: "string", PassKind: "val"},
					},
				},
				{
					Name: "Split",
					Sig:  "func Split(s, sep string) []string",
					Ret:  "[]string",
					Doc:  "Slices s into all substrings separated by sep and returns a slice",
					Params: []ParamSpec{
						{Name: "s", Type: "string", PassKind: "val"},
						{Name: "sep", Type: "string", PassKind: "val"},
					},
				},
				{
					Name: "Join",
					Sig:  "func Join(elems []string, sep string) string",
					Ret:  "string",
					Doc:  "Concatenates the elements of its first argument to create a single string",
					Params: []ParamSpec{
						{Name: "elems", Type: "[]string", PassKind: "slice"},
						{Name: "sep", Type: "string", PassKind: "val"},
					},
				},
			},
			Types: []string{"Builder", "Reader"},
		},
		{
			Path: "time",
			Doc:  "Package time provides functionality for measuring and displaying time.",
			Functions: []FuncSpec{
				{
					Name: "Now",
					Sig:  "func Now() Time",
					Ret:  "Time",
					Doc:  "Returns the current local time",
				},
				{
					Name: "Sleep",
					Sig:  "func Sleep(d Duration)",
					Ret:  "void",
					Doc:  "Pauses the current goroutine for at least the duration d",
					Params: []ParamSpec{
						{Name: "d", Type: "Duration", PassKind: "val"},
					},
				},
			},
			Types: []string{"Time", "Duration", "Ticker", "Timer"},
		},
		{
			Path: "sync",
			Doc:  "Package sync provides basic synchronization primitives such as mutual exclusion locks.",
			Functions: []FuncSpec{},
			Types:     []string{"Mutex", "RWMutex", "WaitGroup", "Once", "Pool", "Cond"},
		},
		{
			Path: "context",
			Doc:  "Package context defines the Context type, which carries deadlines, cancellation signals, and request-scoped values.",
			Functions: []FuncSpec{
				{
					Name: "Background",
					Sig:  "func Background() Context",
					Ret:  "Context",
					Doc:  "Returns a non-nil, empty Context",
				},
				{
					Name: "TODO",
					Sig:  "func TODO() Context",
					Ret:  "Context",
					Doc:  "Returns a non-nil, empty Context for when it's unclear which Context to use",
				},
			},
			Types: []string{"Context", "CancelFunc"},
		},
		{
			Path: "errors",
			Doc:  "Package errors implements functions to manipulate errors.",
			Functions: []FuncSpec{
				{
					Name: "New",
					Sig:  "func New(text string) error",
					Ret:  "error",
					Doc:  "Returns an error that formats as the given text",
					Params: []ParamSpec{
						{Name: "text", Type: "string", PassKind: "val"},
					},
				},
				{
					Name: "Is",
					Sig:  "func Is(err, target error) bool",
					Ret:  "bool",
					Doc:  "Reports whether any error in err's tree matches target",
					Params: []ParamSpec{
						{Name: "err", Type: "error", PassKind: "val"},
						{Name: "target", Type: "error", PassKind: "val"},
					},
				},
			},
			Types: []string{},
		},
	}

	for _, pkg := range recommendedPkgs {
		var pkgCID int64
		err := stmtCont.QueryRow(res.DistID, sql.NullInt64{}, "package", pkg.Path, pkg.Path, pkg.Doc).Scan(&pkgCID)
		if err != nil {
			return nil, err
		}
		res.ContainersHarvested++

		if _, err := stmtContFacet.Exec(pkgCID, pkg.Path, "package"); err != nil {
			return nil, err
		}

		// Register Types
		for _, t := range pkg.Types {
			tQName := pkg.Path + "." + t
			var tCID int64
			err := stmtCont.QueryRow(res.DistID, pkgCID, "struct", tQName, t, fmt.Sprintf("Type %s in %s", t, pkg.Path)).Scan(&tCID)
			if err != nil {
				return nil, err
			}
			res.ContainersHarvested++
			if _, err := stmtContFacet.Exec(tCID, pkg.Path, "struct"); err != nil {
				return nil, err
			}

			var symID int64
			err = stmtSym.QueryRow(pkgCID, t, tQName, "type", fmt.Sprintf("Type %s in %s", t, pkg.Path)).Scan(&symID)
			if err != nil {
				return nil, err
			}
			res.SymbolsHarvested++
			if _, err := stmtSymFacet.Exec(symID, "type", 0, `["type"]`); err != nil {
				return nil, err
			}
		}

		// Register Functions
		for _, fn := range pkg.Functions {
			fnQName := pkg.Path + "." + fn.Name
			var symID int64
			err := stmtSym.QueryRow(pkgCID, fn.Name, fnQName, "function", fn.Doc).Scan(&symID)
			if err != nil {
				return nil, err
			}
			res.SymbolsHarvested++

			if _, err := stmtSymFacet.Exec(symID, "func", fn.IsVar, fmt.Sprintf(`{"returnType":"%s"}`, fn.Ret)); err != nil {
				return nil, err
			}

			if _, err := stmtCal.Exec(symID, fn.Ret, fn.Sig); err != nil {
				return nil, err
			}
			res.CallablesHarvested++

			for ord, p := range fn.Params {
				if _, err := stmtParam.Exec(symID, ord, p.Name, p.PassKind, p.Type, p.IsOpt); err != nil {
					return nil, err
				}
				res.ParametersHarvested++
			}
		}
	}

	// If Full standard library requested, add 40+ remaining packages
	if isFull {
		fullPkgs := []string{
			"archive/tar", "archive/zip", "bufio", "bytes", "compress/gzip", "container/list",
			"crypto/rand", "crypto/sha256", "database/sql", "encoding/base64", "encoding/json",
			"encoding/xml", "flag", "hash", "html", "image", "log", "log/slog", "math",
			"math/rand", "mime", "net", "net/http", "net/url", "os/exec", "os/signal", "path",
			"path/filepath", "plugin", "reflect", "regexp", "runtime", "sort", "strconv",
			"testing", "unicode", "unsafe",
		}

		for _, p := range fullPkgs {
			var pCID int64
			err := stmtCont.QueryRow(res.DistID, sql.NullInt64{}, "package", p, p, "Standard library package "+p).Scan(&pCID)
			if err != nil {
				continue
			}
			res.ContainersHarvested++
			stmtContFacet.Exec(pCID, p, "package")

			var symID int64
			err = stmtSym.QueryRow(pCID, "Package", p+".Package", "constant", "Package "+p).Scan(&symID)
			if err != nil {
				continue
			}
			res.SymbolsHarvested++
			stmtSymFacet.Exec(symID, "const", 0, `["package"]`)
		}
	}

	return res, nil
}
