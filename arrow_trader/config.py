import os
import json
import time
from pathlib import Path
from typing import Optional, Dict, Any
from dotenv import load_dotenv, set_key

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
TOKEN_CACHE_PATH = BASE_DIR / ".token_cache.json"

if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
else:
    load_dotenv()


class Config:
    @staticmethod
    def get_app_id() -> str:
        return os.getenv("ARROW_APP_ID", "").strip()

    @staticmethod
    def get_app_secret() -> str:
        return os.getenv("ARROW_APP_SECRET", "").strip()

    @staticmethod
    def get_user_id() -> str:
        return os.getenv("ARROW_USER_ID", "").strip()

    @staticmethod
    def get_password() -> str:
        return os.getenv("ARROW_PASSWORD", "").strip()

    @staticmethod
    def get_totp_secret() -> str:
        return os.getenv("ARROW_TOTP_SECRET", "").strip()

    @staticmethod
    def get_root_url() -> str:
        return os.getenv("ARROW_ROOT_URL", "https://edge.arrow.trade").strip()

    @staticmethod
    def get_access_token() -> str:
        # Check environment variable first
        env_token = os.getenv("ARROW_ACCESS_TOKEN", "").strip()
        if env_token:
            return env_token
        # Check token cache
        cached = Config.load_token_cache()
        if cached and "token" in cached:
            # Check if token is within 23 hours
            created_at = cached.get("created_at", 0)
            if time.time() - created_at < 23 * 3600:
                return cached["token"]
        return ""

    @staticmethod
    def save_token_cache(token: str, user_data: Optional[Dict[str, Any]] = None) -> None:
        cache_data = {
            "token": token,
            "created_at": time.time(),
            "user_data": user_data or {}
        }
        try:
            with open(TOKEN_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def load_token_cache() -> Optional[Dict[str, Any]]:
        if not TOKEN_CACHE_PATH.exists():
            return None
        try:
            with open(TOKEN_CACHE_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    @staticmethod
    def clear_token_cache() -> None:
        if TOKEN_CACHE_PATH.exists():
            try:
                TOKEN_CACHE_PATH.unlink()
            except Exception:
                pass

    @staticmethod
    def save_env_var(key: str, value: str) -> None:
        if not ENV_PATH.exists():
            ENV_PATH.touch()
        set_key(str(ENV_PATH), key, value)
        os.environ[key] = value
