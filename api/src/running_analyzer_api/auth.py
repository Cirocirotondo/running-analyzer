"""JWT verification against the self-hosted Supabase Auth (GoTrue) and user creation through its admin API."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime, timedelta

import httpx
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_db
from .models import Account
from .settings import settings

bearer = HTTPBearer(auto_error=False)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=["HS256"], audience="authenticated")
    except jwt.PyJWTError as e:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"invalid token: {e}") from e


async def current_account(
    request: Request,
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> Account:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    claims = decode_token(creds.credentials)
    account = await db.get(Account, uuid.UUID(claims["sub"]))
    if account is None:
        # A GoTrue user without an Account: signed up outside /auth/signup (never in production).
        raise HTTPException(status.HTTP_403_FORBIDDEN, "no account for this user")
    if account.deletion_requested_at is not None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "account is being deleted")
    # Active Account = used while signed in in the last 30 days; one write per hour is enough.
    now = datetime.now(UTC)
    if account.last_active_at is None or now - account.last_active_at > timedelta(hours=1):
        account.last_active_at = now
        await db.commit()
    return account


async def current_admin(account: Account = Depends(current_account)) -> Account:
    if account.role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "admin only")
    return account


def service_token() -> str:
    """A short-lived service_role JWT, accepted by GoTrue's admin endpoints."""
    now = int(time.time())
    return jwt.encode({"role": "service_role", "iat": now, "exp": now + 60}, settings.jwt_secret, algorithm="HS256")


async def create_auth_user(email: str, password: str) -> uuid.UUID:
    """Creates the user in GoTrue (email confirmed, since the invite code vouches for it)."""
    async with httpx.AsyncClient(base_url=settings.auth_internal_url, timeout=10) as client:
        r = await client.post(
            "/admin/users",
            headers={"Authorization": f"Bearer {service_token()}"},
            json={"email": email, "password": password, "email_confirm": True},
        )
    if r.status_code == 422 or r.status_code == 400:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, r.json().get("msg") or r.json().get("message") or "cannot create user")
    r.raise_for_status()
    return uuid.UUID(r.json()["id"])


async def delete_auth_user(user_id: uuid.UUID) -> None:
    async with httpx.AsyncClient(base_url=settings.auth_internal_url, timeout=10) as client:
        r = await client.delete(f"/admin/users/{user_id}", headers={"Authorization": f"Bearer {service_token()}"})
    if r.status_code not in (200, 204, 404):
        r.raise_for_status()


async def account_by_email(db: AsyncSession, email: str) -> Account | None:
    return (await db.execute(select(Account).where(Account.email == email))).scalar_one_or_none()
