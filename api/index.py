"""
Vercel Serverless Entrypoint for Arrow Trade & Simulator
"""
import sys
from pathlib import Path
from fastapi import Request
from fastapi.responses import HTMLResponse, JSONResponse

# Add project root directory to sys.path so modules like arrow_trader are importable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from arrow_trader.web.app import app, STATIC_DIR

# Direct fallback route in case Vercel rewrites directly to /api/index
@app.get("/api/index")
@app.get("/api/index.py")
def get_index_entrypoint():
    game_file = STATIC_DIR / "game.html"
    if game_file.exists():
        return HTMLResponse(content=game_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Arrow Trade Pro Simulator</h1>", status_code=200)

@app.get("/api/ping")
def ping_health():
    return {
        "status": "online",
        "static_dir": str(STATIC_DIR),
        "static_dir_exists": STATIC_DIR.exists(),
        "game_html_exists": (STATIC_DIR / "game.html").exists(),
        "game_css_exists": (STATIC_DIR / "game.css").exists(),
        "game_js_exists": (STATIC_DIR / "game.js").exists(),
    }
