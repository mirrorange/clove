import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, HttpUrl, field_validator
from dotenv import load_dotenv

class Settings(BaseSettings):
    """Application settings with environment variable and JSON config support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_ignore_empty=True,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """Customize settings sources to add JSON config support.

        Priority order (highest to lowest):
        1. JSON config file
        2. Environment variables
        3. .env file
        4. Default values
        """
        return (
            init_settings,
            cls._json_config_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        )

    @classmethod
    def _json_config_settings(cls) -> Dict[str, Any]:
        """Load settings from JSON config file in data_folder."""

        # Check if NO_FILESYSTEM_MODE is enabled
        if os.environ.get("NO_FILESYSTEM_MODE", "").lower() in ("true", "1", "yes"):
            return {}

        # Load .env file to ensure environment variables are available
        load_dotenv()

        # First get data_folder from env or default
        data_folder = os.environ.get(
            "DATA_FOLDER", str(Path.home() / ".clove" / "data")
        )

        config_path = os.path.join(data_folder, "config.json")

        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    return config_data
            except (json.JSONDecodeError, IOError):
                # If there's an error reading the JSON, just return empty dict
                return {}
        return {}

    # Server settings
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=5201, env="PORT")

    # Application configuration
    data_folder: Path = Field(
        default=Path.home() / ".clove" / "data",
        env="DATA_FOLDER",
        description="Folder path for storing persistent data (accounts, etc.)",
    )
    locales_folder: Path = Field(
        default=Path(__file__).parent.parent / "locales",
        env="LOCALES_FOLDER",
        description="Folder path for storing translation files",
    )
    static_folder: Path = Field(
        default=Path(__file__).parent.parent / "static",
        env="STATIC_FOLDER",
        description="Folder path for storing static files",
    )
    default_language: str = Field(
        default="en",
        env="DEFAULT_LANGUAGE",
        description="Default language code for translations",
    )
    retry_attempts: int = Field(
        default=3,
        env="RETRY_ATTEMPTS",
        description="Number of retry attempts for failed requests",
    )
    retry_interval: int = Field(
        default=1,
        env="RETRY_INTERVAL",
        description="Interval between retry attempts in seconds",
    )
    no_filesystem_mode: bool = Field(
        default=False,
        env="NO_FILESYSTEM_MODE",
        description="When True, disables all filesystem operations (accounts/settings stored in memory only)",
    )

    # Proxy settings
    proxy_url: Optional[str] = Field(default=None, env="PROXY_URL")

    # API Keys
    api_keys: List[str] | str = Field(
        default_factory=list,
        env="API_KEYS",
        description="Comma-separated list of API keys",
    )
    admin_api_keys: List[str] | str = Field(
        default_factory=list,
        env="ADMIN_API_KEYS",
        description="Comma-separated list of admin API keys",
    )

    # Claude URLs
    claude_ai_url: HttpUrl = Field(default="https://claude.ai", env="CLAUDE_AI_URL")
    claude_api_baseurl: HttpUrl = Field(
        default="https://api.anthropic.com", env="CLAUDE_API_BASEURL"
    )

    # Cookies
    cookies: List[str] | str = Field(
        default_factory=list,
        env="COOKIES",
        description="Comma-separated list of Claude.ai cookies",
    )

    # Content processing
    custom_prompt: Optional[str] = Field(default=None, env="CUSTOM_PROMPT")
    use_real_roles: bool = Field(default=True, env="USE_REAL_ROLES")
    human_name: str = Field(default="Human", env="CUSTOM_HUMAN_NAME")
    assistant_name: str = Field(default="Assistant", env="CUSTOM_ASSISTANT_NAME")
    pad_tokens: List[str] | str = Field(default_factory=list, env="PAD_TOKENS")
    padtxt_length: int = Field(default=0, env="PADTXT_LENGTH")
    allow_external_images: bool = Field(
        default=False,
        env="ALLOW_EXTERNAL_IMAGES",
        description="Allow downloading images from external URLs",
    )

    # Request settings
    request_timeout: int = Field(default=60, env="REQUEST_TIMEOUT")
    request_retries: int = Field(default=3, env="REQUEST_RETRIES")
    request_retry_interval: int = Field(default=1, env="REQUEST_RETRY_INTERVAL")

    # Feature flags
    preserve_chats: bool = Field(default=False, env="PRESERVE_CHATS")

    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_to_file: bool = Field(
        default=False, env="LOG_TO_FILE", description="Enable logging to file"
    )
    log_file_path: str = Field(
        default="logs/app.log", env="LOG_FILE_PATH", description="Log file path"
    )
    log_file_rotation: str = Field(
        default="10 MB",
        env="LOG_FILE_ROTATION",
        description="Log file rotation (e.g., '10 MB', '1 day', '1 week')",
    )
    log_file_retention: str = Field(
        default="7 days",
        env="LOG_FILE_RETENTION",
        description="Log file retention (e.g., '7 days', '1 month')",
    )
    log_file_compression: str = Field(
        default="zip",
        env="LOG_FILE_COMPRESSION",
        description="Log file compression format",
    )

    # Session management settings
    session_timeout: int = Field(
        default=300,
        env="SESSION_TIMEOUT",
        description="Session idle timeout in seconds",
    )
    session_cleanup_interval: int = Field(
        default=30,
        env="SESSION_CLEANUP_INTERVAL",
        description="Interval for cleaning up expired sessions in seconds",
    )
    max_sessions_per_cookie: int = Field(
        default=3,
        env="MAX_SESSIONS_PER_COOKIE",
        description="Maximum number of concurrent sessions per cookie",
    )

    # Account management settings
    account_task_interval: int = Field(
        default=60,
        env="ACCOUNT_TASK_INTERVAL",
        description="Interval for account management task in seconds",
    )

    # Tool call settings
    tool_call_timeout: int = Field(
        default=300,
        env="TOOL_CALL_TIMEOUT",
        description="Timeout for pending tool calls in seconds",
    )
    tool_call_cleanup_interval: int = Field(
        default=60,
        env="TOOL_CALL_CLEANUP_INTERVAL",
        description="Interval for cleaning up expired tool calls in seconds",
    )

    # Cache settings
    cache_timeout: int = Field(
        default=300,
        env="CACHE_TIMEOUT",
        description="Timeout for cache checkpoints in seconds (default: 5 minutes)",
    )
    cache_cleanup_interval: int = Field(
        default=60,
        env="CACHE_CLEANUP_INTERVAL",
        description="Interval for cleaning up expired cache checkpoints in seconds",
    )

    # Claude OAuth settings
    oauth_client_id: str = Field(
        default="9d1c250a-e61b-44d9-88ed-5944d1962f5e",
        env="OAUTH_CLIENT_ID",
        description="OAuth client ID for Claude authentication",
    )
    oauth_authorize_url: str = Field(
        default="https://claude.ai/v1/oauth/{organization_uuid}/authorize",
        env="OAUTH_AUTHORIZE_URL",
        description="OAuth authorization endpoint URL template",
    )
    oauth_token_url: str = Field(
        default="https://console.anthropic.com/v1/oauth/token",
        env="OAUTH_TOKEN_URL",
        description="OAuth token exchange endpoint URL",
    )
    oauth_redirect_uri: str = Field(
        default="https://console.anthropic.com/oauth/code/callback",
        env="OAUTH_REDIRECT_URI",
        description="OAuth redirect URI for authorization flow",
    )

    # Claude API Specific
    max_models: List[str] | str = Field(
        default=["claude-opus-4-20250514"],
        env="MAX_MODELS",
        description="Comma-separated list of models that require max plan accounts",
    )

    @field_validator(
        "api_keys", "admin_api_keys", "cookies", "max_models", "pad_tokens"
    )
    def parse_comma_separated(cls, v: str | List[str]) -> List[str]:
        """Parse comma-separated string."""
        if isinstance(v, str):
            return [key.strip() for key in v.split(",") if key.strip()]
        return v


settings = Settings()
