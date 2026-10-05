import secrets
import uuid
from collections import Counter
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import storage
from ..auth import current_admin
from ..db import get_db
from ..models import Account, Analysis, InviteCode, Runner, Session, Video

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(current_admin)])


def new_code() -> str:
    # 10 characters, no ambiguous letters, easy to read out loud.
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(secrets.choice(alphabet) for _ in range(10))


@router.post("/invite-codes")
async def create_invite_codes(count: int = 5, admin: Account = Depends(current_admin), db: AsyncSession = Depends(get_db)):
    codes = [InviteCode(code=new_code(), created_by=admin.id) for _ in range(max(1, min(count, 100)))]
    db.add_all(codes)
    await db.commit()
    return [c.code for c in codes]


@router.get("/invite-codes")
async def list_invite_codes(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(InviteCode).order_by(InviteCode.created_at.desc()))).scalars().all()
    emails = dict((await db.execute(select(Account.id, Account.email).where(Account.id.in_([c.used_by for c in rows if c.used_by])))).all())
    return [
        {"code": c.code, "created_at": c.created_at, "used_by": emails.get(c.used_by), "used_at": c.used_at, "revoked_at": c.revoked_at}
        for c in rows
    ]


@router.post("/invite-codes/{code}/revoke")
async def revoke_invite_code(code: str, db: AsyncSession = Depends(get_db)):
    c = (await db.execute(select(InviteCode).where(InviteCode.code == code))).scalar_one()
    c.revoked_at = datetime.now(UTC)
    await db.commit()
    return {"revoked": code}


@router.get("/accounts")
async def accounts(db: AsyncSession = Depends(get_db)):
    """Sign-up date, Sessions and last activity; no personal data beyond the email (SPEC §4.8)."""
    counts = dict((await db.execute(select(Runner.account_id, func.count(Session.id)).join(Session, Session.runner_id == Runner.id, isouter=True).group_by(Runner.account_id))).all())
    rows = (await db.execute(select(Account).order_by(Account.created_at.desc()))).scalars()
    return [
        {"email": a.email, "role": a.role, "created_at": a.created_at, "last_active_at": a.last_active_at, "sessions": counts.get(a.id, 0)}
        for a in rows
    ]


@router.get("/failed-sessions")
async def failed_sessions(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Session, Analysis, Account.email).join(Analysis, Analysis.session_id == Session.id).join(Runner, Runner.id == Session.runner_id)
            .join(Account, Account.id == Runner.account_id).where(Analysis.state == "failed").order_by(Analysis.finished_at.desc()).limit(200)
        )
    ).all()
    return [
        {"session_id": s.id, "email": email, "recorded_on": s.recorded_on, "finished_at": a.finished_at, "reason": a.failure_reason,
         "log": a.progress if a.failure_reason == "internal_error" else None, "improvement_consent": s.improvement_consent, "pipeline_version": a.pipeline_version,
         "failure_report": a.failure_report, "failure_report_at": a.failure_report_at}
        for s, a, email in rows
    ]


@router.get("/failure-reports/count")
async def open_failure_reports(db: AsyncSession = Depends(get_db)):
    """Open Failure Reports, for the count next to the Admin link."""
    return {"open": (await db.execute(select(func.count()).select_from(Analysis).where(Analysis.failure_report == "open"))).scalar()}


async def open_report(db: AsyncSession, session_id: uuid.UUID) -> Session:
    s = (await db.execute(select(Session).where(Session.id == session_id).options(selectinload(Session.videos), selectinload(Session.analysis)))).scalar_one_or_none()
    if s is None or s.analysis is None or s.analysis.failure_report != "open":
        raise HTTPException(status.HTTP_409_CONFLICT, "no open Failure Report for this session")
    return s


@router.post("/sessions/{session_id}/reanalyze")
async def reanalyze(session_id: uuid.UUID, request: Request, db: AsyncSession = Depends(get_db)):
    """Runs the Analysis of an open Failure Report again, in the same Session: a failed Session has no
    results to lose. Success closes the report and emails the Runner; another failure leaves it open."""
    s = await open_report(db, session_id)
    a = s.analysis
    if not any(v.deleted_at is None and v.uploaded_at is not None and v.slot != "rear" for v in s.videos):
        raise HTTPException(status.HTTP_409_CONFLICT, "no side video left to analyze")
    a.state, a.progress, a.progress_pct, a.eta_seconds = "queued", None, None, None
    s.state = "queued"
    await db.commit()
    # A distinct job id: the failed job may still be in RQ's registries (queue_info strips the suffix).
    request.app.state.queue.enqueue("worker.jobs.analyze", str(a.id), job_timeout=3 * 3600, job_id=f"{a.id}-retry{int(datetime.now(UTC).timestamp())}")
    return {"queued": str(a.id)}


