from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from uuid import UUID
import time

from app.core.exceptions import OAuthExchangeError
from app.dependencies.auth import AdminAuthDep
from app.services.account import account_manager
from app.core.account import AuthType, AccountStatus, OAuthToken
from app.services.oauth import oauth_authenticator


class OAuthTokenCreate(BaseModel):
    access_token: str
    refresh_token: str
    expires_at: float


class AccountCreate(BaseModel):
    cookie_value: Optional[str] = None
    oauth_token: Optional[OAuthTokenCreate] = None
    organization_uuid: Optional[UUID] = None
    capabilities: Optional[List[str]] = None


class AccountUpdate(BaseModel):
    cookie_value: Optional[str] = None
    oauth_token: Optional[OAuthTokenCreate] = None
    capabilities: Optional[List[str]] = None
    status: Optional[AccountStatus] = None


class OAuthCodeExchange(BaseModel):
    organization_uuid: UUID
    code: str
    pkce_verifier: str
    capabilities: Optional[List[str]] = None


class AccountResponse(BaseModel):
    organization_uuid: str
    capabilities: Optional[List[str]]
    cookie_value: Optional[str] = Field(None, description="Masked cookie value")
    status: AccountStatus
    auth_type: AuthType
    is_pro: bool
    is_max: bool
    has_oauth: bool
    last_used: str
    resets_at: Optional[str] = None


router = APIRouter()


@router.get("", response_model=List[AccountResponse])
async def list_accounts(_: AdminAuthDep):
    """List all accounts."""
    accounts = []

    for org_uuid, account in account_manager._accounts.items():
        accounts.append(
            AccountResponse(
                organization_uuid=org_uuid,
                capabilities=account.capabilities,
                cookie_value=account.cookie_value[:20] + "..."
                if account.cookie_value
                else None,
                status=account.status,
                auth_type=account.auth_type,
                is_pro=account.is_pro,
                is_max=account.is_max,
                has_oauth=account.oauth_token is not None,
                last_used=account.last_used.isoformat(),
                resets_at=account.resets_at.isoformat() if account.resets_at else None,
            )
        )

    return accounts


@router.get("/{organization_uuid}", response_model=AccountResponse)
async def get_account(organization_uuid: str, _: AdminAuthDep):
    """Get a specific account by organization UUID."""
    if organization_uuid not in account_manager._accounts:
        raise HTTPException(status_code=404, detail="Account not found")

    account = account_manager._accounts[organization_uuid]

    return AccountResponse(
        organization_uuid=organization_uuid,
        capabilities=account.capabilities,
        cookie_value=account.cookie_value[:20] + "..."
        if account.cookie_value
        else None,
        status=account.status,
        auth_type=account.auth_type,
        is_pro=account.is_pro,
        is_max=account.is_max,
        has_oauth=account.oauth_token is not None,
        last_used=account.last_used.isoformat(),
        resets_at=account.resets_at.isoformat() if account.resets_at else None,
    )


@router.post("", response_model=AccountResponse)
async def create_account(account_data: AccountCreate, _: AdminAuthDep):
    """Create a new account."""
    oauth_token = None
    if account_data.oauth_token:
        oauth_token = OAuthToken(
            access_token=account_data.oauth_token.access_token,
            refresh_token=account_data.oauth_token.refresh_token,
            expires_at=account_data.oauth_token.expires_at,
        )

    account = await account_manager.add_account(
        cookie_value=account_data.cookie_value,
        oauth_token=oauth_token,
        organization_uuid=str(account_data.organization_uuid),
        capabilities=account_data.capabilities,
    )

    return AccountResponse(
        organization_uuid=account.organization_uuid,
        capabilities=account.capabilities,
        cookie_value=account.cookie_value[:20] + "..."
        if account.cookie_value
        else None,
        status=account.status,
        auth_type=account.auth_type,
        is_pro=account.is_pro,
        is_max=account.is_max,
        has_oauth=account.oauth_token is not None,
        last_used=account.last_used.isoformat(),
        resets_at=account.resets_at.isoformat() if account.resets_at else None,
    )


