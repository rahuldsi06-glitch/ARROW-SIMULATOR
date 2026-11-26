from __future__ import annotations
import os
import json
import hmac
import time
import base64
import hashlib
import secrets
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

SECRET_KEY = os.environ.get("ARROW_AUTH_SECRET", "arrow-trade-pro-2.0-hmac-secret-key").encode("utf-8")


def _resolve_db_path() -> Path:
    candidates = [
        Path(__file__).resolve().parent.parent.parent / "data" / "game_cache" / "users.db",
        Path.cwd() / "data" / "game_cache" / "users.db",
        Path("/tmp/arrow_users.db"),
    ]
    for p in candidates:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            # Test writable
            with sqlite3.connect(str(p)) as conn:
                conn.execute("SELECT 1")
            return p
        except Exception:
            continue
    return Path("/tmp/arrow_users.db")


DB_PATH = _resolve_db_path()


class AuthService:
    """Handles user signup/signin, signed session tokens, behavior tracking, and Tradeify-style profile analytics."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DB_PATH
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    full_name TEXT NOT NULL,
                    password_hash TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    trade_id TEXT NOT NULL,
                    session_date TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    market TEXT NOT NULL,
                    instrument_type TEXT NOT NULL,
                    side TEXT NOT NULL,
                    qty INTEGER NOT NULL,
                    entry_price REAL NOT NULL,
                    exit_price REAL NOT NULL,
                    pnl REAL NOT NULL,
                    pnl_pct REAL NOT NULL,
                    exit_reason TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS user_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    metadata TEXT,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    @staticmethod
    def _hash_password(password: str, salt: Optional[str] = None) -> str:
        salt = salt or secrets.token_hex(16)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
        return f"{salt}${dk.hex()}"

    @staticmethod
    def _verify_password(password: str, stored_hash: str) -> bool:
        try:
            salt, expected_hex = stored_hash.split("$", 1)
            dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
            return hmac.compare_digest(dk.hex(), expected_hex)
        except Exception:
            return False

    @staticmethod
    def create_token(user: Dict[str, Any]) -> str:
        payload = {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "full_name": user["full_name"],
            "iat": int(time.time()),
        }
        raw = base64.urlsafe_b64encode(json.dumps(payload).encode("utf-8")).decode("utf-8")
        sig = hmac.new(SECRET_KEY, raw.encode("utf-8"), hashlib.sha256).hexdigest()
        return f"{raw}.{sig}"

    def verify_token(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        if not token:
            return None
        try:
            clean = token.replace("Bearer ", "").strip()
            raw, sig = clean.split(".", 1)
            expected_sig = hmac.new(SECRET_KEY, raw.encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(sig, expected_sig):
                return None
            payload = json.loads(base64.urlsafe_b64decode(raw.encode("utf-8")).decode("utf-8"))
            return payload
        except Exception:
            return None

    def signup(self, username: str, email: str, password: str, full_name: str = "") -> Dict[str, Any]:
        u = username.strip().lower()
        e = email.strip().lower()
        fn = full_name.strip() or username.strip()
        if len(u) < 3:
            raise ValueError("Username must be at least 3 characters.")
        if "@" not in e or "." not in e:
            raise ValueError("Please enter a valid email address.")
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters.")

        pw_hash = self._hash_password(password)
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT id FROM users WHERE username = ? OR email = ?",
                (u, e),
            ).fetchone()
            if existing:
                raise ValueError("An account with this username or email already exists.")
            cur = conn.execute(
                "INSERT INTO users (username, email, full_name, password_hash, created_at) VALUES (?, ?, ?, ?, ?)",
                (u, e, fn, pw_hash, now),
            )
            user_id = cur.lastrowid
            conn.execute(
                "INSERT INTO user_events (user_id, event_type, metadata, created_at) VALUES (?, ?, ?, ?)",
                (user_id, "SIGNUP", json.dumps({"username": u}), now),
            )
            conn.commit()

        user = {"id": user_id, "username": u, "email": e, "full_name": fn, "created_at": now}
        return {"token": self.create_token(user), "user": user}

    def login(self, identifier: str, password: str) -> Dict[str, Any]:
        ident = identifier.strip().lower()
        if not ident or not password:
            raise ValueError("Username/Email and password are required.")

        with self._conn() as conn:
            row = conn.execute(
                "SELECT id, username, email, full_name, password_hash, created_at FROM users WHERE username = ? OR email = ?",
                (ident, ident),
            ).fetchone()
            if not row or not self._verify_password(password, row["password_hash"]):
                raise ValueError("Invalid username/email or password.")
            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            conn.execute(
                "INSERT INTO user_events (user_id, event_type, metadata, created_at) VALUES (?, ?, ?, ?)",
                (row["id"], "LOGIN", json.dumps({"identifier": ident}), now),
            )
            conn.commit()

        user = {
            "id": row["id"],
            "username": row["username"],
            "email": row["email"],
            "full_name": row["full_name"],
            "created_at": row["created_at"],
        }
        return {"token": self.create_token(user), "user": user}

    def record_trade(self, user_id: int, trade: Dict[str, Any]) -> None:
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        session_date = str(trade.get("session_date") or datetime.utcnow().strftime("%Y-%m-%d"))[:10]
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO user_trades (
                    user_id, trade_id, session_date, symbol, market, instrument_type,
                    side, qty, entry_price, exit_price, pnl, pnl_pct, exit_reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    str(trade.get("trade_id", "")),
                    session_date,
                    str(trade.get("symbol", "")),
                    str(trade.get("market", "IN")),
                    str(trade.get("instrument_type", "options")),
                    str(trade.get("option_type", "LONG")),
                    int(trade.get("quantity", 0)),
                    float(trade.get("entry_price", 0.0)),
                    float(trade.get("exit_price", 0.0)),
                    float(trade.get("pnl", 0.0)),
                    float(trade.get("pnl_pct", 0.0)),
                    str(trade.get("exit_reason", "MANUAL_EXIT")),
                    now,
                ),
            )
            conn.execute(
                "INSERT INTO user_events (user_id, event_type, metadata, created_at) VALUES (?, ?, ?, ?)",
                (user_id, "TRADE_CLOSE", json.dumps({"symbol": trade.get("symbol"), "pnl": trade.get("pnl")}), now),
            )
            conn.commit()

    def record_event(self, user_id: int, event_type: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO user_events (user_id, event_type, metadata, created_at) VALUES (?, ?, ?, ?)",
                (user_id, event_type, json.dumps(metadata or {}), now),
            )
            conn.commit()

    def get_profile(self, user_id: int, market_filter: Optional[str] = None) -> Dict[str, Any]:
        with self._conn() as conn:
            if market_filter:
                rows = conn.execute(
                    "SELECT * FROM user_trades WHERE user_id = ? AND market = ? ORDER BY id DESC LIMIT 500",
                    (user_id, market_filter),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM user_trades WHERE user_id = ? ORDER BY id DESC LIMIT 500",
                    (user_id,),
                ).fetchall()
            events = conn.execute(
                "SELECT event_type, metadata, created_at FROM user_events WHERE user_id = ? ORDER BY id DESC LIMIT 30",
                (user_id,),
            ).fetchall()

        trades = [dict(r) for r in rows]
        wins = [t["pnl"] for t in trades if t["pnl"] > 0]
        losses = [t["pnl"] for t in trades if t["pnl"] < 0]
        gross_win = sum(wins)
        gross_loss = abs(sum(losses))
        net_pnl = round(sum(t["pnl"] for t in trades), 2)
        total = len(trades)
        win_rate = round((len(wins) / total) * 100.0, 1) if total > 0 else 0.0
        profit_factor = round(gross_win / gross_loss, 2) if gross_loss > 0 else (99.9 if gross_win > 0 else 0.0)
        avg_win = round(gross_win / len(wins), 2) if wins else 0.0
        avg_loss = round(sum(losses) / len(losses), 2) if losses else 0.0

        calendar: Dict[str, Dict[str, Any]] = {}
        for t in trades:
            d = t["session_date"]
            if d not in calendar:
                calendar[d] = {"date": d, "pnl": 0.0, "trades": 0, "wins": 0, "losses": 0}
            calendar[d]["pnl"] = round(calendar[d]["pnl"] + t["pnl"], 2)
            calendar[d]["trades"] += 1
            if t["pnl"] > 0:
                calendar[d]["wins"] += 1
            elif t["pnl"] < 0:
                calendar[d]["losses"] += 1

        day_pnls = [c["pnl"] for c in calendar.values()]
        best_day = max(day_pnls) if day_pnls else 0.0
        worst_day = min(day_pnls) if day_pnls else 0.0

        return {
            "stats": {
                "total_trades": total,
                "wins": len(wins),
                "losses": len(losses),
                "win_rate": win_rate,
                "net_pnl": net_pnl,
                "profit_factor": profit_factor,
                "avg_win": avg_win,
                "avg_loss": avg_loss,
                "best_day": best_day,
                "worst_day": worst_day,
            },
            "calendar": calendar,
            "trades": trades,
            "recent_events": [dict(e) for e in events],
        }
