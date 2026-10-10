"""
Vercel Serverless Entrypoint for Arrow Trade & Simulator
"""
import sys
from pathlib import Path

# Add project root directory to sys.path so modules like arrow_trader are importable
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from arrow_trader.web.app import app

# Vercel's Python runtime exposes ASGI application as `app`
