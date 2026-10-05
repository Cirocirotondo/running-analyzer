# Prototype experiments

Log of what was tried on real videos, with outcomes. Dates are 2026.

## Test videos

| Video | Content | Notes |
|---|---|---|
| `data/pexels_992697.mp4` | woman, side view, 25 fps, 11 s | stock clip, camera roughly at hip height |
| `data/pexels_6455341.mp4` | man, portrait, 24 fps, 10 s | stock clip, low camera |
| `videos/20261003_174723.mp4` | owner, side view, **240 fps** (8x slow motion, 30 fps container), 82 s, 14 km/h, 179 cm | phone on the floor ~1.5 m from the belt, tilted up; runner enters at 8 s, steady from ~15 s |
| `videos/20261003_174340.mp4`, `174547.mp4` | owner, side views, 30 fps | both from floor level, legs occluded by the treadmill arches |
| `videos/20261003_174926.mp4` | owner, rear view, 240 fps capture, slow motion only in parts | not analyzed yet |

## 10-03 — RTMPose vs MediaPipe (ADR 0007)

RTMPose (Halpe26 via rtmlib, `performance` mode) vs MediaPipe PoseLandmarker heavy, same pipeline.
On all four videos MediaPipe loses the feet: cadence 158 ± 43 vs 157 ± 7 steps/min on the owner's clip,
far-leg score 0.54 vs 0.86. RTMPose chosen. GPU: ~80–120 ms/frame; MediaPipe CPU: ~60 ms/frame at 1080p,
but 9.8 s/frame on a 1440x2560 portrait clip (unexplained, not investigated).

## 10-03 — Gait events

Zeni 2008 (heel furthest ahead of hip = initial contact; toe furthest behind = toe-off) works for initial
contact but toe-off comes 2–3 frames late at 25 fps in running (the foot keeps trailing back after lift-off).
Fixed by taking the frame where the toe's upward velocity first reaches 30 % of its cycle peak; verified by
eye within ±1 frame at 25 fps and ±25 ms at 240 fps. Prominence threshold for peak detection must use a
robust range (5th–95th percentile), otherwise a few bad frames during warm-up suppress all events.

Visual checks of initial contact are unreliable when the camera is at floor level: a foot 5 cm above the
belt looks like it is on it. Raw keypoint x-trajectories (foot moving forward, then back with the belt)
are the better reference there.

## 10-03 — Slow-motion clips

Samsung writes `com.android.capture.fps` (e.g. 240) while the container says 30 fps; every captured frame
is kept, so real time = frame / capture fps. `analyze.py` reads the tag with ffprobe. Partial slow motion
(`SlowMotion_Data` segments) is ambiguous: the Recording Guide should require either normal speed at
>= 60 fps or slow motion applied to the whole clip.

## 10-03 — Low camera: can 3D pose or self-rectification fix it? No.

Problem: users will not always place the phone at hip height; the owner's clip was shot from the floor.

1. **RTMW3D (3D whole-body model in rtmlib)** on seconds 9–20: depth output is nearly flat — left/right
   hip depth difference 2 cm where the pelvis is ~25 cm wide — so 3D knee angles equal the 2D ones within
   1°. Monocular 3D from this viewpoint adds nothing. `pose3d.py`.
2. **Self-rectification from limb-length constancy**: fit a homography (focal, tilt, pan) that makes thigh
   and shank lengths constant across 2 600 frames. The segment-length CV only drops from 3.9 % to 3.7 % and
   the angles move by < 1°, so the fit is not constrained by the data. `rectify.py`.

What the attempt did show: even from floor level the thigh and shank lengths vary only ~4 % over the
cycle, so the sagittal angles are probably less distorted than feared; the measures that suffer are
vertical ones in cm (vertical oscillation came out at 15 cm, typical 6–10) and near/far leg comparisons
(knee flexion at IC 14° near vs 8° far).

## 10-03 — Steady-state window and detector frequency

