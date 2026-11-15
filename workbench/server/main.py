"""
UTSS Workbench Backend Server (FastAPI)
Provides API endpoints for cross-language catalog querying, symbol comparison,
bindgen synthesis, and OLAP analytics.
"""

from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Optional

try:
    from fastapi import FastAPI, HTTPException, Query
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
except ImportError:
    FastAPI = None
    BaseModel = object

from bridge_engine import BridgeEngine
from olap_pipeline import OlapPipeline
from utss_csharp_bindgen import CSharpBindgen

app = FastAPI(
    title="UTSS Workbench API",
    description="Cross-language analysis, bridge resolution, and code generation",
    version="0.1.0",
) if FastAPI is not None else None

if app is not None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

engine = BridgeEngine()
pipeline = OlapPipeline()

if app is not None:
    @app.get("/")
    def root():
        return {
            "name": "UTSS Workbench API",
            "version": "0.1.0",
            "status": "ready",
            "languages": list(engine.catalog_paths.keys()),
        }

    @app.get("/metrics")
    def get_metrics():
        """Returns row counts and stratum breakdowns across all 6 language catalogs."""
        return pipeline.aggregate_catalog_metrics()

    @app.get("/spectrum/{language}")
    def get_spectrum(language: str):
        """Returns spectrum table counts for a specific language catalog."""
        try:
            return engine.inspect_spectrum(language)
        except Exception as e:
            raise HTTPException(status_code=404, detail=str(e))

    @app.get("/symbols/search")
    def search_symbols(q: str = Query(..., min_length=1), limit: int = 50):
        """Searches for symbols matching query across all 6 language catalogs."""
        return engine.find_symbols(q, limit=limit)

    @app.post("/bindgen/csharp")
    def generate_csharp_bindings(
        language: str = Query("python", description="Language catalog to generate bindings from"),
        target_namespace: str = Query("Utss.Generated", description="Target C# namespace"),
    ):
        """Generates C# wrapper bindings from the requested catalog."""
        if language not in engine.catalog_paths:
            raise HTTPException(status_code=400, detail=f"Unknown language: {language}")
        
        path = engine.catalog_paths[language]
        if not path.exists():
            raise HTTPException(status_code=404, detail=f"Catalog not found for {language}")

        bindgen = CSharpBindgen(path)
        code = bindgen.generate(target_namespace=target_namespace)
        return {
            "language": language,
            "target_namespace": target_namespace,
            "line_count": len(code.splitlines()),
            "code": code,
        }


def run_server(host: str = "0.0.0.0", port: int = 8000):
    import uvicorn
    uvicorn.run("main:app", host=host, port=port, reload=True)


if __name__ == "__main__":
    if FastAPI is not None:
        run_server()
    else:
        print("[UTSS Workbench] FastAPI not installed in current environment. Install via requirements.txt.")
