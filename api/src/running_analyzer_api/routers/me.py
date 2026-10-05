from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import mail, storage
from ..auth import current_account, delete_auth_user
from ..db import get_db
from ..models import Account, Runner, RunnerMeasurement, Session
from ..schemas import AccountDeletion, AccountSettings, MeOut, RunnerOut, RunnerUpdate

router = APIRouter(prefix="/me", tags=["me"])


async def runner_of(db: AsyncSession, account: Account) -> Runner:
    # v1: exactly one Runner per Account.
    return (await db.execute(select(Runner).where(Runner.account_id == account.id))).scalar_one()


def runner_out(r: Runner) -> RunnerOut:
    return RunnerOut(
        id=r.id, display_name=r.display_name, height_cm=r.height_cm, weight_kg=r.weight_kg, sex=r.sex,
        birth_year=r.birth_year, profile_complete=r.height_cm is not None,
    )


@router.get("", response_model=MeOut)
async def me(account: Account = Depends(current_account), db: AsyncSession = Depends(get_db)):
    runner = await runner_of(db, account)
    return MeOut(account_id=account.id, email=account.email, role=account.role, runner=runner_out(runner), notify_analysis_ready=account.notify_analysis_ready)


@router.put("/settings", response_model=MeOut)
async def update_settings(body: AccountSettings, account: Account = Depends(current_account), db: AsyncSession = Depends(get_db)):
    account.notify_analysis_ready = body.notify_analysis_ready
    await db.commit()
    return await me(account, db)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(body: AccountDeletion, account: Account = Depends(current_account), db: AsyncSession = Depends(get_db)):
    """Deletes the Account at once (docs/SPEC.md §4.6): files in storage, the login, then the rows (the
    Runner, Sessions, Videos, Analyses follow by cascade). Confirmed by re-typing the email."""
    if body.email.strip().lower() != account.email.lower():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "email_mismatch")
    email = account.email
    runner = await runner_of(db, account)
    sessions = (await db.execute(select(Session).where(Session.runner_id == runner.id).options(selectinload(Session.videos), selectinload(Session.analysis)))).scalars().all()
    for s in sessions:
        for v in s.videos:
            storage.delete(v.storage_key)
        for key in ((s.analysis.keypoints_keys or {}).values() if s.analysis else []):
            storage.delete(key)
            storage.delete(key.replace(".parquet", ".json"))
    await delete_auth_user(account.id)
    await db.delete(account)
    await db.commit()
    mail.account_deleted(email)


@router.put("/runner", response_model=RunnerOut)
async def update_runner(body: RunnerUpdate, account: Account = Depends(current_account), db: AsyncSession = Depends(get_db)):
    runner = await runner_of(db, account)
    changes = body.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(runner, k, v)
    if "height_cm" in changes or "weight_kg" in changes:
        db.add(RunnerMeasurement(runner_id=runner.id, height_cm=runner.height_cm, weight_kg=runner.weight_kg))
    await db.commit()
    await db.refresh(runner)
    return runner_out(runner)
