import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from server.config import Config
from server.routes import router

app = FastAPI(
    title="UTSS Universal Language Analysis & Synthesis Platform",
    description="Interactive language internals workbench, tutor, and comparative data science tool.",
    version="0.1.0"
)

# Include API endpoints
app.include_router(router)

# Mount static assets if directory exists
if Config.STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=Config.STATIC_DIR), name="static")
    if (Config.STATIC_DIR / "assets").exists():
        app.mount("/assets", StaticFiles(directory=Config.STATIC_DIR / "assets"), name="assets")

def main():
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

if __name__ == "__main__":
    main()
