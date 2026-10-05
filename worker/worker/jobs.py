"""RQ job: run the pipeline for one Analysis.

download videos -> check -> steady window -> pose -> metrics -> upload keypoints -> write
MetricValues and Advice -> mark done (or failed with a reason the Runner can act on).
"""

from __future__ import annotations

import json
import os
import tempfile
import traceback
import uuid
from datetime import UTC, datetime
from pathlib import Path

import boto3
import numpy as np
from botocore.client import Config
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session as DbSession, selectinload, sessionmaker

from running_analyzer_api import mail
from running_analyzer_api.metrics_config import ADVICE_TEXT, METRICS, UNRELIABLE_WHEN, WHOLE_BODY, foot_strike
from running_analyzer_api.models import Advice, Analysis, MetricValue, Runner, Session, Video

from . import pipeline

DATABASE_URL = os.environ["DATABASE_URL"]
S3 = dict(
    endpoint_url=os.environ["S3_ENDPOINT"], aws_access_key_id=os.environ["S3_ACCESS_KEY"],
    aws_secret_access_key=os.environ["S3_SECRET_KEY"], region_name="us-east-1",
    config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
)
BUCKET = os.environ["S3_BUCKET"]
MIN_CYCLES = 6
MIN_SCORE = 0.5
# Failures that are a fact of the file, not possibly our mistake: no Failure Report is offered
# (docs/SPEC.md §11, Playback Video and retention).
FILE_FAILURES = {"fps_too_low", "too_short"}

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
Db = sessionmaker(engine)


class VideoRejected(Exception):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def analyze(analysis_id: str) -> None:
    s3 = boto3.client("s3", **S3)
    with Db() as db:
        analysis = db.get(Analysis, uuid.UUID(analysis_id))
        if analysis is None:
            return
        session = db.execute(
            select(Session).where(Session.id == analysis.session_id).options(selectinload(Session.videos), selectinload(Session.runner))
        ).scalar_one()
        analysis.state, analysis.started_at = "running", datetime.now(UTC)
        session.state = "processing"
        # A re-run replaces the previous results.
        for row in list(analysis.metrics) + list(analysis.advice):
            db.delete(row)
        analysis.failure_reason = None
        analysis.progress_pct, analysis.eta_seconds = 0.0, None  # a re-analysis must not show the last run's estimate
        db.commit()

        def progress(msg: str, pct: float | None = None, eta_seconds: float | None = None):
            analysis.progress = msg
            if pct is not None:
                analysis.progress_pct = round(min(100.0, max(0.0, pct)), 1)
            if eta_seconds is not None:
                analysis.eta_seconds = int(max(0, eta_seconds))
            db.commit()

        result: dict = {"views": {}}
        try:
            with tempfile.TemporaryDirectory() as tmp:
                _run(db, s3, analysis, session, Path(tmp), progress, result)
            _store_results(db, analysis, session, result)
            analysis.state, analysis.finished_at, analysis.progress = "done", datetime.now(UTC), None
            analysis.progress_pct, analysis.eta_seconds = 100.0, 0
            analysis.frames_processed = sum(r.get("frames_processed", 0) for r in result["views"].values())
            session.state = "done"
            if analysis.failure_report == "open":  # an Admin re-analyzed a Failure Report and it worked
                analysis.failure_report, analysis.failure_report_at = "closed", datetime.now(UTC)
            _keep_playback_only(db, s3, session, result)
        except VideoRejected as e:
            analysis.state, analysis.failure_reason, analysis.finished_at = "failed", e.reason, datetime.now(UTC)
            session.state = "failed"
        except Exception:
            analysis.state, analysis.failure_reason, analysis.finished_at = "failed", "internal_error", datetime.now(UTC)
            analysis.progress = traceback.format_exc()[-1500:]
            session.state = "failed"
        db.commit()
        if analysis.state == "failed":
            _after_failure(db, s3, session, analysis, result)
        _notify(session, analysis)


def _delete_files(db: DbSession, s3, session: Session) -> None:
    now = datetime.now(UTC)
    for v in session.videos:
        if v.deleted_at is None and v.uploaded_at is not None:
            s3.delete_object(Bucket=BUCKET, Key=v.storage_key)
            v.deleted_at = now
    db.commit()