`--auto-window 20`: a coarse pose pass at ~30 fps (every 8th frame of a 240 fps clip, 3 min for 82 s)
finds the 20 s with the lowest coefficient of variation of step intervals, the runner in frame and well
tracked; the full pass then runs only there. On `174723` it chose 47–67 s (CV 0.034); metrics match the
hand-picked 30–50 s window (cadence 166 ± 2 vs 167 ± 4, contact 261/251 vs 257/252 ms). Needed in the
product: the first 10–15 s of every clip are warm-up and ruin the standard deviations.

`--det-every N` (rtmlib PoseTracker, detector every N frames, previous pose box in between), 5 s of the
same clip: N=1 80 ms/frame, N=8 30 ms, N=24 25 ms, with identical metrics (cadence 167.0/167.2/167.2,
knee at IC 13.4/13.3/13.2°). Default is now 8: 30 s at 240 fps take ~4 min on the RTX 4060.

## 10-03 — CPU cost and model presets (for hosting decisions)

`--device cpu`, det-every 8, 1080x1920 frames, same clip:

| preset (rtmlib) | 32 cores | 2 cores (taskset) | mean score |
|---|---|---|---|
| performance (YOLOX-x + RTMPose-x) | 244 ms/frame | 246 ms/frame | 0.81 |
| balanced (YOLOX-m + RTMPose-m) | — | 55 ms/frame | 0.79 |
| lightweight | — | 51 ms/frame | 0.64 |

The performance preset does not scale with cores, so a 2-vCPU VPS is as fast as the laptop: ~30 min for
30 s at 240 fps (15 min at 120 fps). On the RTX 4060 the same run takes 18–30 ms/frame.

Balanced vs performance on the steady 47–67 s window (GPU): means are close for cadence, tibia, trunk and
ankle-ahead-of-hip, but balanced is much noisier (contact time ±23 vs ±7 ms, foot angle ±6.4 vs ±1.1°,
knee at IC ±5.5 vs ±1.8°) and shifts contact time by +20–30 ms and vertical oscillation by −3 cm. The
performance preset is required for the Metrics we show; balanced is only a fallback for a quick preview.

Consequence for hosting: either accept 15–30 min per analysis on a CPU VPS (queue, email when done), or
run the worker on serverless GPU (2–4 min, a few cents per analysis).

**In Docker (10-04):** ONNX Runtime sizes its thread pool from the host CPU count (32 here), so inside a
container limited to 4 CPUs it ran 32 spinning threads: 4.9 s/frame, 20x slower than the host. With
`intra_op_num_threads` forced to the CPU quota (`ORT_THREADS`, injected by `worker/pipeline.py` because
rtmlib exposes no session options) and `cpus: 4`: 614 ms/frame — still 2.5x the laptop figure, which is
what a small VPS should be budgeted at. The worker therefore subsamples to 120 fps (`PIPELINE_MAX_FPS`):
a 20 s window = 2 400 frames ≈ 25 min, plus ~9 min for the coarse pass over a 30 s clip.

## 10-04 — Pose robustness: forced re-detection and limb-length gate

Simone's side clip showed single frames with a badly wrong skeleton (legs folded onto the treadmill
frame). Cause: with `det_every = 8` the detector runs every 8th frame and in between the box comes
from the previous pose, so one bad pose feeds the next (drift loop), helped by the treadmill arches
occluding the legs. Two fixes in `analyze.py`:

- `_run_rtmpose` forces the detector on the next frame when a pose looks suspicious (mean score
  < 0.5, or person height jumping by more than 25 % between consecutive frames).
- `clean()` applies `implausible_legs()`: thigh or shank lengths deviating more than 35 % from their
  median mark that leg's knee/ankle/heel/toe as missing, which are then interpolated like low-score
  points. The count is stored in `camera_check.implausible_leg_frames`.

Regression on the pexels clip: same events and cadence. On Simone's clip (4 800 frames at 120 fps)
the gate fired on 0 frames after the forced re-detection, i.e. the re-detection alone removed the
drift.

## 10-04 — Foot keypoints: where the error comes from, four methods compared

