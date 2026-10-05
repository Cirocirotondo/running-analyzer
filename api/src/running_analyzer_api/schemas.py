from __future__ import annotations

import uuid
from datetime import date, datetime

from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    invite_code: str
    accept_terms: bool
    accept_privacy: bool
    accept_disclaimer: bool
    is_adult: bool


class RunnerOut(BaseModel):
    id: uuid.UUID
    display_name: str | None
    height_cm: float | None
    weight_kg: float | None
    sex: str | None
    birth_year: int | None
    profile_complete: bool


class RunnerUpdate(BaseModel):
    display_name: str | None = None
    height_cm: float | None = Field(default=None, ge=100, le=250)
    weight_kg: float | None = Field(default=None, ge=25, le=250)
    sex: str | None = Field(default=None, pattern="^(female|male|other)$")
    birth_year: int | None = Field(default=None, ge=1900, le=2030)


class AccountSettings(BaseModel):
    notify_analysis_ready: bool


class AccountDeletion(BaseModel):
    email: str  # re-typed by the Runner as confirmation


class MeOut(BaseModel):
    account_id: uuid.UUID
    email: str
    role: str
    runner: RunnerOut
    notify_analysis_ready: bool = True


class SessionCreate(BaseModel):
    recorded_on: date
    speed_kmh: float = Field(gt=0, le=40)
    incline_pct: float = Field(default=0, ge=-10, le=30)
    shoes: str | None = Field(default=None, max_length=200)
    side_videos: int = Field(default=1, ge=1, le=2)  # one Side View, or both (left and right legs)
    rear_view: bool = False
    improvement_consent: bool = False
    processing_consent: bool


class VideoOut(BaseModel):
    slot: str  # side_a | side_b | rear
    view: str  # left_side | right_side | rear, or "side" until recognized
    uploaded: bool
    deleted: bool
    duration_s: float | None
    container_fps: float | None
    capture_fps: float | None
    check_result: dict | None


class UploadTarget(BaseModel):
    slot: str
    url: str
    max_bytes: int


class SessionOut(BaseModel):
    id: uuid.UUID
    recorded_on: date
    speed_kmh: float
    incline_pct: float
    shoes: str | None
    state: str
    created_at: datetime
    videos: list[VideoOut]
    analysis_state: str | None
    analysis_progress: str | None
    progress_pct: float | None = None  # while processing
    eta_seconds: int | None = None  # time left: processing estimate, or wait + processing when queued
    queue_position: int | None = None  # 0 = next to start
    failure_reason: str | None
    failure_report: str | None = None  # asked | open | closed (docs/SPEC.md §11)


class FailureReportAnswer(BaseModel):
    send: bool  # true: send the Videos to the team; false: delete them


class SessionCreated(BaseModel):
    session: SessionOut
    uploads: list[UploadTarget]


class VideoUploaded(BaseModel):
    size_bytes: int
    duration_s: float | None = None
    container_fps: float | None = None
    capture_fps: float | None = None
    width: int | None = None
    height: int | None = None


class MetricOut(BaseModel):
    per_view: dict[str, float | None] | None = None  # whole-body Metrics from two Side Views
    unreliable_reason: str | None = None  # Recording Check warning that may bias the value
    metric_key: str
    view: str
    side: str
    label: str
    unit: str | None
    mean: float | None
    sd: float | None
    n_cycles: int
    mean_score: float | None
    state: str
    reason: str | None
    value_text: str | None
    typical_low: float | None
    typical_high: float | None
    source_id: str | None
    advice_eligible: bool


class AdviceOut(BaseModel):
    metric_key: str
    body: str


class AnalysisOut(BaseModel):
    session: SessionOut
    pipeline_version: str
    finished_at: datetime | None
    window: dict | None
    camera_check: dict | None
    video_urls: dict[str, str]
    keypoints_urls: dict[str, str]
    metrics: list[MetricOut]
    advice: list[AdviceOut]
    info: dict | None
