"""Periodic cleanup of Videos nobody will use (docs/SPEC.md §11, Playback Video and retention):

- draft Sessions untouched for 7 days are deleted with their Videos;
- Failure Reports the Runner did not answer within 7 days: the Videos are deleted;
- open Failure Reports older than 90 days: closed, the Videos deleted.

    uv run python -m worker.janitor          # every hour, forever (the janitor service)
    uv run python -m worker.janitor --once   # one pass
"""

from __future__ import annotations

import logging
import sys
import time
from datetime import UTC, datetime, timedelta

import boto3
from running_analyzer_api.models import Analysis, Session, Video
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from .jobs import BUCKET, S3, Db

DRAFT_DAYS = 7
ANSWER_DAYS = 7
REPORT_DAYS = 90
EVERY_SECONDS = 3600

log = logging.getLogger("janitor")


def run_once(now: datetime | None = None) -> dict:
    now = now or datetime.now(UTC)
    s3 = boto3.client("s3", **S3)
    done = {"drafts": 0, "unanswered": 0, "expired_reports": 0}

    def delete_files(session: Session) -> None:
        for v in session.videos:
            if v.deleted_at is None and v.uploaded_at is not None:
                s3.delete_object(Bucket=BUCKET, Key=v.storage_key)
                v.deleted_at = now

    with Db() as db:
        # A draft's last change is its creation or its latest upload.
        last_change = func.greatest(Session.created_at, func.coalesce(func.max(Video.uploaded_at), Session.created_at))
        stale = select(Session.id).join(Video, Video.session_id == Session.id, isouter=True).where(Session.state == "draft").group_by(Session.id).having(last_change < now - timedelta(days=DRAFT_DAYS))
        for s in db.execute(select(Session).where(Session.id.in_(stale)).options(selectinload(Session.videos))).scalars():
            for v in s.videos:
                if v.uploaded_at is not None:
                    s3.delete_object(Bucket=BUCKET, Key=v.storage_key)
            db.delete(s)
            done["drafts"] += 1
        db.commit()

        for state, days, key in (("asked", ANSWER_DAYS, "unanswered"), ("open", REPORT_DAYS, "expired_reports")):
            rows = db.execute(
                select(Analysis).where(Analysis.failure_report == state, Analysis.failure_report_at < now - timedelta(days=days))
                .options(selectinload(Analysis.session).selectinload(Session.videos))
            ).scalars()
            for a in rows:
                delete_files(a.session)
                a.failure_report, a.failure_report_at = "closed", now
                done[key] += 1
            db.commit()
    return done


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    while True:
        try:
            log.info("cleanup: %s", run_once())
        except Exception:
            log.exception("cleanup failed")
        if "--once" in sys.argv:
            return
        time.sleep(EVERY_SECONDS)


if __name__ == "__main__":
    main()
