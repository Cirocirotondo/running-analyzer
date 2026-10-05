import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from .. import mail, probe, storage, workload
from ..auth import current_account
from ..db import get_db
from ..metrics_config import METRICS, SOURCES
from ..models import Account, Analysis, Session, Video
from ..schemas import (
    AdviceOut,
    AnalysisOut,
    FailureReportAnswer,
    MetricOut,
    SessionCreate,
    SessionCreated,
    SessionOut,
    UploadTarget,
    VideoOut,
    VideoUploaded,
)
from ..settings import settings
from .me import runner_of

router = APIRouter(prefix="/sessions", tags=["sessions"])


async def seconds_per_frame(db: AsyncSession) -> float:
    """Measured processing rate: last finished analyses' duration over frames processed."""
    rows = (
        await db.execute(
            select(Analysis.started_at, Analysis.finished_at, Analysis.frames_processed)
            .where(Analysis.state == "done", Analysis.frames_processed > 0)
            .order_by(Analysis.finished_at.desc()).limit(10)
        )
    ).all()
    rates = [((f - st).total_seconds() - workload.FIXED_OVERHEAD_SECONDS) / n for st, f, n in rows if f and st and n]
    rates = [r for r in rates if r > 0]
    return sum(rates) / len(rates) if rates else workload.DEFAULT_SECONDS_PER_FRAME


async def queue_info(request: Request, db: AsyncSession, a: Analysis | None) -> dict:
    """Position in the queue and ETA for a queued or running Analysis, from frame counts and the measured rate."""
    if a is None or a.state not in ("queued", "running"):
        return {}
    spf = await seconds_per_frame(db)
    if a.state == "running":
        if a.eta_seconds is not None:
            return {"progress_pct": a.progress_pct, "eta_seconds": a.eta_seconds}
        # The worker reports its own estimate once pose estimation runs; before that (downloading and
        # checking a large file) estimate from the planned work, as for a queued Analysis.
        elapsed = (datetime.now(UTC) - a.started_at).total_seconds() if a.started_at else 0
        return {"progress_pct": a.progress_pct, "eta_seconds": int(max(30.0, workload.estimate_seconds(a.frames_planned or 0, spf) - elapsed))}
    job_ids = [jid.split("-retry")[0] for jid in request.app.state.queue.job_ids]
    position = next((i for i, jid in enumerate(job_ids) if jid == str(a.id)), len(job_ids))
    ahead_ids = [uuid.UUID(j) for j in job_ids[:position]]
    ahead = (await db.execute(select(Analysis.frames_planned).where(Analysis.id.in_(ahead_ids)))).scalars().all() if ahead_ids else []
    running = (await db.execute(select(Analysis).where(Analysis.state == "running").limit(1))).scalar_one_or_none()
    if running is None:
        left_running = 0.0
    elif running.eta_seconds is not None:
        left_running = running.eta_seconds
    else:  # no estimate from the worker yet (still downloading or checking): planned work minus elapsed time
        elapsed = (datetime.now(UTC) - running.started_at).total_seconds() if running.started_at else 0
        left_running = max(60.0, workload.estimate_seconds(running.frames_planned or 0, spf) - elapsed)
    eta = left_running + sum(workload.estimate_seconds(n or 0, spf) for n in ahead) + workload.estimate_seconds(a.frames_planned or 0, spf)
    return {"progress_pct": 0.0, "queue_position": position, "eta_seconds": int(eta)}


def session_out(s: Session, queue: dict | None = None) -> SessionOut:
    a = s.analysis
    return SessionOut(
        **(queue or {}),
        id=s.id, recorded_on=s.recorded_on, speed_kmh=s.speed_kmh, incline_pct=s.incline_pct, shoes=s.shoes,
        state=s.state, created_at=s.created_at,
        videos=[
            VideoOut(slot=v.slot, view=v.view, uploaded=v.uploaded_at is not None, deleted=v.deleted_at is not None, duration_s=v.duration_s,
                     container_fps=v.container_fps, capture_fps=v.capture_fps, check_result=v.check_result)
            for v in sorted(s.videos, key=lambda v: v.slot)
        ],
        analysis_state=a.state if a else None, analysis_progress=a.progress if a else None,
        failure_reason=a.failure_reason if a else None, failure_report=a.failure_report if a else None,
    )


