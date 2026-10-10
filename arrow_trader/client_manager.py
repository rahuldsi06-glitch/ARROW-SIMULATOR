from __future__ import annotations
import logging
from typing import Optional, Dict, Any, Tuple
from pyarrow_client import ArrowClient, ArrowStreams
from .config import Config

logger = logging.getLogger(__name__)


class ArrowClientManager:
    _instance: Optional[ArrowClientManager] = None

    def __init__(self):
        self.app_id = Config.get_app_id()
        self.root_url = Config.get_root_url()
        self.client: Optional[ArrowClient] = None
        self._user_details: Optional[Dict[str, Any]] = None
        self._initialize_client()

    @classmethod
    def get_instance(cls) -> ArrowClientManager:
        if cls._instance is None:
            cls._instance = ArrowClientManager()
        return cls._instance

    def _initialize_client(self) -> None:
        self.app_id = Config.get_app_id()
        self.root_url = Config.get_root_url()
        if self.app_id:
            self.client = ArrowClient(
                app_id=self.app_id,
                root_url=self.root_url if self.root_url else None,
                timeout=15
            )
            cached_token = Config.get_access_token()
            if cached_token:
                try:
                    self.client.set_token(cached_token)
                except Exception as e:
                    logger.warning(f"Failed to set cached token: {e}")
        else:
            self.client = None

    def reconfigure(self, app_id: str, app_secret: Optional[str] = None, root_url: Optional[str] = None) -> None:
        if app_id:
            Config.save_env_var("ARROW_APP_ID", app_id)
        if app_secret:
            Config.save_env_var("ARROW_APP_SECRET", app_secret)
        if root_url:
            Config.save_env_var("ARROW_ROOT_URL", root_url)
        self._initialize_client()

    def is_authenticated(self) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
        """
        Checks if client has a valid session.
        Returns: (is_auth, user_details_dict, error_message)
        """
        if not self.client:
            return False, None, "App ID is not configured. Please set ARROW_APP_ID."

        token = self.client.get_token()
        if not token:
            return False, None, "No active access token found."

        try:
            user_info = self.client.get_user_details()
            self._user_details = user_info
            return True, user_info, None
        except Exception as e:
            err_str = str(e)
            return False, None, err_str

    def auto_login(
        self,
        user_id: Optional[str] = None,
        password: Optional[str] = None,
        app_secret: Optional[str] = None,
        totp_secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Automated TOTP login. Uses parameters or loads from config/.env.
        """
        user_id = (user_id or Config.get_user_id()).strip()
        password = (password or Config.get_password()).strip()
        app_secret = (app_secret or Config.get_app_secret()).strip()
        totp_secret = (totp_secret or Config.get_totp_secret()).strip()

        if not self.app_id:
            raise ValueError("App ID is required. Please set ARROW_APP_ID.")
        if not user_id:
            raise ValueError("User ID is required.")
        if not password:
            raise ValueError("Password is required.")
        if not app_secret:
            raise ValueError("App Secret is required.")
        if not totp_secret:
            raise ValueError("TOTP Secret is required.")

        if not self.client:
            self._initialize_client()

        result = self.client.auto_login(
            user_id=user_id,
            password=password,
            app_secret=app_secret,
            totp_secret=totp_secret
        )

        token = self.client.get_token()
        if token:
            Config.save_token_cache(token, result)
            self._user_details = result

        return result

    def get_login_url(self) -> str:
        """
        Get the OAuth login URL for manual web login.
        """
        if not self.client:
            self._initialize_client()
        if not self.client:
            raise ValueError("Client could not be initialized. Please configure ARROW_APP_ID.")
        return self.client.login_url()

    def complete_web_login(self, request_token: str, app_secret: Optional[str] = None) -> Dict[str, Any]:
        """
        Exchange callback request_token for access token.
        """
        app_secret = (app_secret or Config.get_app_secret()).strip()
        if not app_secret:
            raise ValueError("App Secret is required.")
        if not self.client:
            self._initialize_client()

        result = self.client.login(
            request_token=request_token,
            app_secret=app_secret
        )
        token = self.client.get_token()
        if token:
            Config.save_token_cache(token, result)
            self._user_details = result
        return result

    def set_token(self, token: str) -> bool:
        """
        Manually set access token and verify.
        """
        if not self.client:
            self._initialize_client()
        if not self.client:
            raise ValueError("Please configure ARROW_APP_ID first.")

        self.client.set_token(token)
        is_valid, user_data, err = self.is_authenticated()
        if is_valid:
            Config.save_token_cache(token, user_data)
            return True
        else:
            raise ValueError(f"Invalid token or authentication failed: {err}")

    def logout(self) -> None:
        """
        Invalidate session and delete cached token.
        """
        if self.client:
            try:
                self.client.invalidate_session()
            except Exception:
                pass
        Config.clear_token_cache()
        self._user_details = None
        self._initialize_client()

    def get_client(self) -> ArrowClient:
        if not self.client:
            self._initialize_client()
        if not self.client:
            raise ValueError("ArrowClient is not initialized. Please set ARROW_APP_ID.")
        return self.client

    def create_streams(self, debug: bool = False) -> ArrowStreams:
        token = self.client.get_token() if self.client else ""
        if not token:
            raise ValueError("Authentication token is required to start live stream.")
        return ArrowStreams(
            appID=self.app_id,
            token=token,
            debug=debug
        )
