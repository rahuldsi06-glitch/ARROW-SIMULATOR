#!/usr/bin/env python3
import os
import uvicorn
from dotenv import load_dotenv

load_dotenv()

HOST = os.getenv("WEB_HOST", "127.0.0.1")
PORT = int(os.getenv("WEB_PORT", "8000"))

if __name__ == "__main__":
    print(f"🚀 Starting Arrow.Trade Algo Trader Web Interface at http://{HOST}:{PORT}")
    uvicorn.run("arrow_trader.web.app:app", host=HOST, port=PORT, reload=True)
