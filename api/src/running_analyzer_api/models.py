"""Database model, following docs/SPEC.md §5. Vocabulary from GLOSSARY.md.

An Account's id is the Supabase Auth user id (auth.users.id), so a JWT's `sub`
is the Account primary key: no lookup table between the two.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def uuid_pk():
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


def created_at():
    return mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)  # = auth.users.id
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    role: Mapped[str] = mapped_column(String(16), default="runner", nullable=False)  # runner | admin
    created_at: Mapped[datetime] = created_at()
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invite_code_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("invite_codes.id"))
    terms_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    privacy_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    disclaimer_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    adult_declared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deletion_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notify_analysis_ready: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)

    runners: Mapped[list[Runner]] = relationship(back_populates="account", cascade="all, delete-orphan")


class InviteCode(Base):
    __tablename__ = "invite_codes"

    id: Mapped[uuid.UUID] = uuid_pk()
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = created_at()
    used_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Runner(Base):
    __tablename__ = "runners"

    id: Mapped[uuid.UUID] = uuid_pk()
    account_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(100))
    height_cm: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    sex: Mapped[str | None] = mapped_column(String(10))  # female | male | other
    birth_year: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = created_at()

    account: Mapped[Account] = relationship(back_populates="runners")
    measurements: Mapped[list[RunnerMeasurement]] = relationship(back_populates="runner", cascade="all, delete-orphan")
    sessions: Mapped[list[Session]] = relationship(back_populates="runner", cascade="all, delete-orphan")


class RunnerMeasurement(Base):
    """History of height and weight, so old Sessions keep the values used at the time."""

    __tablename__ = "runner_measurements"

    id: Mapped[uuid.UUID] = uuid_pk()
    runner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runners.id", ondelete="CASCADE"), nullable=False)
    height_cm: Mapped[float | None] = mapped_column(Float)
    weight_kg: Mapped[float | None] = mapped_column(Float)
    valid_from: Mapped[datetime] = created_at()

    runner: Mapped[Runner] = relationship(back_populates="measurements")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = uuid_pk()
    runner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("runners.id", ondelete="CASCADE"), nullable=False)
    recorded_on: Mapped[date] = mapped_column(Date, nullable=False)
    speed_kmh: Mapped[float] = mapped_column(Float, nullable=False)
    incline_pct: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    shoes: Mapped[str | None] = mapped_column(String(200))
    height_cm_used: Mapped[float] = mapped_column(Float, nullable=False)
    weight_kg_used: Mapped[float | None] = mapped_column(Float)
    improvement_consent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processing_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # draft | queued | processing | done | failed | videos_deleted
    state: Mapped[str] = mapped_column(String(16), default="draft", nullable=False)
    created_at: Mapped[datetime] = created_at()

    runner: Mapped[Runner] = relationship(back_populates="sessions")
    videos: Mapped[list[Video]] = relationship(back_populates="session", cascade="all, delete-orphan")
    analysis: Mapped[Analysis | None] = relationship(back_populates="session", cascade="all, delete-orphan", uselist=False)


class Video(Base):
    __tablename__ = "videos"
    __table_args__ = (UniqueConstraint("session_id", "slot"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    # Upload slot (side_a, side_b, rear) and the View it turned out to be (left_side, right_side, rear).
    # A side Video's View is "side" until the Recording Check or the Analysis recognizes the running
    # direction.
    slot: Mapped[str] = mapped_column(String(8), nullable=False)
    view: Mapped[str] = mapped_column(String(16), nullable=False)
    storage_key: Mapped[str] = mapped_column(String(300), nullable=False)
    size_bytes: Mapped[int | None] = mapped_column(Integer)
    duration_s: Mapped[float | None] = mapped_column(Float)
    container_fps: Mapped[float | None] = mapped_column(Float)
    capture_fps: Mapped[float | None] = mapped_column(Float)
    frames: Mapped[int | None] = mapped_column(Integer)
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    uploaded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    check_result: Mapped[dict | None] = mapped_column(JSONB)
    # True once storage_key holds the Playback Video and the uploaded file is gone (ADR 0008); the file
    # facts above (fps, frames, size) stay those of the upload, except size_bytes.
    playback: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)

    session: Mapped[Session] = relationship(back_populates="videos")


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[uuid.UUID] = uuid_pk()
    session_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("sessions.id", ondelete="CASCADE"), unique=True, nullable=False)
    pipeline_version: Mapped[str] = mapped_column(String(32), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(16), default="queued", nullable=False)  # queued | running | done | failed
    progress: Mapped[str | None] = mapped_column(String(200))
    progress_pct: Mapped[float | None] = mapped_column(Float)  # 0-100 while running
    eta_seconds: Mapped[int | None] = mapped_column(Integer)  # worker's estimate of the time left
    frames_planned: Mapped[int | None] = mapped_column(Integer)  # pose-estimation frames, computed at submit
    frames_processed: Mapped[int | None] = mapped_column(Integer)  # actual count, written by the worker
    failure_reason: Mapped[str | None] = mapped_column(String(64))
    window: Mapped[dict | None] = mapped_column(JSONB)
    camera_check: Mapped[dict | None] = mapped_column(JSONB)
    keypoints_keys: Mapped[dict | None] = mapped_column(JSONB)  # {"side": storage key, "rear": ...}
    log_key: Mapped[str | None] = mapped_column(String(300))
    # Failure Report of a failed Analysis (docs/SPEC.md §11): asked (the Runner may send the Videos to
    # the team) | open (the team should look at it) | closed. Null when none was offered.
    failure_report: Mapped[str | None] = mapped_column(String(8))
    failure_report_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))  # last change of failure_report
    created_at: Mapped[datetime] = created_at()

    session: Mapped[Session] = relationship(back_populates="analysis")
    metrics: Mapped[list[MetricValue]] = relationship(back_populates="analysis", cascade="all, delete-orphan")
    advice: Mapped[list[Advice]] = relationship(back_populates="analysis", cascade="all, delete-orphan")


class MetricValue(Base):
    __tablename__ = "metric_values"

    id: Mapped[uuid.UUID] = uuid_pk()
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(64), nullable=False)
    view: Mapped[str] = mapped_column(String(8), nullable=False)
    side: Mapped[str] = mapped_column(String(4), nullable=False)  # L | R | both
    mean: Mapped[float | None] = mapped_column(Float)
    sd: Mapped[float | None] = mapped_column(Float)
    n_cycles: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    mean_score: Mapped[float | None] = mapped_column(Float)
    state: Mapped[str] = mapped_column(String(16), nullable=False)  # measured | descriptor | unmeasurable
    reason: Mapped[str | None] = mapped_column(String(64))
    value_text: Mapped[str | None] = mapped_column(String(32))  # descriptors such as the foot strike pattern
    typical_low: Mapped[float | None] = mapped_column(Float)
    typical_high: Mapped[float | None] = mapped_column(Float)
    source_id: Mapped[str | None] = mapped_column(String(64))
    # Whole-body Metrics measured from two Side Views: {"left_side": mean, "right_side": mean}.
    per_view: Mapped[dict | None] = mapped_column(JSONB)
    # Set when a Recording Check warning may bias the value (the Metric is Unreliable), e.g. camera_low.
    unreliable_reason: Mapped[str | None] = mapped_column(String(32))

    analysis: Mapped[Analysis] = relationship(back_populates="metrics")


class Advice(Base):
    __tablename__ = "advice"

    id: Mapped[uuid.UUID] = uuid_pk()
    analysis_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("analyses.id", ondelete="CASCADE"), nullable=False)
    metric_key: Mapped[str] = mapped_column(String(64), nullable=False)
    text_key: Mapped[str] = mapped_column(String(64), nullable=False)
    params: Mapped[dict | None] = mapped_column(JSONB)
    body: Mapped[str | None] = mapped_column(Text)

    analysis: Mapped[Analysis] = relationship(back_populates="advice")
