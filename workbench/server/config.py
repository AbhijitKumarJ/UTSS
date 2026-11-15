from pathlib import Path

class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent
    DBS_DIR = BASE_DIR / "dbs"
    QUERIES_DIR = BASE_DIR / "queries"
    STATIC_DIR = BASE_DIR / "static"
    QUERY_TIMEOUT_SECONDS = 5.0
    DEFAULT_PREVIEW_LIMIT = 500
