from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import account_by_email, create_auth_user, delete_auth_user
from ..db import get_db
from ..models import Account, InviteCode, Runner, RunnerMeasurement
from ..schemas import SignupRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/invite-codes/validate")
async def validate_invite_code(code: str, db: AsyncSession = Depends(get_db)):
    invite = await _usable_invite(db, code)
    return {"valid": invite is not None}


async def _usable_invite(db: AsyncSession, code: str) -> InviteCode | None:
    invite = (await db.execute(select(InviteCode).where(InviteCode.code == code.strip().upper()))).scalar_one_or_none()
    if invite is None or invite.used_at is not None or invite.revoked_at is not None:
        return None
    return invite


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, db: AsyncSession = Depends(get_db)):
    """Creates the auth user, the Account and its Runner in one go. The web then signs in through GoTrue."""
    if not (body.accept_terms and body.accept_privacy and body.accept_disclaimer and body.is_adult):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "all consents are required")
    invite = await _usable_invite(db, body.invite_code)
    if invite is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid or used invite code")
    if await account_by_email(db, body.email) is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "an account with this email already exists")

    user_id = await create_auth_user(body.email, body.password)
    now = datetime.now(UTC)
    try:
        account = Account(
            id=user_id, email=body.email, invite_code_id=invite.id,
            terms_accepted_at=now, privacy_accepted_at=now, disclaimer_accepted_at=now, adult_declared_at=now,
        )
        runner = Runner(account=account)
        runner.measurements.append(RunnerMeasurement())
        invite.used_by = user_id
        invite.used_at = now
        db.add_all([account, runner])
        await db.commit()
    except Exception:
        await delete_auth_user(user_id)
        raise
    return {"account_id": str(user_id)}