def _keep_playback_only(db: DbSession, s3, session: Session, result: dict) -> None:
    """After a successful Analysis each analyzed Video becomes its Playback Video and the uploaded file
    is deleted (ADR 0008). A Video skipped by the Analysis (e.g. a rear clip that was too short) has
    nothing to show and is deleted too."""
    now = datetime.now(UTC)
    by_slot = {r["slot"]: r for r in result["views"].values() if "slot" in r}
    for v in session.videos:
        if v.deleted_at is not None or v.uploaded_at is None:
            continue
        old_key = v.storage_key
        r = by_slot.get(v.slot)
        if r and r.get("playback_key"):
            v.storage_key, v.size_bytes, v.playback = r["playback_key"], r["playback_bytes"], True
        else:
            v.deleted_at = now
        db.commit()
        if old_key != v.storage_key or v.deleted_at is not None:
            s3.delete_object(Bucket=BUCKET, Key=old_key)


def _after_failure(db: DbSession, s3, session: Session, analysis: Analysis, result: dict) -> None:
    """A failed Analysis keeps its uploaded Videos only for a Failure Report (docs/SPEC.md §11): failures
    of the file itself delete them; for the others the Runner is asked, unless they already gave
    Improvement Consent, in which case the report opens at once. A re-analysis of an open report that
    fails again leaves it open."""
    for r in result["views"].values():  # Playback Videos written before the failure
        if r.get("playback_key"):
            s3.delete_object(Bucket=BUCKET, Key=r["playback_key"])
    if analysis.failure_reason in FILE_FAILURES:
        analysis.failure_report = None
        _delete_files(db, s3, session)
        return
    if analysis.failure_report == "open":
        db.commit()
        return
    analysis.failure_report = "open" if session.improvement_consent else "asked"
    analysis.failure_report_at = datetime.now(UTC)
    db.commit()
    if analysis.failure_report == "open":
        notify_admins(db, session, analysis)


def notify_admins(db: DbSession, session: Session, analysis: Analysis) -> None:
    from running_analyzer_api.models import Account

    for (email,) in db.execute(select(Account.email).where(Account.role == "admin")).all():
        mail.failure_report_opened(email, str(session.id), analysis.failure_reason)


def _notify(session: Session, analysis: Analysis) -> None:
    """Analysis ready (if the Runner wants it) or failed (always). Never raises: see mail.send."""
    account = session.runner.account
    date = session.recorded_on.isoformat()
    if analysis.state == "done" and account.notify_analysis_ready:
        mail.analysis_ready(account.email, str(session.id), date, session.speed_kmh)
    elif analysis.state == "failed":
        mail.analysis_failed(account.email, str(session.id), date, analysis.failure_reason, ask_to_send=analysis.failure_report == "asked")


