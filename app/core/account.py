from typing import List, Optional
from enum import Enum
from datetime import datetime
from dataclasses import dataclass

from app.core.exceptions import (
    ClaudeAuthenticationError,
    ClaudeRateLimitedError,
    OAuthAuthenticationNotAllowedError,
    OrganizationDisabledError,
)


class AccountStatus(str, Enum):
    VALID = "valid"
    INVALID = "invalid"
    RATE_LIMITED = "rate_limited"


class AuthType(str, Enum):
    COOKIE_ONLY = "cookie_only"
    OAUTH_ONLY = "oauth_only"
    BOTH = "both"


@dataclass
class OAuthToken:
    """Encapsulates OAuth credentials for an account."""

    access_token: str
    refresh_token: str
    expires_at: float  # Unix timestamp

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OAuthToken":
        """Create from dictionary."""
        return cls(
            access_token=data["access_token"],
            refresh_token=data["refresh_token"],
            expires_at=data["expires_at"],
        )


class Account:
    """Represents a Claude.ai account with cookie and/or OAuth authentication."""

    def __init__(
        self,
        organization_uuid: str,
        capabilities: Optional[List[str]] = None,
        cookie_value: Optional[str] = None,
        oauth_token: Optional[OAuthToken] = None,
        auth_type: AuthType = AuthType.COOKIE_ONLY,
    ):
        self.organization_uuid = organization_uuid
        self.capabilities = capabilities
        self.cookie_value = cookie_value
        self.status = AccountStatus.VALID
        self.auth_type = auth_type
        self.last_used = datetime.now()
        self.resets_at: Optional[datetime] = None
        self.oauth_token: Optional[OAuthToken] = oauth_token

    def __enter__(self) -> "Account":
        """Enter the context manager."""
        self.last_used = datetime.now()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the context manager and handle CookieRateLimitedError."""
        if exc_type is ClaudeRateLimitedError and isinstance(
            exc_val, ClaudeRateLimitedError
        ):
            self.status = AccountStatus.RATE_LIMITED
            self.resets_at = exc_val.resets_at
            self.save()

        if exc_type is ClaudeAuthenticationError and isinstance(
            exc_val, ClaudeAuthenticationError
        ):
            self.status = AccountStatus.INVALID
            self.save()

        if exc_type is OrganizationDisabledError and isinstance(
            exc_val, OrganizationDisabledError
        ):
            self.status = AccountStatus.INVALID
            self.save()

        if exc_type is OAuthAuthenticationNotAllowedError and isinstance(
            exc_val, OAuthAuthenticationNotAllowedError
        ):
            if self.auth_type == AuthType.BOTH:
                self.auth_type = AuthType.COOKIE_ONLY
            else:
                self.status = AccountStatus.INVALID
            self.save()

        return False

    def save(self) -> None:
        from app.services.account import account_manager

        account_manager.save_accounts()

    def to_dict(self) -> dict:
        """Convert Account to dictionary for JSON serialization."""
        return {
            "organization_uuid": self.organization_uuid,
            "capabilities": self.capabilities,
            "cookie_value": self.cookie_value,
            "status": self.status.value,
            "auth_type": self.auth_type.value,
            "last_used": self.last_used.isoformat(),
            "resets_at": self.resets_at.isoformat() if self.resets_at else None,
            "oauth_token": self.oauth_token.to_dict() if self.oauth_token else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Account":
        """Create Account from dictionary."""
        account = cls(
            organization_uuid=data["organization_uuid"],
            capabilities=data.get("capabilities"),
            cookie_value=data.get("cookie_value"),
            auth_type=AuthType(data["auth_type"]),
        )
        account.status = AccountStatus(data["status"])
        account.last_used = datetime.fromisoformat(data["last_used"])
        account.resets_at = (
            datetime.fromisoformat(data["resets_at"]) if data["resets_at"] else None
        )

        if "oauth_token" in data and data["oauth_token"]:
            account.oauth_token = OAuthToken.from_dict(data["oauth_token"])

        return account

    @property
    def is_pro(self) -> bool:
        """Check if account has pro capabilities."""
        if not self.capabilities:
            return False

        pro_keywords = ["pro", "enterprise", "raven", "max"]
        return any(
            keyword in cap.lower()
            for cap in self.capabilities
            for keyword in pro_keywords
        )

    @property
    def is_max(self) -> bool:
        """Check if account has max capabilities."""
        if not self.capabilities:
            return False

        return any("max" in cap.lower() for cap in self.capabilities)

    def __repr__(self) -> str:
        """String representation of the Account."""
        return f"<Account organization_uuid={self.organization_uuid[:8]}... status={self.status.value} auth_type={self.auth_type.value}>"