async def owned_session(db: AsyncSession, account: Account, session_id: uuid.UUID) -> Session:
    runner = await runner_of(db, account)
    s = (
        await db.execute(
            select(Session).where(Session.id == session_id, Session.runner_id == runner.id)
            .options(selectinload(Session.videos), selectinload(Session.analysis))
        )
    ).scalar_one_or_none()
    if s is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "session not found")
    return s


@router.get("", response_model=list[SessionOut])
async def list_sessions(request: Request, account: Account = Depends(current_account), db: AsyncSession = Depends(get_db)):
    runner = await runner_of(db, account)
    rows = await db.execute(
        select(Session).where(Session.runner_id == runner.id).order_by(Session.recorded_on.desc(), Session.created_at.desc())
        .options(selectinload(Session.videos), selectinload(Session.analysis))
    )
    return [session_out(s, await queue_info(request, db, s.analysis)) for s in rows.scalars()]


@router.post("", response_model=SessionCreated, status_code=status.HTTP_201_CREATED)
async def create_session(body: SessionCreate, account: Account = Depends(current_account), db: AsyncSession = Depends(get_db)):
    runner = await runner_of(db, account)
    if runner.height_cm is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "set your height in the profile first")
    if not body.processing_consent:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "consent to video processing is required")
    s = Session(
        id=uuid.uuid4(),  # needed now: the storage keys embed it before the row is inserted
        runner_id=runner.id, recorded_on=body.recorded_on, speed_kmh=body.speed_kmh, incline_pct=body.incline_pct,
        shoes=body.shoes, height_cm_used=runner.height_cm, weight_kg_used=runner.weight_kg,
        improvement_consent=body.improvement_consent, processing_consent_at=datetime.now(UTC), state="draft",
    )
    slots = ["side_a", "side_b"][: body.side_videos] + (["rear"] if body.rear_view else [])
    s.videos = [Video(slot=slot, view="rear" if slot == "rear" else "side", storage_key=storage.video_key(s.id, slot)) for slot in slots]
    s.analysis = None
    db.add(s)
    await db.commit()
    s = await owned_session(db, account, s.id)
    uploads = [UploadTarget(slot=v.slot, url=storage.presign_upload(v.storage_key), max_bytes=settings.max_video_bytes) for v in s.videos]
    return SessionCreated(session=session_out(s), uploads=uploads)


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(session_id: uuid.UUID, request: Request, account: Account = Depends(current_account), db: AsyncSession = Depends(get_db)):
    s = await owned_session(db, account, session_id)
    return session_out(s, await queue_info(request, db, s.analysis))


CHECK_GRACE_SECONDS = 120  # a Recording Check still pending after this does not block the submit


def draft_video(s: Session, slot: str) -> Video:
    if s.state != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, "session already submitted")
    video = next((v for v in s.videos if v.slot == slot), None)
    if video is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such video slot in this session")
    return video


def reset_video(video: Video) -> None:
    video.uploaded_at = video.size_bytes = video.duration_s = video.frames = None
    video.check_result = None
    video.view = "rear" if video.slot == "rear" else "side"


@router.post("/{session_id}/videos/{slot}/upload-url", response_model=UploadTarget)
async def new_upload_url(session_id: uuid.UUID, slot: str, account: Account = Depends(current_account), db: AsyncSession = Depends(get_db)):
    """A fresh upload URL for a slot, to replace its Video (e.g. after a Recording Check warning)."""
    s = await owned_session(db, account, session_id)
    video = draft_video(s, slot)
    reset_video(video)
    await db.commit()
    return UploadTarget(slot=slot, url=storage.presign_upload(video.storage_key), max_bytes=settings.max_video_bytes)


@router.delete("/{session_id}/videos/{slot}", response_model=SessionOut)
async def remove_video(session_id: uuid.UUID, slot: str, account: Account = Depends(current_account), db: AsyncSession = Depends(get_db)):
    """Removes an uploaded Video from a draft Session (the slot stays, empty)."""
    s = await owned_session(db, account, session_id)
    video = draft_video(s, slot)
    if video.uploaded_at is not None:
        storage.delete(video.storage_key)
    reset_video(video)
    await db.commit()
    return session_out(await owned_session(db, account, session_id))


