"""Maintenance commands, run inside the api container:

    uv run python -m running_analyzer_api.cli invites 5      # print 5 new invite codes
    uv run python -m running_analyzer_api.cli admin a@b.c    # give an account the admin role
    uv run python -m running_analyzer_api.cli rerun <session id>  # analyze again as a new session
    uv run python -m running_analyzer_api.cli adopt <new session id> <existing session id> <speed km/h> "<label>" side [rear]
        # turn videos already uploaded to sessions/<new id>/<view>.mp4 into a queued session for the
        # same Runner (files larger than the browser upload limit, e.g. validation recordings)

`rerun` never touches the original: it copies the Session and its video files (server-side copy in
storage) into a new Session marked as a re-run, and queues a fresh Analysis for the copy, so the
Runner can keep looking at the old results and compare.
"""

import asyncio
import sys
import uuid
from datetime import UTC, datetime

import redis
from rq import Queue
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from . import storage, workload
from .db import SessionLocal
from .models import Account, Analysis, InviteCode, Session, Video
from .routers.admin import new_code
from .settings import settings


async def invites(n: int):
    async with SessionLocal() as db:
        codes = [InviteCode(code=new_code()) for _ in range(n)]
        db.add_all(codes)
        await db.commit()
        print("\n".join(c.code for c in codes))


async def admin(email: str):
    async with SessionLocal() as db:
        account = (await db.execute(select(Account).where(Account.email == email))).scalar_one()
        account.role = "admin"
        await db.commit()
        print(f"{email} is now admin")


async def rerun(session_id: str):
    async with SessionLocal() as db:
        src = (
            await db.execute(select(Session).where(Session.id == uuid.UUID(session_id)).options(selectinload(Session.videos)))
        ).scalar_one()
        videos = [v for v in src.videos if v.uploaded_at is not None and v.deleted_at is None]
        if not any(v.slot != "rear" for v in videos):
            sys.exit("the session has no side view video left to analyze")
        stamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
        copy = Session(
            id=uuid.uuid4(), runner_id=src.runner_id, recorded_on=src.recorded_on, speed_kmh=src.speed_kmh,
            incline_pct=src.incline_pct, height_cm_used=src.height_cm_used, weight_kg_used=src.weight_kg_used,
            improvement_consent=src.improvement_consent, processing_consent_at=src.processing_consent_at,
            # Sessions have no notes field; the shoes line is what the list and the header show.
            shoes=f"{src.shoes + ' · ' if src.shoes else ''}re-run {stamp} UTC", state="queued",
        )
        for v in videos:
            key = storage.video_key(copy.id, v.slot)
            storage.internal.copy_object(Bucket=settings.s3_bucket, Key=key, CopySource={"Bucket": settings.s3_bucket, "Key": v.storage_key})
            copy.videos.append(Video(
                slot=v.slot, view=v.view, storage_key=key, size_bytes=v.size_bytes, duration_s=v.duration_s, container_fps=v.container_fps,
                capture_fps=v.capture_fps, frames=v.frames, width=v.width, height=v.height, uploaded_at=v.uploaded_at,
            ))
        planned = sum(workload.planned_frames(workload.family(v.slot), v.frames or 0, workload.effective_fps(v.container_fps, v.capture_fps)) for v in copy.videos)
        copy.analysis = Analysis(pipeline_version=settings.pipeline_version, state="queued", frames_planned=planned)
        db.add(copy)
        await db.commit()
        Queue("analysis", connection=redis.from_url(settings.redis_url)).enqueue(
            "worker.jobs.analyze", str(copy.analysis.id), job_timeout=3 * 3600, job_id=str(copy.analysis.id)
        )
        print(f"new session {copy.id} queued (analysis {copy.analysis.id}); {src.id} is unchanged")


async def adopt(new_id: str, like_session: str, speed: float, label: str, views: list[str]):
    from datetime import date

    from . import probe

    async with SessionLocal() as db:
        ref = await db.get(Session, uuid.UUID(like_session))
        s = Session(
            id=uuid.UUID(new_id), runner_id=ref.runner_id, recorded_on=date.today(), speed_kmh=speed, incline_pct=0.0,
            height_cm_used=ref.height_cm_used, weight_kg_used=ref.weight_kg_used, shoes=label, state="queued",
            processing_consent_at=datetime.now(UTC),
        )
        for view in views:  # "side", "side_b" or "rear": the slot, and the object name in storage
            slot = {"side": "side_a"}.get(view, view)
            key = storage.video_key(s.id, view)
            head = storage.head(key)
            if head is None:
                sys.exit(f"{key} is not in storage")
            info = await probe.probe_url(storage.presign_download_internal(key))
            s.videos.append(Video(
                slot=slot, view="rear" if slot == "rear" else "side", storage_key=key, size_bytes=head["ContentLength"], duration_s=info.duration_s,
                container_fps=info.container_fps, capture_fps=info.capture_fps, frames=info.frames,
                width=info.width, height=info.height, uploaded_at=datetime.now(UTC),
            ))
        planned = sum(workload.planned_frames(workload.family(v.slot), v.frames or 0, workload.effective_fps(v.container_fps, v.capture_fps)) for v in s.videos)
        s.analysis = Analysis(pipeline_version=settings.pipeline_version, state="queued", frames_planned=planned)
        db.add(s)
        await db.commit()
        Queue("analysis", connection=redis.from_url(settings.redis_url)).enqueue(
            "worker.jobs.analyze", str(s.analysis.id), job_timeout=3 * 3600, job_id=str(s.analysis.id)
        )
        print(f"session {s.id} queued: {label}")


if __name__ == "__main__":
    cmd, *args = sys.argv[1:]
    if cmd == "invites":
        asyncio.run(invites(int(args[0]) if args else 5))
    elif cmd == "admin":
        asyncio.run(admin(args[0]))
    elif cmd == "rerun":
        asyncio.run(rerun(args[0]))
    elif cmd == "adopt":
        asyncio.run(adopt(args[0], args[1], float(args[2]), args[3], args[4:]))
    else:
        sys.exit(__doc__)