Simone's bar: when a foot is visible, its markers must be inside the shoe. With the raw/filtered
toggle in the player the raw points were already outside the shoe in some frames, so the model,
not the filter, is the cause. Compared on 24 frames (one second, ~1.4 strides, 1080×1920 at 240
fps) of Simone's side video, GPU, foot points only:

| method | ms/frame (GPU) | median shift vs A (ankle/heel/toe px) |
|---|---|---|
| A — current: YOLOX-x box + RTMPose-x (Halpe26) | 132 (incl. detector) | — |
| B — second RTMPose-x pass on a lower-body crop from A | +14 | 3–5 |
| C — RTMW-x (133 keypoints, cocktail14) on A's box | +27 | 4–8 |
| D — A averaged with its horizontally flipped crop | +22 | 1–4 |

Contact sheets (`feet_L.png`, `feet_R.png`, scratch): in stance, with the foot free, all four
methods put ankle, heel and toe inside the shoe within 3–5 px of each other. In swing the foot is
motion-blurred (visible at 240 fps in a dim gym) and seen from below with the sole showing, and the
toe drifts 10–25 px past the shoe; behind the treadmill arches the methods scatter by 30–60 px. No
method is clearly better, so the model is not the bottleneck: viewpoint, blur and occlusion are.
Decision: keep RTMPose-x. (An earlier claim of a 50 px ankle error at frame 2700 came from a
mis-aligned render: OpenCV seeking plus ignoring the window's start frame. See the next entry.)

Over the whole window, ankle–heel deviates > 35 % from its median in 5–6 % of frames and heel–toe in
1.5 %, all in swing or behind the arches. `implausible_legs()` now also gates the foot (ankle–heel
→ heel; heel–toe → heel and toe); discarded points are interpolated and shown in red in the player
(score set to 0 in the browser JSON, `camera_check.discarded_frames`). Regression on the 240 fps
clip (frames 7200–12000, reused keypoints): every Metric unchanged (≤ 0.2 ms on contact/flight).

What would actually move foot accuracy: camera at knee/hip height instead of the floor (feet seen
side-on like the training data), no treadmill frame between camera and legs, more light (shorter
exposure, less blur). Added to the recording guide inputs.

## 10-04 — Recording Check: camera height and side from a dozen frames

Camera height from where the image centre falls between the feet on the belt and the hips, as a share
of hip height (valid for a level phone): 119–128 % at hip height, 45–47 % from the neighbouring
treadmill (phone tilted up 4–5°, which raises the estimate by ~30 cm), −7 / +9 % from the floor. A
warning below 75 % separates them cleanly. The near/far foot height difference does not work (a few
pixels everywhere: the far foot is estimated too loosely).

`worker/checks.py` on 12 frames from 20–80 % of each 10-04 clip, mid-size model, CPU, ~10 s per clip:
side recognized on all six side clips; hip height OK (right clip roll −2.8°, within correction); both
other-treadmill clips camera_low; floor clips rejected because the head leaves the frame (the nose
must be at least 1/16 of the body height below the top edge: the head is needed for the vertical
oscillation); rear OK (74 cm above the belt, ratio 0.80, rear threshold 0.6).

## 10-04 — Changes applied after the camera validation

- **Vertical oscillation from the head** (`nose`) instead of the hip midpoint. Hip-height clip: 9.5 cm
  (was 18.1). The 10-03 "too high" Advice disappears.
- **Near leg only** for side-view per-leg Metrics (`jobs._store_results` skips the far side; near side
  from keypoint scores, correct on all 7 clips). The analysis page says which leg was measured and
  how to measure the other.
- **Pelvic drop descriptive, no Advice** until validated against pelvis markers (`metrics_config`).
- **Camera roll correction**: `analyze.camera_roll()` takes long near-horizontal lines of the treadmill
  deck in the background (median of 15 frames, band around the feet) and `level()` rotates the
  keypoints before the metrics; the browser JSON stays in image coordinates and carries `roll_deg`,
  which the player's angles use. Right hip-height clip: roll −2.8° (−2.5° by hand from the markers);
  trunk lean left/right 6.2 / 2.6° → 5.5 / 5.5°, foot angle 7.0 / 10.0° → 7.7 / 7.2°. Rear: 0.2°.
- **Recording Guide** in the app: hip height required (with the numbers), phone level, near leg only.
- **Rear window from the middle of long clips**: the worker analysed the first 20 s, which on a 99 s
  clip included getting on the belt (rear cadence 136 instead of ~166).
- **Docker**: single-file bind mounts (`prototype/analyze.py`) go stale when the file is replaced
  (`sed -i`): recreate the container (`up -d --force-recreate`) after such edits.

Anatomy (Simone, barefoot): floor to knee 52 cm, knee to ankle 45 cm; the 106 cm "hip" was taken at
the waistband (iliac crest), ~10 cm above the hip joint the model estimates. Keypoint segments in true
cm (markers): shank 41.6–42.9 cm in all six positions (±1.5 %), thigh 36.9–41.1 cm (±5 %), so the
shank is the stable scale reference; keypoint shank ≈ 0.94 × anatomical shank for this runner.
Proposed, not applied: scale from the shank (optionally from a "knee height" profile field).

## 10-04 — Camera-placement validation (one phone, tape markers)

Seven clips, 240 fps, ~75 s of steady running each, treadmill Woodway, belt speed measured 13.7 km/h.
Positions (distance = camera to the line the feet land on; height = lens relative to the belt):
A hip height (+105 cm, 296 cm), B floor (−17 cm, 194 cm), C on the neighbouring treadmill (+14 cm,
268 cm); A, B and C from both sides, plus a rear clip (+74 cm, 200 cm). Clips facing left in the
image show the runner's **left** side. Scripts: `validation_pose.py` (pose over whole clips at
120 fps, `data/validation/*.npz`), `validation_markers.py` (deck markers and belt speed),
`validation_analysis.py` (metrics per 20 s window, true scale). Within each clip three 20 s windows
give the clip-internal spread.

