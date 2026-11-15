pub mod strata {
    pub const AMBIENT: i64 = 0;
    pub const STDLIB: i64 = 1;
    pub const ECOSYSTEM: i64 = 2;
    pub const WORKSPACE: i64 = 3;
}

pub mod container_kinds {
    pub const AMBIENT_SCOPE: &str = "ambient_scope";
    pub const CRATE: &str = "crate";
    pub const MODULE: &str = "module";
    pub const STRUCT: &str = "struct";
    pub const ENUM: &str = "enum";
    pub const TRAIT: &str = "trait";
    pub const UNION: &str = "union";
}

pub mod symbol_kinds {
    pub const KEYWORD: &str = "keyword";
    pub const TYPE_ALIAS: &str = "type_alias";
    pub const FUNCTION: &str = "function";
    pub const METHOD: &str = "method";
    pub const ASSOCIATED_FN: &str = "associated_fn";
    pub const STRUCT_FIELD: &str = "struct_field";
    pub const ENUM_VARIANT: &str = "enum_variant";
    pub const CONSTANT: &str = "constant";
    pub const STATIC_VAR: &str = "static_var";
    pub const MACRO: &str = "macro";
}

pub mod visibilities {
    pub const PUBLIC: &str = "public";
    pub const PUB_CRATE: &str = "pub_crate";
    pub const PUB_SUPER: &str = "pub_super";
    pub const PRIVATE: &str = "private";
}

pub mod provenances {
    pub const AMBIENT_KEYWORD: &str = "ambient_keyword";
    pub const AMBIENT_PRELUDE: &str = "ambient_prelude";
    pub const STD_ITEM: &str = "std_item";
    pub const CRATE_ITEM: &str = "crate_item";
    pub const AST_DEFINED: &str = "ast_defined";
}

pub mod pass_kinds {
    pub const VAL: &str = "val";
    pub const REF: &str = "ref";
    pub const MUT_REF: &str = "mut_ref";
    pub const SELF_VAL: &str = "self_val";
    pub const SELF_REF: &str = "self_ref";
    pub const SELF_MUT_REF: &str = "self_mut_ref";
}

pub mod access_modes {
    pub const READ_ONLY: &str = "read_only";
    pub const READ_WRITE: &str = "read_write";
}