def _run(db: DbSession, s3, analysis: Analysis, session: Session, tmp: Path, progress, out: dict) -> None:
    """Fills `out` as it goes, so the files written before a failure can be cleaned up."""
    videos = [v for v in sorted(session.videos, key=lambda v: v.slot) if v.deleted_at is None]  # side_a, side_b, rear
    side_videos = [v for v in videos if v.slot != "rear"]

    def planned(v: Video) -> int:
        return pipeline.planned_frames("rear" if v.slot == "rear" else "side", v.frames or 0, pipeline.effective_fps(v.container_fps or 30.0, v.capture_fps))

    # Progress budget per Video, in proportion to its planned work.
    weights = [max(1, planned(v)) for v in videos]
    edges = np.concatenate([[0.0], np.cumsum(weights) / sum(weights) * 97.0])
    for k, video in enumerate(videos):
        lo, hi = float(edges[k]), float(edges[k + 1])
        family = "rear" if video.slot == "rear" else "side"
        label = "rear" if family == "rear" else "side" if len(side_videos) == 1 else f"side video {side_videos.index(video) + 1}"
        progress(f"downloading {label}", pct=lo)
        local = tmp / f"{video.slot}.mp4"
        s3.download_file(BUCKET, video.storage_key, str(local))
        progress(f"checking {label}", pct=lo + 0.02 * (hi - lo))
        check = pipeline.check_video(local, capture_fps_hint=video.capture_fps, view=family)
        # Keep the Recording Check's verdict (warnings, recognized side); add the file facts.
        video.check_result = {**(video.check_result or {}), "file": check}
        # The browser cannot read fps, so the submit-time frame estimate used defaults; replace it with the
        # probed values so the queue ETA shown to other Runners is right.
        video.container_fps, video.capture_fps, video.duration_s, video.frames = check["container_fps"], check["capture_fps"], check["duration_s"], check["frames"]
        analysis.frames_planned = sum(planned(v) for v in videos)
        db.commit()
        if not check["passed"]:
            if family == "side" and len(side_videos) == 1:
                raise VideoRejected(check["reason"])
            out["views"][video.view if video.view != "side" else video.slot] = {"skipped": check["reason"]}
            continue
        out_dir = tmp / f"out_{video.slot}"
        out_dir.mkdir()
        scoped = pipeline.scoped_progress(progress, lo + 0.03 * (hi - lo), hi - 0.02 * (hi - lo))
        if family == "side":
            res = pipeline.analyze_side(local, out_dir, speed_kmh=session.speed_kmh, height_cm=session.height_cm_used, progress=scoped, fps=check["fps"])
            # The running direction tells which side of the Runner the camera saw.
            view = "left_side" if res["info"].get("near_side") == "L" else "right_side"
            if view in out["views"]:
                raise VideoRejected("same_side")
            video.view = view
        else:
            res = pipeline.analyze_rear(local, out_dir, progress=scoped, fps=check["fps"])
            view = "rear"
        res["warnings"] = list((video.check_result or {}).get("warnings") or [])
        key = f"sessions/{session.id}/keypoints_{view}.parquet"
        progress(f"uploading {label} keypoints", pct=hi - 0.02 * (hi - lo))
        s3.upload_file(str(out_dir / "keypoints.parquet"), BUCKET, key)
        s3.upload_file(str(out_dir / "keypoints.json"), BUCKET, key.replace(".parquet", ".json"), ExtraArgs={"ContentType": "application/json"})
        res["keypoints_key"] = key
        res["slot"] = video.slot
        out["views"][view] = res
        playback_key = f"sessions/{session.id}/playback_{view}.mp4"
        s3.upload_file(str(out_dir / "playback.mp4"), BUCKET, playback_key, ExtraArgs={"ContentType": "video/mp4"})
        res["playback_key"], res["playback_bytes"] = playback_key, (out_dir / "playback.mp4").stat().st_size
        db.commit()
    if not any(v in out["views"] and "metrics" in out["views"][v] for v in ("left_side", "right_side")):
        raise VideoRejected(next((r["skipped"] for r in out["views"].values() if "skipped" in r), "no_side_video"))


def _unreliable(base: str, warnings: list[str]) -> str | None:
    return next((w for w in warnings if base in UNRELIABLE_WHEN.get(w, set())), None)