@router.post("/{session_id}/videos/{slot}/uploaded", response_model=SessionOut)
async def video_uploaded(session_id: uuid.UUID, slot: str, body: VideoUploaded, request: Request, account: Account = Depends(current_account), db: AsyncSession = Depends(get_db)):
    """The browser calls this after the PUT to storage succeeded; the API verifies the object exists."""
    s = await owned_session(db, account, session_id)
    if s.state != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, "session already submitted")
    video = next((v for v in s.videos if v.slot == slot), None)
    if video is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no such video slot in this session")
    obj = storage.head(video.storage_key)
    if obj is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "video not found in storage")
    if obj["ContentLength"] > settings.max_video_bytes:  # the browser checks too, but the signed URL does not
        storage.delete(video.storage_key)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "too_large")
    video.size_bytes = obj["ContentLength"]
    # Read the real frame rate and length now: the browser only knows the playback duration, and a
    # 25 fps clip should be refused here rather than after waiting in the queue.
    info = await probe.probe_url(storage.presign_download_internal(video.storage_key))
    if info is None:
        video.check_result = {"passed": False, "reason": "unreadable"}
        await db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "the file could not be read as a video")
    video.container_fps, video.capture_fps = info.container_fps, info.capture_fps
    video.duration_s, video.width, video.height = round(info.duration_s, 2), info.width, info.height
    video.frames = info.frames
    reason = "fps_too_low" if info.fps < workload.MIN_FPS else "too_short" if info.duration_s < workload.MIN_SECONDS[workload.family(slot)] else None
    file_facts = {"fps": info.fps, "frames": info.frames, "duration_s": round(info.duration_s, 2)}
    if reason:
        video.check_result = {"outcome": "rejected", "reason": reason, "warnings": [], "file": file_facts}
        await db.commit()
        raise HTTPException(status.HTTP_400_BAD_REQUEST, reason)
    video.uploaded_at = datetime.now(UTC)
    # The Recording Check looks at the frames in a few seconds; the wizard polls the Session for it.
    video.check_result = {"outcome": "pending", "warnings": [], "file": file_facts, "queued_at": video.uploaded_at.isoformat()}
    await db.commit()
    request.app.state.checks.enqueue("worker.checks.check_video", str(video.id), job_timeout=300)
    return session_out(await owned_session(db, account, session_id))


@router.post("/{session_id}/submit", response_model=SessionOut)
async def submit(session_id: uuid.UUID, request: Request, account: Account = Depends(current_account), db: AsyncSession = Depends(get_db)):
    s = await owned_session(db, account, session_id)
    if s.state != "draft":
        raise HTTPException(status.HTTP_409_CONFLICT, "session already submitted")
    # Videos planned but never uploaded are simply dropped; at least one side Video must remain.
    for v in list(s.videos):
        if v.uploaded_at is None:
            s.videos.remove(v)
    sides = [v for v in s.videos if v.slot != "rear"]
    if not sides:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "no_side_video")
    now = datetime.now(UTC)
    for v in s.videos:
        check = v.check_result or {}
        if check.get("outcome") == "rejected":
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "video_rejected")
        queued = check.get("queued_at")
        if check.get("outcome") == "pending" and queued and (now - datetime.fromisoformat(queued)).total_seconds() < CHECK_GRACE_SECONDS:
            raise HTTPException(status.HTTP_409_CONFLICT, "checks_pending")
    known = [v.view for v in sides if v.view in ("left_side", "right_side")]
    if len(known) != len(set(known)):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "same_side")
    planned = sum(workload.planned_frames(workload.family(v.slot), v.frames or 0, workload.effective_fps(v.container_fps, v.capture_fps)) for v in s.videos)
    analysis = Analysis(session_id=s.id, pipeline_version=settings.pipeline_version, state="queued", frames_planned=planned)
    s.analysis = analysis
    s.state = "queued"
    await db.commit()
    request.app.state.queue.enqueue("worker.jobs.analyze", str(analysis.id), job_timeout=3 * 3600, job_id=str(analysis.id))
    return session_out(await owned_session(db, account, session_id))


