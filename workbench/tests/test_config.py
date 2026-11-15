from pathlib import Path
from server.config import Config

def test_config_paths():
    assert Config.BASE_DIR.exists()
    assert Config.DBS_DIR.name == "dbs"
    assert Config.QUERIES_DIR.name == "queries"
    assert Config.STATIC_DIR.name == "static"
    assert Config.QUERY_TIMEOUT_SECONDS == 5.0
    assert Config.DEFAULT_PREVIEW_LIMIT == 500