def _store_results(db: DbSession, analysis: Analysis, session: Session, result: dict) -> None:
    sex = session.runner.sex
    views = result["views"]
    analysis.keypoints_keys = {v: r["keypoints_key"] for v, r in views.items() if "keypoints_key" in r}
    analysis.window = {v: r.get("window") for v, r in views.items()}
    analysis.camera_check = {v: r.get("camera_check") for v, r in views.items()}

    def add(base: str, family: str, side: str, m: dict, warnings: list[str], per_view: dict | None = None, value_text: str | None = None):
        definition = METRICS.get(base)
        if definition is None:
            return
        state = m.get("state", "unmeasurable")
        rng = definition.range_for(session.speed_kmh, sex) if not definition.descriptor else None
        if definition.descriptor and state == "measured":
            state = "descriptor"
        reason = None
        if state in ("measured", "descriptor") and (m.get("n", 0) < MIN_CYCLES or (m.get("mean_score") or 0) < MIN_SCORE):
            state, reason = "unmeasurable", "too_few_cycles" if m.get("n", 0) < MIN_CYCLES else "low_confidence"
        unreliable = _unreliable(base, warnings) if state != "unmeasurable" else None
        row = MetricValue(
            analysis_id=analysis.id, metric_key=base, view=family, side=side,
            mean=m.get("mean"), sd=m.get("sd"), n_cycles=m.get("n", 0), mean_score=m.get("mean_score"),
            state=state, reason=reason, value_text=value_text or (m.get("value") if isinstance(m.get("value"), str) else None),
            typical_low=rng.low if rng else None, typical_high=rng.high if rng else None, source_id=rng.source if rng else None,
            per_view=per_view, unreliable_reason=unreliable,
        )
        db.add(row)
        # Advice is the one place we say "change something": only on reliable, measured values.
        if definition.advice_eligible and state == "measured" and not unreliable and rng and row.mean is not None:
            _maybe_advice(db, analysis, definition, row, rng)

    # Side Views: each leg from its own View (Near Leg only); whole-body Metrics averaged over the Views.
    body: dict[str, list[tuple[str, dict, list[str]]]] = {}
    for view in ("left_side", "right_side"):
        res = views.get(view)
        if not res or "metrics" not in res:
            continue
        near = "L" if view == "left_side" else "R"
        warnings = res.get("warnings", [])
        for key, m in res["metrics"].items():
            if key.startswith("_"):
                continue
            base, side = _split_side(key)
            if base in WHOLE_BODY:
                if side in ("both", near):
                    body.setdefault(base, []).append((view, m, warnings))
            elif base == "foot_strike_pattern":
                continue  # recomputed below from the Near Leg's foot angle
            elif side == near:
                add(base, "side", near, m, warnings)
                if base == "foot_angle_ic" and m.get("mean") is not None:
                    add("foot_strike_pattern", "side", near, {**m, "state": "measured"}, warnings, value_text=foot_strike(m["mean"]))
    for base, entries in body.items():
        usable = [(v, m, w) for v, m, w in entries if m.get("mean") is not None] or entries
        means = [m["mean"] for _, m, _ in usable if m.get("mean") is not None]
        merged = {
            "mean": float(np.mean(means)) if means else None,
            "sd": float(np.mean([m["sd"] for _, m, _ in usable if m.get("sd") is not None])) if any(m.get("sd") is not None for _, m, _ in usable) else None,
            "n": int(sum(m.get("n", 0) for _, m, _ in usable)),
            "mean_score": float(np.mean([m.get("mean_score") or 0 for _, m, _ in usable])),
            "state": "measured" if any(m.get("state") == "measured" for _, m, _ in usable) else usable[0][1].get("state", "unmeasurable"),
        }
        per_view = {v: m.get("mean") for v, m, _ in entries} if len(entries) > 1 else None
        add(base, "side", "both", merged, sorted({w for _, _, ws in usable for w in ws}), per_view=per_view)

    rear = views.get("rear")
    if rear and "metrics" in rear:
        for key, m in rear["metrics"].items():
            if not key.startswith("_"):
                base, side = _split_side(key)
                add(base, "rear", side, m, rear.get("warnings", []))
    db.commit()


def _split_side(key: str) -> tuple[str, str]:
    if key.endswith("_L") or key.endswith("_R"):
        return key[:-2], key[-1]
    return key, "both"


def _maybe_advice(db, analysis, definition, row, rng):
    if row.mean < rng.low and definition.higher_is == "better":
        text_key = f"{definition.key}_low"
    elif row.mean > rng.high and definition.higher_is == "worse":
        text_key = f"{definition.key}_high"
    else:
        return
    if text_key not in ADVICE_TEXT:
        return
    # One Advice per Metric, even when both sides are outside the range.
    if any(a.metric_key == definition.key for a in analysis.advice):
        return
    body = ADVICE_TEXT[text_key].format(mean=row.mean, low=rng.low, high=rng.high)
    analysis.advice.append(Advice(metric_key=definition.key, text_key=text_key, params={"mean": row.mean, "low": rng.low, "high": rng.high}, body=body))