**Scale and speed.** The two deck markers (100 cm between inner edges) measure 521 px at 252 cm and
588 / 583 px at 224 cm: focal length 1312 px, consistent with the measured distances to 1 %. The
belt marker crosses them in 280 ms (median of 24 passes, IQR ±0.5 %): 13.7 km/h after the depth
correction for the belt edge (belt 56 cm wide inside an 88 cm frame, from the rear clip). The
app's height-based scale (thigh + shank = 49 % of height) is 1–6 % too large: +1.2 / +3.7 % at
hip height, +4.0 / +5.5 % from the floor, +4.9 / +6.3 % from the other treadmill. Simone's
keypoint leg (hip–knee–ankle) is about 82–84 cm, 46–47 % of height.

**Near leg, by camera position** (mean of three windows; within-clip spread in brackets):

| Metric | Left A | Left B floor | Left C | Right A | Right B floor | Right C |
|---|---|---|---|---|---|---|
| Knee flexion at IC (°) | 17.0 (±0.9) | 12.1 (±0.4) | 14.2 (±1.7) | 17.4 (±0.6) | 12.6 (±1.1) | 12.1 (±1.0) |
| Tibia angle at IC (°) | −8.5 (±0.4) | −10.8 (±0.6) | −11.5 (±0.4) | −9.9 (±0.6) | −11.7 (±0.8) | −11.7 (±0.5) |
| Foot angle at IC (°) | 6.8 (±0.8) | 2.4 (±0.3) | 5.6 (±0.5) | 10.0 (±0.4) | 0.8 (±0.6) | 3.1 (±0.7) |
| Ankle ahead of hip, true scale (cm) | 26.6 | 27.0 | 28.5 | 29.9 | 29.0 | 27.1 |
| Vertical oscillation, nose (cm) | 9.5 | 9.4 | 9.2 | 8.0 | 8.2 | 8.7 |
| Vertical oscillation, hips (cm) | 18.2 | 18.5 | 16.2 | 15.7 | 18.4 | 15.4 |
| Cadence (steps/min) | 165.2 | 166.9 | 168.5 | 169.5 | 165.9 | 165.8 |