@router.post("/sessions/{session_id}/resolve")
async def resolve(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Closes an open Failure Report without re-analyzing and deletes its Videos."""
    s = await open_report(db, session_id)
    now = datetime.now(UTC)
    for v in s.videos:
        if v.deleted_at is None and v.uploaded_at is not None:
            storage.delete(v.storage_key)
            v.deleted_at = now
    s.analysis.failure_report, s.analysis.failure_report_at = "closed", now
    await db.commit()
    return {"resolved": str(s.id)}


@router.get("/sessions/{session_id}/videos")
async def session_videos(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Video links for a Session, only with Improvement Consent (ADR 0006)."""
    s = (await db.execute(select(Session).where(Session.id == session_id).options(selectinload(Session.videos)))).scalar_one_or_none()
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")
    if not s.improvement_consent:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "no improvement consent for this session")
    return {v.view: storage.presign_download(v.storage_key, expires=900) for v in s.videos if v.deleted_at is None}


@router.get("/stats")
async def stats(db: AsyncSession = Depends(get_db)):
    now = datetime.now(UTC)
    accounts_all = (await db.execute(select(Account.created_at, Account.last_active_at))).all()
    active_since = now - timedelta(days=30)
    sessions = (await db.execute(select(func.count()).select_from(Session))).scalar()
    failed = (await db.execute(select(func.count()).select_from(Analysis).where(Analysis.state == "failed"))).scalar()
    per_day = (
        await db.execute(
            select(func.date(Session.created_at), func.count()).where(Session.created_at >= now - timedelta(days=30))
            .group_by(func.date(Session.created_at)).order_by(func.date(Session.created_at))
        )
    ).all()
    durations = (await db.execute(select(Analysis.started_at, Analysis.finished_at).where(Analysis.state == "done", Analysis.started_at.isnot(None)).order_by(Analysis.finished_at.desc()).limit(50))).all()
    secs = [(f - st).total_seconds() for st, f in durations if f and st]
    storage_bytes = (await db.execute(select(func.coalesce(func.sum(Video.size_bytes), 0)).where(Video.deleted_at.is_(None), Video.uploaded_at.isnot(None)))).scalar()
    # Monthly sign-up cohorts and the share of each still active (signed in within 30 days).
    cohorts: dict[str, list[int]] = {}
    for created, last in accounts_all:
        c = cohorts.setdefault(created.strftime("%Y-%m"), [0, 0])
        c[0] += 1
        c[1] += int(bool(last and last >= active_since))
    # Recording Check outcomes over the last 90 days: which instructions are not being followed.
    checks = (await db.execute(select(Video.check_result).where(Video.uploaded_at >= now - timedelta(days=90), Video.check_result.isnot(None)))).scalars().all()
    outcomes = Counter((c or {}).get("outcome", "unchecked") for c in checks)
    reasons = Counter((c or {}).get("reason") for c in checks if (c or {}).get("outcome") == "rejected")
    warnings = Counter(w for c in checks for w in ((c or {}).get("warnings") or []))
    return {
        "accounts": len(accounts_all),
        "active_accounts_30d": sum(1 for _, last in accounts_all if last and last >= active_since),
        "sessions": sessions,
        "failed_analyses": failed,
        "sessions_per_day": [
            {"day": str(day), "sessions": dict((str(d), n) for d, n in per_day).get(str(day), 0)}
            for day in ((now - timedelta(days=29 - i)).date() for i in range(30))
        ],
        "mean_processing_seconds": round(sum(secs) / len(secs)) if secs else None,
        "storage_bytes": int(storage_bytes or 0),
        "cohorts": [{"month": m, "signups": n, "active_30d": a} for m, (n, a) in sorted(cohorts.items())],
        "recording_checks": {"videos": len(checks), "outcomes": dict(outcomes), "rejections": dict(reasons), "warnings": dict(warnings)},
    }