def delete_video_files(s: Session) -> None:
    now = datetime.now(UTC)
    for v in s.videos:
        if v.deleted_at is None and v.uploaded_at is not None:
            storage.delete(v.storage_key)
            v.deleted_at = now


async def notify_admins(db: AsyncSession, s: Session) -> None:
    for email in (await db.execute(select(Account.email).where(Account.role == "admin"))).scalars():
        mail.failure_report_opened(email, str(s.id), s.analysis.failure_reason)


@router.post("/{session_id}/failure-report", response_model=SessionOut)
async def answer_failure_report(session_id: uuid.UUID, body: FailureReportAnswer, account: Account = Depends(current_account), db: AsyncSession = Depends(get_db)):
    """The Runner's answer to "send your videos to our team?" after a failed Analysis. Yes grants
    Improvement Consent for this Session and opens a Failure Report; no deletes the Videos."""
    s = await owned_session(db, account, session_id)
    a = s.analysis
    if a is None or a.failure_report != "asked":
        raise HTTPException(status.HTTP_409_CONFLICT, "nothing to answer")
    a.failure_report_at = datetime.now(UTC)
    if body.send:
        s.improvement_consent, a.failure_report = True, "open"
    else:
        delete_video_files(s)
        a.failure_report = "closed"
    await db.commit()
    if body.send:
        await notify_admins(db, s)
    return session_out(await owned_session(db, account, session_id))


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(session_id: uuid.UUID, account: Account = Depends(current_account), db: AsyncSession = Depends(get_db)):
    s = await owned_session(db, account, session_id)
    for v in s.videos:
        storage.delete(v.storage_key)
    if s.analysis and s.analysis.keypoints_keys:
        for key in s.analysis.keypoints_keys.values():
            storage.delete(key)
            storage.delete(key.replace(".parquet", ".json"))
    await db.delete(s)
    await db.commit()


@router.delete("/{session_id}/videos", response_model=SessionOut)
async def delete_videos(session_id: uuid.UUID, account: Account = Depends(current_account), db: AsyncSession = Depends(get_db)):
    """Removes the video files (the Playback Videos, ADR 0008) but keeps the Analysis."""
    s = await owned_session(db, account, session_id)
    delete_video_files(s)
    s.state = "videos_deleted"
    await db.commit()
    return session_out(await owned_session(db, account, session_id))


@router.get("/{session_id}/analysis", response_model=AnalysisOut)
async def get_analysis(session_id: uuid.UUID, account: Account = Depends(current_account), db: AsyncSession = Depends(get_db)):
    s = await owned_session(db, account, session_id)
    a = s.analysis
    if a is None or a.state != "done":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "no finished analysis for this session")
    a = (await db.execute(select(Analysis).where(Analysis.id == a.id).options(selectinload(Analysis.metrics), selectinload(Analysis.advice)))).scalar_one()
    metrics = []
    for m in a.metrics:
        d = METRICS.get(m.metric_key)
        metrics.append(MetricOut(
            metric_key=m.metric_key, view=m.view, side=m.side, label=d.label if d else m.metric_key, unit=d.unit if d else None,
            mean=m.mean, sd=m.sd, n_cycles=m.n_cycles, mean_score=m.mean_score, state=m.state, reason=m.reason, value_text=m.value_text,
            typical_low=m.typical_low, typical_high=m.typical_high, source_id=m.source_id, advice_eligible=bool(d and d.advice_eligible),
            per_view=m.per_view, unreliable_reason=m.unreliable_reason,
        ))
    return AnalysisOut(
        session=session_out(s), pipeline_version=a.pipeline_version, finished_at=a.finished_at, window=a.window, camera_check=a.camera_check,
        video_urls={v.view if v.view != "side" else v.slot: storage.presign_download(v.storage_key) for v in s.videos if v.deleted_at is None},
        # The player reads the JSON twin of the parquet file; each key needs its own signature.
        keypoints_urls={view: storage.presign_download(key.replace(".parquet", ".json")) for view, key in (a.keypoints_keys or {}).items()},
        metrics=metrics, advice=[AdviceOut(metric_key=x.metric_key, body=x.body or "") for x in a.advice],
        info={"sources": SOURCES},
    )