Findings:

- **Camera height matters for angles.** From the floor or the neighbouring treadmill, knee flexion at
  contact comes out ~5° lower than at hip height (on both sides), the tibia angle 2–3° more negative,
  the foot angle 4–9° lower. These shifts are 3–10× the within-clip spread. Distances (ankle ahead of
  hip, true scale) agree within ±2–3 cm. Hip height must be a requirement of the Recording Guide.
- **The far leg is not measurable.** Same leg, hip-height camera, near vs far side: knee flexion 17.0 vs
  9.6° (left) and 17.4 vs 7.1° (right); foot angle 10.0 vs −4.4° (right). Report the near leg only;
  both legs need one recording per side.
- **Vertical oscillation from the hip keypoints is wrong by ~2×.** Hips 15–18.5 cm per stride vs nose
  8.0–9.5 cm (shoulders 9–11 cm, noisier with arm swing). The trunk is rigid, so the hips cannot move
  twice as much as the head: the model's hip point follows the thigh. The nose agrees across all six
  positions and with the literature (6–10 cm). The 14.5 cm and the "too high" Advice of 10-03 were
  this artefact.
- **Pelvic drop from the hip keypoints is not trustworthy.** Rear clip, hip width 107 px (79 px on
  10-03): the pelvis tilts by ±2–3° every step, but the stance-side hip goes down, the opposite of a
  contralateral drop; the metric comes out −0.2 ± 0.5° (2.0 / 1.4° on 10-03). The same thigh-following
  bias of the hip keypoint explains it. Hip adduction 6.3° (L) / 3.7° (R). Camera roll from the deck's
  bottom edge: 0.2°, negligible.
- **Camera roll biases absolute angles.** In the right hip-height clip the deck edge is tilted by
  ~2.5°, and trunk lean reads 2–3° there vs 6° from the left. Trunk lean and tibia angle are measured
  against the image vertical, so a tilted phone shifts them one-to-one.
- **Temporal metrics** are not camera-dependent, but vary between bouts (cadence 165–170 across
  clips) more than within a clip (±0.2–1.4): compare sessions recorded the same day with care.

Also found: OpenCV's frame seek (`CAP_PROP_POS_FRAMES`) assumes evenly spaced frames; these clips
start with a 1.6 s gap after the first frame, so seeking to frame 12960 returned frame ~12939 and the
app's skeleton was ~90 ms off the video. `iter_frames` now skips by decoding.

Next: tape markers on the shorts over the sacrum (rear) and at the side of the hip (side view) give a
ground truth for pelvic drop and pelvis vertical oscillation independent of the pose model.

## 10-04 — Rear view in the worker: one stance found, absurd values

