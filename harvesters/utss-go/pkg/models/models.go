package models

import "database/sql"

type Environment struct {
	EnvID                 int64  `json:"env_id"`
	Language              string `json:"language"`
	RuntimeName           string `json:"runtime_name"`
	LanguageVersion       string `json:"language_version"`
	VersionMajor          int    `json:"version_major"`
	VersionMinor          int    `json:"version_minor"`
	VersionMicro          int    `json:"version_micro"`
	PlatformTriplet       string `json:"platform_triplet"`
	SysPlatform           string `json:"sys_platform"`
	ExecutablePath        string `json:"executable_path"`
}

type Distribution struct {
	DistID      int64          `json:"dist_id"`
	EnvID       int64          `json:"env_id"`
	Stratum     int            `json:"stratum"`
	DistName    string         `json:"dist_name"`
	DistVersion string         `json:"dist_version"`
	Summary     sql.NullString `json:"summary"`
}

type Container struct {
	ContainerID       int64          `json:"container_id"`
	DistID            int64          `json:"dist_id"`
	ParentContainerID sql.NullInt64  `json:"parent_container_id"`
	ContainerKind     string         `json:"container_kind"`
	QualifiedName     string         `json:"qualified_name"`
	ShortName         string         `json:"short_name"`
	RequiresImport    int            `json:"requires_import"`
	Visibility        string         `json:"visibility"`
	IsHidden          int            `json:"is_hidden"`
	PhysicalPath      sql.NullString `json:"physical_path"`
	StubPath          sql.NullString `json:"stub_path"`
	SHA256Hash        sql.NullString `json:"sha256_hash"`
	StartLine         sql.NullInt64  `json:"start_line"`
	StartCol          sql.NullInt64  `json:"start_col"`
	EndLine           sql.NullInt64  `json:"end_line"`
	EndCol            sql.NullInt64  `json:"end_col"`
	Docstring         sql.NullString `json:"docstring"`
}

type Symbol struct {
	SymbolID          int64          `json:"symbol_id"`
	ContainerID       int64          `json:"container_id"`
	OriginContainerID sql.NullInt64  `json:"origin_container_id"`
	Name              string         `json:"name"`
	QualifiedName     string         `json:"qualified_name"`
	SymbolKind        string         `json:"symbol_kind"`
	Visibility        string         `json:"visibility"`
	Provenance        string         `json:"provenance"`
	IsHidden          int            `json:"is_hidden"`
	StartLine         sql.NullInt64  `json:"start_line"`
	StartCol          sql.NullInt64  `json:"start_col"`
	EndLine           sql.NullInt64  `json:"end_line"`
	EndCol            sql.NullInt64  `json:"end_col"`
	Docstring         sql.NullString `json:"docstring"`
}

type Callable struct {
	SymbolID        int64          `json:"symbol_id"`
	IsAsync         int            `json:"is_async"`
	IsGenerator     int            `json:"is_generator"`
	IsStatic        int            `json:"is_static"`
	IsClassBound    int            `json:"is_class_bound"`
	HasOverloads    int            `json:"has_overloads"`
	OverloadCount   int            `json:"overload_count"`
	TypeParamsJSON  sql.NullString `json:"type_params_json"`
	ReturnTypeExpr  sql.NullString `json:"return_type_expr"`
	RawSignature    sql.NullString `json:"raw_signature"`
	SignatureSource string         `json:"signature_source"`
}

type Parameter struct {
	ParamID          int64          `json:"param_id"`
	CallableSymbolID int64          `json:"callable_symbol_id"`
	OverloadID       sql.NullInt64  `json:"overload_id"`
	Ordinal          int            `json:"ordinal"`
	Name             string         `json:"name"`
	PassKind         string         `json:"pass_kind"`
	TypeExpr         sql.NullString `json:"type_expr"`
	TypeSource       sql.NullString `json:"type_source"`
	DefaultExpr      sql.NullString `json:"default_expr"`
	IsOptional       int            `json:"is_optional"`
}

type StateMember struct {
	SymbolID          int64          `json:"symbol_id"`
	DeclaredTypeExpr  sql.NullString `json:"declared_type_expr"`
	RuntimeTypeName   string         `json:"runtime_type_name"`
	IsConstant        int            `json:"is_constant"`
	IsMutable         int            `json:"is_mutable"`
	LiteralValueRepr  sql.NullString `json:"literal_value_repr"`
	AccessMode        string         `json:"access_mode"`
}

type SymbolAlias struct {
	AliasID           int64  `json:"alias_id"`
	SourceContainerID int64  `json:"source_container_id"`
	ExposedName       string `json:"exposed_name"`
	TargetModuleName  string `json:"target_module_name"`
	TargetSymbolName  string `json:"target_symbol_name"`
	AliasKind         string `json:"alias_kind"`
	IsInDunderAll     int    `json:"is_in_dunder_all"`
}

type GoContainerFacet struct {
	ContainerID        int64          `json:"container_id"`
	PackageName        string         `json:"package_name"`
	ItemKind           string         `json:"item_kind"`
	TypeParamsJSON     sql.NullString `json:"type_params_json"`
	EmbeddedFieldsJSON sql.NullString `json:"embedded_fields_json"`
	IsExported         int            `json:"is_exported"`
}

type GoSymbolFacet struct {
	SymbolID      int64          `json:"symbol_id"`
	MemberKind    string         `json:"member_kind"`
	ReceiverKind  string         `json:"receiver_kind"`
	ReceiverType  sql.NullString `json:"receiver_type"`
	IsExported    int            `json:"is_exported"`
	IsVariadic    int            `json:"is_variadic"`
	SignatureJSON sql.NullString `json:"signature_json"`
}
