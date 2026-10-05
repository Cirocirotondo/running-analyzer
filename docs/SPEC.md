# Running Analyzer — v1 specification

Status: draft, 2026-10-03. Terms are defined in [GLOSSARY.md](../GLOSSARY.md); decisions in [docs/adr/](adr/).
This document says what v1 does. It does not say how the pipeline measures things (see
[prototype/EXPERIMENTS.md](../prototype/EXPERIMENTS.md)); the pipeline is a module behind the contract in §6.

## 1. Scope

A web app where a Runner uploads treadmill videos of themself, gets an Analysis (skeleton overlay, Metrics
with Typical Ranges and sources, Advice) and can follow their Metrics over time.

v1 is a closed beta: invite-only, adults only, individual Runners (no Operators), English UI prepared for
i18n, no usage limits, no payments.

Out of v1 (decided in the design session): Operator version, shoe advice and catalogue, A/B comparison
between Sessions, re-analysis, shareable links, minors, push notifications, behavioural analytics,
rearfoot eversion/pronation.

## 2. People and access

- **Account**: email + password, Google, Apple (Supabase Auth, self-hosted). Created only with a valid,
  unused Invite Code. At sign-up the person declares they are 18+ and accepts the privacy notice and the
  medical disclaimer ("not a medical opinion").
- **Runner**: created automatically with the Account (one per Account in v1). The UI never shows the
  Account/Runner distinction. Fields in §5.
- **Admin**: a role on an Account, set by hand in the database for the team. Admins get the admin area (§4.8).

## 3. Core flow

1. Sign in (or sign up with an Invite Code).
2. First time only: complete the Runner profile (height mandatory; weight, sex, birth year optional, with a
   banner saying analyses are less accurate without them) and read the Recording Guide.
3. **New Session** (wizard):
   1. Treadmill Settings (speed, incline) and shoes (free text). Units: metric by default; mph, lb, ft/in
      accepted and converted on submit.
   2. Recording Guide recap (skippable after the first time).
   3. Upload one or two side Videos (at least one) and optionally a rear Video. Browser-side checks before
      upload: fps >= 60 (or capture-fps tag >= 60 for slow motion), duration >= 20 s (rear 6 s), file <= 1
      GB (configurable; only the Playback Video is kept, ADR 0008). Right after each upload the Recording Check (§11) recognizes the View
      (Left Side / Right Side from the running direction) and judges the camera placement; its outcome is
      shown next to the Video, which can be replaced on its own. Two Videos of the same side must be
      replaced. A Session needs at least one Side View; Views can be added only before submitting.
   4. (merged into 3)
   5. Consent: explicit consent to processing the Videos (mandatory) and Improvement Consent (optional
      checkbox: "allow the team to view this Session's videos to improve the analysis").
   6. Submit: the Session is created, the Analysis job is queued.
4. **Processing page**: state of the job (queued → running → done / failed) with elapsed time and an
   estimate. The Runner may leave; an email is sent when the Analysis is ready or has failed.
5. **Analysis page** (§4.5).
6. **Home**: list of Sessions (date, speed, shoes, state) and a trend chart of selected Metrics over time.

## 4. Screens

### 4.1 Sign in / Sign up
Email+password, Google, Apple. Sign up asks for the Invite Code first; invalid or used codes are rejected
with a clear message. Age (18+) checkbox, privacy notice and disclaimer acceptance, both stored with a timestamp.

### 4.2 Home
- Cards or rows for each Session: date, speed/incline, shoes, Views present (side / side+rear), state
  (processing, done, failed with reason, video deleted).
- Trend chart: one Metric at a time (selector), one point per Session with a done Analysis, shaded Typical
  Range band when defined for that speed. Unmeasurable points are omitted and listed below the chart.
- "New Session" button.

### 4.3 New Session wizard
As in §3 step 3. The Recording Guide is a page with illustrations and the rules:
phone at hip height, perpendicular to the belt, 3–4 m away, whole body in frame with margin, main camera
(no ultra-wide), 60 fps or more, or slow motion applied to the whole clip; start recording when already at
speed; 20–30 s; rear view from directly behind, closer (~2 m). The guide text is content, not code
(editable without a deploy).

