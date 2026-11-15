using System.Text.Json.Serialization;

namespace UTSS.CSharp;

public static class Strata
{
    public const int Ambient = 0;
    public const int Runtime = 1;
    public const int Ecosystem = 2;
    public const int Workspace = 3;
}

public static class ContainerKinds
{
    public const string AmbientScope = "ambient_scope";
    public const string Namespace = "namespace";
    public const string Class = "class";
    public const string Struct = "struct";
    public const string RecordClass = "record";
    public const string RecordStruct = "record_struct";
    public const string Interface = "interface";
    public const string Enum = "enum";
    public const string Delegate = "delegate";
}

public static class SymbolKinds
{
    public const string Keyword = "keyword";
    public const string TypeAlias = "type_alias";
    public const string Method = "method";
    public const string Constructor = "constructor";
    public const string Property = "property";
    public const string Field = "field";
    public const string Event = "event";
    public const string Indexer = "indexer";
    public const string Operator = "operator";
    public const string ConversionOperator = "conversion_operator";
    public const string Constant = "constant";
    public const string EnumMember = "enum_member";
}

public static class Visibilities
{
    public const string Public = "public";
    public const string Internal = "internal";
    public const string Private = "private";
    public const string Protected = "protected";
    public const string ProtectedInternal = "protected_internal";
    public const string PrivateProtected = "private_protected";
}

public static class Provenances
{
    public const string AmbientKeyword = "ambient_keyword";
    public const string AmbientTypeAlias = "ambient_type_alias";
    public const string AmbientGlobalUsing = "ambient_global_using";
    public const string BclReflected = "bcl_reflected";
    public const string NugetReferenced = "nuget_referenced";
    public const string AstDefined = "ast_defined";
}

public static class PassKinds
{
    public const string Value = "value";
    public const string Ref = "ref";
    public const string Out = "out";
    public const string In = "in";
    public const string Params = "params";
    public const string Optional = "optional";
}

public static class AccessModes
{
    public const string ReadOnly = "read_only";
    public const string ReadWrite = "read_write";
    public const string InitOnly = "init_only";
}

public record EnvironmentRecord(
    long EnvId,
    string Language,
    string RuntimeName,
    string LanguageVersion,
    int VersionMajor,
    int VersionMinor,
    int VersionMicro,
    string PlatformTriplet,
    string SysPlatform,
    string ExecutablePath,
    string? CapturedAt = null
);

public record DistributionRecord(
    long DistId,
    long EnvId,
    int Stratum,
    string DistName,
    string DistVersion,
    string? Summary = null
);

public record ContainerRecord(
    long ContainerId,
    long DistId,
    long? ParentContainerId,
    string ContainerKind,
    string QualifiedName,
    string ShortName,
    int RequiresImport = 1,
    string Visibility = Visibilities.Public,
    int IsHidden = 0,
    string? PhysicalPath = null,
    string? StubPath = null,
    string? Sha256Hash = null,
    int? StartLine = null,
    int? StartCol = null,
    int? EndLine = null,
    int? EndCol = null,
    string? Docstring = null
);

public record SymbolRecord(
    long SymbolId,
    long ContainerId,
    long? OriginContainerId,
    string Name,
    string QualifiedName,
    string SymbolKind,
    string Visibility = Visibilities.Public,
    string Provenance = Provenances.AstDefined,
    int IsHidden = 0,
    int? StartLine = null,
    int? StartCol = null,
    int? EndLine = null,
    int? EndCol = null,
    string? Docstring = null
);

public record CallableRecord(
    long SymbolId,
    int IsAsync = 0,
    int IsGenerator = 0,
    int IsStatic = 0,
    int IsClassBound = 0,
    int HasOverloads = 0,
    int OverloadCount = 0,
    string? TypeParamsJson = null,
    string? ReturnTypeExpr = null,
    string? RawSignature = null,
    string SignatureSource = "reflection"
);

public record CallableOverloadRecord(
    long OverloadId,
    long CallableSymbolId,
    int OverloadOrdinal,
    string? TypeParamsJson,
    string? ReturnTypeExpr,
    string RawSignature
);

public record ParameterRecord(
    long ParamId,
    long CallableSymbolId,
    long? OverloadId,
    int Ordinal,
    string Name,
    string PassKind = PassKinds.Value,
    string? TypeExpr = null,
    string? TypeSource = null,
    string? DefaultExpr = null,
    int IsOptional = 0
);

public record StateMemberRecord(
    long SymbolId,
    string? DeclaredTypeExpr,
    string RuntimeTypeName,
    int IsConstant = 0,
    int IsMutable = 1,
    string? LiteralValueRepr = null,
    string AccessMode = AccessModes.ReadWrite
);

public record SymbolAliasRecord(
    long AliasId,
    long SourceContainerId,
    string ExposedName,
    string TargetModuleName,
    string TargetSymbolName,
    string AliasKind,
    int IsInDunderAll = 0
);

public record CsContainerFacetRecord(
    long ContainerId,
    string TypeKind,
    int IsSealed = 0,
    int IsAbstract = 0,
    int IsStatic = 0,
    int IsReadonlyStruct = 0,
    int IsRefStruct = 0,
    string? BaseTypeQName = null,
    string? ImplementedInterfacesJson = null,
    string? GenericTypeParametersJson = null,
    string? AttributesJson = null
);

public record CsSymbolFacetRecord(
    long SymbolId,
    string MemberKind,
    int IsVirtual = 0,
    int IsOverride = 0,
    int IsAbstract = 0,
    int IsSealed = 0,
    int IsAsync = 0,
    int IsUnsafe = 0,
    int IsExtensionMethod = 0,
    int IsInitOnly = 0,
    int HasGetter = 0,
    int HasSetter = 0,
    string? ExplicitInterfaceSpecifier = null,
    string? OperatorKind = null,
    string? AttributesJson = null
);
