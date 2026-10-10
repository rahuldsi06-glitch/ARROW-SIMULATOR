#!/usr/bin/env python3
"""
Arrow Trade Pro - Options Battle Simulator Launcher
Launches the high-performance Tesla/Apple style Trading Game Simulator.
"""
import os
import sys
import webbrowser
import threading
import time
import uvicorn
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("GAME_HOST", "127.0.0.1")
PORT = int(os.getenv("GAME_PORT", "8000"))


def open_browser():
    time.sleep(1.2)
    url = f"http://{HOST}:{PORT}/game"
    print(f"\n🎮 Launching Arrow Trade Simulator in your browser: {url}\n")
    webbrowser.open(url)


if __name__ == "__main__":
    print("=" * 70)
    print("  🎯 ARROW TRADE PRO // OPTIONS BATTLE SIMULATOR")
    print("  Engineered for Pro Traders & Gamified Market Simulation")
    print("=" * 70)
    print(f"  Server URL: http://{HOST}:{PORT}/game")
    print(f"  API Docs:   http://{HOST}:{PORT}/docs")
    print("=" * 70)

    # Launch browser automatically in background
    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run("arrow_trader.web.app:app", host=HOST, port=PORT, reload=False)