### 4.4 Processing
Job state, progress message from the worker ("checking video", "estimating pose 40 %", "computing
metrics"), and, on failure, the reason in plain words (e.g. "the legs are not fully visible") with a button
to re-upload that Video into the same Session.

### 4.5 Analysis
- **Player**: the Side View Video with the skeleton drawn in the browser from the keypoints file, toggle
  on/off, play/pause, 0.25×–1× speed, frame step, markers for initial contact and toe-off. Rear View in a
  second tab when present.
- **Metric cards**, one per Metric, grouped Side / Rear: value (mean ± SD over cycles, number of cycles),
  unit, Typical Range band with the Runner's value positioned on it, source citation (study, year, link),
  state badge (measured / descriptor / unmeasurable with the reason). Clicking a card scrubs the player to
  a representative cycle.
- **Advice** section: only for Metrics configured as advice-eligible (v1: cadence, pelvic drop, vertical
  oscillation) and only when the value is outside the Typical Range and measured. Text from a template per
  Metric, always with the source and the disclaimer. Never a diagnosis.
- **Session info**: speed, incline, shoes, height used, pipeline version, camera check result.
- Actions: delete Videos (keeps the Analysis), delete Session, export PDF.

### 4.6 Profile
Runner fields, unit preferences, consents given (with dates), "download my data" (ZIP: Videos,
keypoints, Analyses as JSON, profile as JSON), "delete my account" (immediate, confirmed by re-typing the
email).

### 4.7 Legal pages
Privacy notice, terms, disclaimer. Content, not code.

### 4.8 Admin area (role Admin only)
- Invite Codes: generate N single-use codes, list with state (unused / used by whom, when), revoke.
- Accounts: list with sign-up date, number of Sessions, last activity; no personal data beyond email.
- Failed Sessions: list with failure reason and pipeline log; Videos viewable only if the Session has
  Improvement Consent.
- Stats: Sessions per day, mean processing time, storage used, Active Accounts (30 days), monthly
  sign-up cohorts with retention. All computed from the database.

## 5. Domain model

Field types are indicative; ids are UUIDs; all timestamps UTC.

- **Account**: id, email, auth_provider, role (runner | admin), created_at, last_active_at (updated at
  most once per hour by API calls), invite_code_id, consents: terms_accepted_at, privacy_accepted_at,
  disclaimer_accepted_at, adult_declared_at, deletion_requested_at.
- **InviteCode**: id, code, created_by (Account), created_at, used_by (Account, nullable), used_at,
  revoked_at.
- **Runner**: id, account_id, display_name, height_cm, weight_kg (nullable), sex (nullable: female | male |
  other), birth_year (nullable), created_at. Height changes are versioned: **RunnerMeasurement**: id,
  runner_id, height_cm, weight_kg, valid_from.
- **Session**: id, runner_id, recorded_on (date), speed_kmh, incline_pct, shoes (text, nullable),
  height_cm_used, weight_kg_used, improvement_consent (bool), processing_consent_at, state (draft | queued
  | processing | done | failed | videos_deleted), created_at.
- **Video**: id, session_id, view (side | rear), storage_key, size_bytes, duration_s, container_fps,
  capture_fps (nullable), width, height, uploaded_at, deleted_at (nullable), check_result (json: passed,
  reasons).
- **Analysis**: id, session_id (unique), pipeline_version, started_at, finished_at, state (running | done |
  failed), failure_reason (text, nullable), window (json: start_s, end_s per view), camera_check (json),
  keypoints_key (storage key of the keypoints file per view), log_key.
- **MetricValue**: id, analysis_id, metric_key, view, side (L | R | both), mean, sd, n_cycles, mean_score,
  state (measured | descriptor | unmeasurable), reason (nullable), typical_low, typical_high (nullable,
  the range applied), source_id (nullable).
- **Advice**: id, analysis_id, metric_key, text_key, params (json).
- **MetricDefinition** (configuration, versioned in the repo not the database): key, label, unit, view,
  descriptor (bool), advice_eligible (bool), typical ranges: list of {speed_min, speed_max, sex, low,
  high, source}. Sources from [typical-ranges.md](typical-ranges.md).

Deletion rules (see §11, Playback Video and retention, which replaces the original-footage rules): deleting a Video removes the file and sets deleted_at; the Session becomes
`videos_deleted` and the Analysis stays. Deleting a Session removes Videos, keypoints, Analysis,
MetricValues, Advice. Deleting an Account removes everything of its Runners and the Account row; backups
expire within 30 days. Accounts inactive for 24 months get a warning email, then deletion after 30 days.

## 6. Pipeline contract (API ↔ worker)

The worker is a separate process consuming a Redis queue. Job payload:

```json
{"analysis_id": "...", "session": {"speed_kmh": 14, "incline_pct": 0, "height_cm": 179, "sex": null},
 "videos": [{"view": "side", "storage_key": "..."}, {"view": "rear", "storage_key": "..."}],
 "pipeline_version": "2026.10"}
```

Worker steps, each reported as progress: download → video check (fps, duration, body in frame, camera
tilt estimate) → steady window selection → pose estimation → events and Metrics → write outputs.

Outputs written to storage and the database:
- `keypoints_<view>.parquet` (frame, joint, x, y, score) in the analyzed window, frame numbers relative to
  the source file, plus `window.json` (start/end frames and fps actually used).
- `metrics.json`: the prototype's format, one entry per metric with mean, sd, n, mean_score, state;
  `_info` with event frames, direction, near side, camera check.
- A log file.

Failure reasons are an enum shown to the Runner in plain words: `fps_too_low`, `too_short`,
`runner_not_found`, `body_not_fully_visible`, `no_steady_running`, `camera_too_low`, `internal_error`.

Rules the API applies on the worker's output: a Metric is shown as unmeasurable if its state says so, if
n_cycles < 6, or if the camera check flags the Metric as unreliable for that placement (configuration per
Metric). Typical Range lookup by speed and sex; outside the covered speed band → no range, no Advice.
Angular Metrics are reported for the near leg only when the far leg's score is below a configurable
threshold (default: show both, flag the far leg).

## 7. API (FastAPI, JWT from Supabase Auth)

- `POST /invite-codes/validate`, `POST /auth/signup` (code + consents), session via Supabase client.
- `GET/PUT /me/runner`, `GET /me/export` (async ZIP, email with link), `DELETE /me`.
- `POST /sessions` (metadata + consents) → session id and signed upload URLs per view;
  `POST /sessions/{id}/videos/{view}/uploaded` (confirms upload, triggers checks);
  `POST /sessions/{id}/submit` (queues the job); `GET /sessions`, `GET /sessions/{id}`,
  `DELETE /sessions/{id}`, `DELETE /sessions/{id}/videos`.
- `GET /sessions/{id}/analysis` (metrics, advice, signed URLs for video and keypoints),
  `GET /sessions/{id}/analysis/pdf`, `GET /sessions/{id}/status` (polling; SSE later if needed).
- `GET /trends?metric=...`.
- Admin: `POST /admin/invite-codes`, `GET /admin/invite-codes`, `POST /admin/invite-codes/{id}/revoke`,
  `GET /admin/accounts`, `GET /admin/failed-sessions`, `GET /admin/sessions/{id}/videos` (only with
  Improvement Consent), `GET /admin/stats`.

Uploads go from the browser straight to S3-compatible storage with signed URLs; the API never proxies
video bytes.

## 8. Emails

Analysis ready; Analysis failed (with reason and re-upload link); data export ready; inactivity warning;
account deleted confirmation. Transactional provider to be chosen (must be EU-hosted or EU-region).

## 9. Non-functional

- Hosting per ADR 0004: one Hetzner VPS (Next.js, FastAPI, Redis, worker on CPU, PostgreSQL, Supabase
  Auth) + Hetzner Object Storage. Everything in Docker Compose, identical in development.
- CPU processing budget: measured in a 4-CPU container at ~0.6 s per frame, the worker subsamples to
  120 fps (`PIPELINE_MAX_FPS`) and a 30 s clip takes ~35 minutes end to end. The Runner is told to expect
  "up to an hour" and is emailed. A serverless GPU worker (ADR 0004) brings this to a few minutes behind
  the same queue when it matters.
- Pipeline version recorded on every Analysis; Typical Range configuration versioned with the code.
- i18n: all UI strings in message files; English only shipped.
- Accessibility: keyboard-operable player and cards; colour is never the only carrier of state.
- Logging without personal data beyond ids; errors to a self-hosted tracker (optional).

## 10. Open questions, to be settled by the validation recordings

- Which Metrics are reliable enough to show at all from a floor-level camera (validation protocol in
  [validation-recording-protocol.md](validation-recording-protocol.md)).
- Reliability threshold on keypoint score (prototype: 0.5) and minimum cycles (prototype: 6).
- ~~Whether angular Metrics are shown for both legs or the near leg only~~: near leg only (10-04 validation).
- cm scale: leg-length estimate from height vs hip-to-floor measurement in the profile (and a calibration
  photo later).

## 11. Decisions of 2026-10-04 (after the camera-placement validation)

**Views.** Left Side, Right Side and Rear, named after the side of the Runner the camera sees. Each Side
View measures its Near Leg only. With both Side Views, leg Metrics show left | right side by side with the
difference (no judgement, no Advice), and whole-body Metrics (cadence, step length, vertical oscillation,
trunk lean) show the mean of the two Views with both values in the info popup.

**Recording Check.** A light worker on its own queue inspects ~12 frames of each uploaded Video within
seconds. Outcomes:
- *Rejected*: no runner, body out of frame, < 60 fps, too short, running direction not recognizable.
- *Warning* (can still be submitted): camera too low or too high (camera height estimated from where the
  image centre falls between feet and hips; hip height ≈ 120 %, floor ≈ 0 %, neighbouring treadmill ≈
  45 %; warning below 75 %), phone tilted beyond what the roll correction handles, runner too small in
  the frame.
- *OK*.
Metrics affected by a Warning are **Unreliable**: shown with their value and a "!" marked "not
reliable", and never produce Advice (low camera: knee flexion, tibia and foot angle, foot strike).

**Emails** (provider Brevo, EU; Mailpit in development; also used by Supabase Auth): Analysis ready (can
be turned off in the profile, on by default), Analysis failed, account deleted. Data export and legal
pages are postponed to after the beta (a short notice for testers is still needed before inviting them).

**Admin area**: §4.8 plus Recording Check statistics (warnings and rejections by reason).

**Tests**: synthetic videos generated with ffmpeg (slow-motion tag, initial gap, dropped frames, edit
list) checked into the repository test the frame/time mapping; a short real clip kept outside git tests
the Metrics against expected values. Fast tests run on GitHub Actions on every push; the real-clip test
runs locally.

**Playback Video and retention** ([ADR 0008](adr/0008-only-the-playback-video-is-kept.md)).
- After a successful Analysis the worker writes, for each Video, a Playback Video: the frames of its
  Analysis Window that were analyzed (one per keypoint row, e.g. 2400 frames at 120 fps for a 240 fps
  slow-motion Video), in real time, with regular timestamps starting at 0, upright pixels, no audio,
  H.264 CRF 23 (about 19 MB per 20 s). CRF 26 (about 12 MB) was judged acceptable too, should storage
  need to shrink. Side and Rear Videos are treated the same way.
- The player, the admin video view (Improvement Consent) and "delete videos" all act on the Playback
  Video; the uploaded Video is deleted as soon as the Playback Video is stored.
- When an Analysis fails, its uploaded Videos are deleted, except through a Failure Report:
  - `fps_too_low`, `too_short`: deleted right away.
  - `internal_error` and the reasons that may be our mistake (`runner_not_found`,
    `body_not_fully_visible`, `no_steady_running`, `not_side_view`): if the Session has Improvement
    Consent, a Failure Report opens at once; otherwise the Session page and the "Analysis failed" email
    ask the Runner to send the Videos to the team (answering yes grants Improvement Consent and opens a
    Failure Report). No answer within 7 days, or "no": the Videos are deleted.
  - Admins learn of a new Failure Report by email and by a count next to the Admin link; it is
    highlighted in "Failed analyses". "Re-analyze" runs the Analysis again in the same Session (if it
    succeeds: "Analysis ready" email, Playback Video, original deleted, report closed); "Resolved" closes
    it and deletes the Videos. Unresolved reports are closed and their Videos deleted after 90 days.
  - The failure reason and the Recording Check results always stay.
- Draft Sessions untouched for 7 days are deleted with their Videos.
- Sessions analyzed before this change keep their original Videos as they are.
- Choosing the Analysis Window in the wizard and cutting the Video in the browser before upload are
  postponed; the server keeps choosing the Analysis Window.