Simone's rear metrics in the app were all "not measurable", with 1 cycle per leg and pelvic drop
63–85°. The worker passed the whole clip to `analyze_rear.compute`, including the last ~0.7 s where
the runner steps off and leaves the frame (keypoint score 0.19, ankles at the bottom of the image).
Stance detection is percentile-based (bottom 25 % of each ankle's vertical range), so those frames
moved the threshold below every real stance. The prototype had cut them by hand with
`--start-seconds/--max-seconds`.

Fix: `analyze_rear.running_segment()` keeps the longest stretch where the mean score is ≥ 0.6 and the
pelvis stays within half a torso length of its median position (gaps ≤ 0.1 s bridged); the worker
computes on that stretch only and records it in `info.running_segment_frames`. On the clip: frames
0–1531 of 1669 (6.4 s), 9 stances per leg, pelvic drop 2.0 / 1.4°, hip adduction 4.4 / 5.3°, in line
with the 10-03 prototype run.

## 10-04 — Skeleton out of sync with the video: dropped frames and the edit list

Simone's screenshots at 1:30 and 1:33 of playback showed foot markers 40–80 px off a fully visible
foot, while the worker's rows for those frames, rendered from a sequential decode, sit inside the
shoe (`series.png`, scratch). The player was drawing the wrong row: it mapped the <video> time to a
file frame as `round(time × container_fps)`, assuming uniform timestamps. The uploaded clip has:

- an edit list from the trim: the first frame is shown at 0.0476 s, not 0 (≈ 1.4 frames);
- a timestamp jump of 166 ms between frames 2680 and 2681 (1:29.3): the phone dropped 5 container
  frames (≈ 21 ms of real time at 240 fps). The browser honours the timestamps; ffmpeg and OpenCV
  deliver frames by count.

So from 1:29 on the player was 4 frames late (1–2 before), and in swing the foot moves 5–10 px per
frame. Fix: the worker reads every frame's presentation time with ffprobe (`packet=pts_time`) and
writes `times[i]` per row into the browser JSON; the player looks the row up by time (binary
search) and takes the displayed frame's time from `requestVideoFrameCallback` when available.
Frame stepping and the window limits use the same table. Older JSONs without `times` fall back to
the fps formula.

Red herring on the way: comparing worker rows with a fresh pass "at the same index" gave a best match
at a 12-frame lag with 23 px residual. That was the stride period: the window now starts at frame
1200 (balanced coarse pass) and 1200 ≡ −11 mod the 173-frame stride. Aligned on `start_frame`,
worker rows match a detector-every-frame pass at lag 0 with 8 px median difference.

Open: the dropped frames also shorten the real-time axis of the metrics by 21 ms once in this clip
(one step interval). Negligible here; a gap detector that inserts missing rows would make it exact.

## 10-04 — Balanced model for the coarse pass (worker)

The steady-window search only needs cadence and the runner's position, so the worker now runs it with
the `balanced` preset (YOLOX-m + RTMPose-m) and keeps `performance` for the metrics pass. Cost per
coarse frame drops to ~0.2 of a full-pass frame (`COARSE_COST`), which the ETA uses. Simone's session
(side 25.2 s + rear 6.95 s) on the local GPU: 3:53 → 3:26 end to end.

## 10-04 — 240 vs 120 vs 60 fps (same keypoints, subsampled; window 47–67 s)

Means are identical at 240 and 120 fps (cadence 166.1, knee at IC 12.8/8.3°, all angles within 0.1°);
only the temporal SDs grow a little (contact ±7 → ±8 ms, flight ±6 → ±8 ms). At 60 fps a systematic drift
appears (contact +5 ms, flight −7 ms) and SDs are ~1.5×. Decision: analyze at 120 fps by default
(`PIPELINE_MAX_FPS`), 240 only for validation runs on the local GPU; 60 fps clips are accepted with
slightly less precise contact/flight times.

## 10-03 — Rear view (`analyze_rear.py`) on `174926`

The clip has a `SlowMotion_Data` tag (partial slow motion) but frame differences are uniform over the
whole file, and the cadence found with fps = 240 matches the side view (~157–170 vs 157 steps/min), so
all 1 669 frames are real 240 fps frames: 7 s of running, 9 stance phases per leg. The last 0.5 s has
the runner leaving the frame and must be cut.

Stance from behind: the ankle sits on a plateau at the bottom of its vertical range while on the belt;
stance = contiguous frames in the bottom 25 % of that range. Frontal-plane angles are taken as the peak
within each stance (close to midstance) rather than at a detected instant.

Results: contralateral pelvic drop 3.5 ± 1.5° (left stance) and 0.6 ± 1.1° (right stance) before
removing the pelvis baseline of −1.2° (camera roll or posture); ~2° each after. Hip adduction vs vertical
4.5–5.5°, vs pelvis 4–7°. Keypoint score 0.85–0.89. Hip width is only 79 px at this distance, so one
pixel of hip error is ~0.7° of pelvic tilt: the rear camera should be closer than the side one.

Open: how much does camera height actually change each Metric? Needs a controlled test: the same run
filmed at the same time from hip height and from the floor, then compare. Until then, the strategy is
Recording Guide + automatic tilt check from scene lines + Runner profile (height, hip-to-floor,
calibration photo) for scale.