@router.put("/{organization_uuid}", response_model=AccountResponse)
async def update_account(
    organization_uuid: str, account_data: AccountUpdate, _: AdminAuthDep
):
    """Update an existing account."""
    if organization_uuid not in account_manager._accounts:
        raise HTTPException(status_code=404, detail="Account not found")

    account = account_manager._accounts[organization_uuid]

    # Update fields if provided
    if account_data.cookie_value is not None:
        # Remove old cookie mapping if exists
        if (
            account.cookie_value
            and account.cookie_value in account_manager._cookie_to_uuid
        ):
            del account_manager._cookie_to_uuid[account.cookie_value]

        account.cookie_value = account_data.cookie_value
        account_manager._cookie_to_uuid[account_data.cookie_value] = organization_uuid

    if account_data.oauth_token is not None:
        account.oauth_token = OAuthToken(
            access_token=account_data.oauth_token.access_token,
            refresh_token=account_data.oauth_token.refresh_token,
            expires_at=account_data.oauth_token.expires_at,
        )
        # Update auth type based on what's available
        if account.cookie_value and account.oauth_token:
            account.auth_type = AuthType.BOTH
        elif account.oauth_token:
            account.auth_type = AuthType.OAUTH_ONLY
        else:
            account.auth_type = AuthType.COOKIE_ONLY

    if account_data.capabilities is not None:
        account.capabilities = account_data.capabilities

    if account_data.status is not None:
        account.status = account_data.status
        if account.status == AccountStatus.VALID:
            account.resets_at = None

    # Save changes
    account_manager.save_accounts()

    return AccountResponse(
        organization_uuid=organization_uuid,
        capabilities=account.capabilities,
        cookie_value=account.cookie_value[:20] + "..."
        if account.cookie_value
        else None,
        status=account.status,
        auth_type=account.auth_type,
        is_pro=account.is_pro,
        is_max=account.is_max,
        has_oauth=account.oauth_token is not None,
        last_used=account.last_used.isoformat(),
        resets_at=account.resets_at.isoformat() if account.resets_at else None,
    )


@router.delete("/{organization_uuid}")
async def delete_account(organization_uuid: str, _: AdminAuthDep):
    """Delete an account."""
    if organization_uuid not in account_manager._accounts:
        raise HTTPException(status_code=404, detail="Account not found")

    await account_manager.remove_account(organization_uuid)

    return {"message": "Account deleted successfully"}


@router.post("/oauth/exchange", response_model=AccountResponse)
async def exchange_oauth_code(exchange_data: OAuthCodeExchange, _: AdminAuthDep):
    """Exchange OAuth authorization code for tokens and create account."""
    # Exchange code for tokens
    token_data = await oauth_authenticator.exchange_token(
        exchange_data.code, exchange_data.pkce_verifier
    )

    if not token_data:
        raise OAuthExchangeError()

    # Create OAuth token object
    oauth_token = OAuthToken(
        access_token=token_data["access_token"],
        refresh_token=token_data["refresh_token"],
        expires_at=time.time() + token_data["expires_in"],
    )

    # Create account with OAuth token
    account = await account_manager.add_account(
        oauth_token=oauth_token,
        organization_uuid=str(exchange_data.organization_uuid),
        capabilities=exchange_data.capabilities,
    )

    return AccountResponse(
        organization_uuid=account.organization_uuid,
        capabilities=account.capabilities,
        cookie_value=None,
        status=account.status,
        auth_type=account.auth_type,
        is_pro=account.is_pro,
        is_max=account.is_max,
        has_oauth=True,
        last_used=account.last_used.isoformat(),
        resets_at=account.resets_at.isoformat() if account.resets_at else None,
    )
