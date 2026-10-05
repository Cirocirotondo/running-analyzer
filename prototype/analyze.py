"""Prototype: side-view running analysis from a treadmill video.

Usage:
    uv run analyze.py VIDEO --speed-kmh 12 --height-cm 178 [--model rtmpose|mediapipe] [--device cpu|cuda]

Pipeline: pose per frame -> gap interpolation + Butterworth filter -> gait events
(Zeni 2008: initial contact = heel furthest ahead of the hip, toe-off = toe furthest
behind) -> per-cycle metrics -> JSON + keypoints parquet + overlay video + plots.

Pixel-to-cm scale comes from the leg length (thigh + shank ~ 0.49 x height, Winter).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from scipy.signal import butter, filtfilt, find_peaks

# Common keypoint set shared by both models (left/right suffix added below).
JOINTS = ["shoulder", "hip", "knee", "ankle", "heel", "toe"]
SIDES = ["L", "R"]
NAMES = [f"{j}_{s}" for s in SIDES for j in JOINTS] + ["nose"]

# Halpe26 (rtmlib BodyWithFeet) and MediaPipe 33 indices for the common set.
HALPE26 = {"L": [5, 11, 13, 15, 24, 20], "R": [6, 12, 14, 16, 25, 21], "nose": 0}
MEDIAPIPE = {"L": [11, 23, 25, 27, 29, 31], "R": [12, 24, 26, 28, 30, 32], "nose": 0}

LEG_LENGTH_RATIO = 0.49  # thigh + shank as a fraction of body height (Winter 2009)
MIN_SCORE = 0.3  # keypoints below this are treated as missing and interpolated
MIN_CYCLES = 6  # fewer cycles than this makes every metric unmeasurable


# --------------------------------------------------------------------------- pose


def iter_frames(path: Path, max_frames: int | None = None, skip: int = 0, step: int = 1):
    """Yield frames one at a time so long high-fps videos never sit in memory.
    `step` > 1 yields every step-th frame (the others are decoded but not returned)."""
    cap = cv2.VideoCapture(str(path))
    # Skip by decoding, not with CAP_PROP_POS_FRAMES: OpenCV turns a frame number into a time assuming
    # evenly spaced frames, and phone clips are not (slow motion starts with a 1.6 s gap after the
    # first frame, phones drop frames). A seek then lands dozens of frames early and every keypoint
    # row is shifted against the video. grab() decodes without converting, ~400 frames/s.
    for _ in range(skip):
        if not cap.grab():
            cap.release()
            return
    i = 0
    while max_frames is None or i < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        yield frame
        i += 1
        for _ in range(step - 1):
            if not cap.grab():
                return
    cap.release()


def find_steady_window(kp, sc, fps, window_s, min_score=0.6):
    """Pick the window of `window_s` seconds where the runner is in frame, well
    tracked and running at a stable cadence. Returns (start_frame, cv) or None.
    Stability = coefficient of variation of the step intervals in the window;
    the runner must also stay put (hip position drift) so warm-up walks and
    people stepping on/off the treadmill are excluded."""
    j = {n: i for i, n in enumerate(NAMES)}
    ev = detect_events(kp, fps)
    ics = np.sort(np.concatenate([ev.ic["L"], ev.ic["R"]]))
    hip = (kp[:, j["hip_L"]] + kp[:, j["hip_R"]]) / 2
    leg = np.linalg.norm(kp[:, j["hip_L"]] - kp[:, j["ankle_L"]], axis=1)
    w = int(window_s * fps)
    best = None
    for start in range(0, len(kp) - w + 1, max(1, int(fps))):
        end = start + w
        if sc[start:end].mean() < min_score:
            continue
        in_win = ics[(ics >= start) & (ics < end)]
        if len(in_win) < window_s * 2:  # fewer than 2 steps/s is not running
            continue
        intervals = np.diff(in_win) / fps
        cv = float(intervals.std() / intervals.mean())
        drift = float(np.ptp(hip[start:end], axis=0).max() / np.median(leg[start:end]))
        if drift > 0.6:  # hip moved more than 60 % of a leg length: not steady
            continue
        if best is None or cv < best[1] - 1e-6 or (abs(cv - best[1]) < 1e-6 and start > best[0]):
            best = (start, cv)
    return best


def run_pose(frames, model: str, device: str, fps: float):
    """Return keypoints (N, 13, 2) in pixels and scores (N, 13)."""


def probe(path: Path):
    """Container fps, frame count, width, height and the camera's capture fps if the
    phone recorded in slow motion (Android writes com.android.capture.fps)."""
    cap = cv2.VideoCapture(str(path))
    fps, n, w, h = cap.get(cv2.CAP_PROP_FPS), int(cap.get(cv2.CAP_PROP_FRAME_COUNT)), int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    capture_fps = None
    try:
        import subprocess

        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format_tags=com.android.capture.fps", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True,
        ).stdout.strip()
        capture_fps = float(out) if out else None
    except (FileNotFoundError, ValueError):
        pass
    return fps, n, w, h, capture_fps


DET_EVERY = 8  # frames between person detections; in between, the previous pose's box is reused


POSE_MODE = "performance"  # rtmlib preset: lightweight | balanced | performance


def run_pose(frames, model: str, device: str, fps: float, det_every: int = DET_EVERY):
    """Return keypoints (N, 13, 2) in pixels and scores (N, 13)."""
    if model == "rtmpose":
        return _run_rtmpose(frames, device, det_every)
    if model == "mediapipe":
        return _run_mediapipe(frames, fps)
    raise ValueError(model)


def _select(kp, sc, index_map):
    idx = index_map["L"] + index_map["R"] + [index_map["nose"]]
    return kp[idx], sc[idx]


def _run_rtmpose(frames, device, det_every):
    import onnxruntime as ort
    from rtmlib import BodyWithFeet, PoseTracker

    if hasattr(ort, "preload_dlls"):
        ort.preload_dlls()
    # The detector (YOLOX-x) costs more than the pose model itself; running it
    # every det_every frames and reusing the last pose's bounding box in between
    # is safe on a treadmill, where the runner barely moves in the frame.
    model = PoseTracker(BodyWithFeet, det_frequency=det_every, tracking=False, mode=POSE_MODE, backend="onnxruntime", device=device)
    kps, scs = [], []
    prev_hip, prev_height = None, None
    for frame in frames:
        kp, sc = model(frame)
        if len(kp) == 0:
            kps.append(np.full((13, 2), np.nan))
            scs.append(np.zeros(13))
            model.frame_cnt = 0  # nobody found: detect again on the next frame
            continue
        # The runner is the largest person in frame; once found, follow the
        # person whose hip stays closest to the previous frame's hip.
        hips = (kp[:, 11] + kp[:, 12]) / 2
        heights = kp[:, :, 1].max(axis=1) - kp[:, :, 1].min(axis=1)
        largest = int(np.argmax(heights))
        if prev_hip is None:
            best = largest
        else:
            best = int(np.argmin(np.linalg.norm(hips - prev_hip, axis=1)))
            # If the runner was not in frame yet, we may have locked onto a
            # bystander: switch when someone clearly bigger appears.
            if heights[largest] > 1.5 * heights[best]:
                best = largest
        # Between detections the box comes from the previous pose, so a wrong pose
        # grows a wrong box and the next pose drifts further. Break the loop: when
        # the pose looks suspicious, run the detector again on the next frame.
        suspicious = sc[best].mean() < 0.5 or (prev_height is not None and abs(heights[best] - prev_height) > 0.25 * prev_height)
        if suspicious:
            model.frame_cnt = 0
        prev_hip, prev_height = hips[best], heights[best]
        k, s = _select(kp[best], sc[best], HALPE26)
        kps.append(k)
        scs.append(s)
    return np.array(kps), np.array(scs)


def _run_mediapipe(frames, fps):
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision

    opts = vision.PoseLandmarkerOptions(
        base_options=BaseOptions(
            model_asset_path=str(Path(__file__).parent / "models/pose_landmarker_heavy.task")
        ),
        running_mode=vision.RunningMode.VIDEO,
    )
    landmarker = vision.PoseLandmarker.create_from_options(opts)
    kps, scs = [], []
    for i, frame in enumerate(frames):
        h, w = frame.shape[:2]
        img = mp.Image(image_format=mp.ImageFormat.SRGB, data=cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
        res = landmarker.detect_for_video(img, int(i * 1000 / fps))
        if not res.pose_landmarks:
            kps.append(np.full((13, 2), np.nan))
            scs.append(np.zeros(13))
            continue
        lm = res.pose_landmarks[0]
        kp = np.array([[p.x * w, p.y * h] for p in lm])
        # MediaPipe exposes visibility (0-1) rather than a detection score.
        sc = np.array([p.visibility for p in lm])
        k, s = _select(kp, sc, MEDIAPIPE)
        kps.append(k)
        scs.append(s)
    landmarker.close()
    return np.array(kps), np.array(scs)


# ------------------------------------------------------------------ filtering


def camera_roll(path: Path, kp: np.ndarray, sc: np.ndarray, samples: int = 15, below: float = 0.6) -> float | None:
    """Camera roll in degrees (positive = the scene's horizontal slopes down to the right of the image),
    from the treadmill deck edge just below the feet. The background is the median of frames spread over
    the clip, so the runner disappears; long near-horizontal lines in a band around the feet's lowest
    position are the deck edges. None when no such line is found.

    Absolute angles (trunk lean, tibia and foot angle, thigh vs vertical) are measured against the image
    axes, so a phone tilted by a couple of degrees shifts them by as much."""
    cap = cv2.VideoCapture(str(path))
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    frames = []
    for i in np.linspace(0.1 * n, 0.9 * n, samples).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))  # exact frame does not matter for a background
        ok, f = cap.read()
        if ok:
            frames.append(f)
    cap.release()
    return roll_from_frames(frames, kp, sc, below=below)


def roll_from_frames(frames: list[np.ndarray], kp: np.ndarray, sc: np.ndarray, below: float = 0.6, max_deg: float = 8.0) -> float | None:
    """camera_roll() on frames already in memory (BGR); kp/sc are any keypoints of the runner in the clip."""
    if len(frames) < 5:
        return None
    gray = [cv2.cvtColor(f, cv2.COLOR_BGR2GRAY) if f.ndim == 3 else f for f in frames]
    bg = np.median(np.array(gray), axis=0).astype(np.uint8)
    h, w = bg.shape
    j = {nm: i for i, nm in enumerate(NAMES)}
    feet = np.concatenate([kp[:, j[f"{p}_{s}"], 1] for p in ("heel", "toe") for s in SIDES])
    good = np.concatenate([sc[:, j[f"{p}_{s}"]] for p in ("heel", "toe") for s in SIDES]) > 0.5
    if good.sum() < 4:
        return None
    floor = float(np.percentile(feet[good], 95))
    leg = float(np.nanmedian(np.linalg.norm(kp[:, j["hip_L"]] - kp[:, j["ankle_L"]], axis=1)))
    # From the side the deck edge is right under the feet; from behind the deck's rear end is further
    # down the image (`below`, in leg lengths).
    y0, y1 = int(max(0, floor - 0.25 * leg)), int(min(h, floor + below * leg))
    if y1 - y0 < 10:
        return None
    edges = cv2.Canny(cv2.GaussianBlur(bg[y0:y1], (5, 5), 0), 40, 120)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 720, threshold=80, minLineLength=int(0.2 * w), maxLineGap=12)
    if lines is None:
        return None
    angles, weights = [], []
    for x0, ya, x1, yb in lines.reshape(-1, 4):
        a = np.degrees(np.arctan2(yb - ya, x1 - x0))
        if abs(a) < max_deg:
            angles.append(a)
            weights.append(np.hypot(x1 - x0, yb - ya))
    if not angles:
        return None
    order = np.argsort(angles)
    cum = np.cumsum(np.array(weights)[order])
    return float(np.array(angles)[order][np.searchsorted(cum, cum[-1] / 2)])  # length-weighted median


def level(kp: np.ndarray, roll_deg: float | None, width: int, height: int) -> np.ndarray:
    """Rotate keypoints about the image centre so the scene's horizontal is horizontal again."""
    if not roll_deg:
        return kp
    t = np.radians(-roll_deg)
    c = np.array([width / 2, height / 2])
    rot = np.array([[np.cos(t), -np.sin(t)], [np.sin(t), np.cos(t)]])
    return (kp - c) @ rot.T + c


MAX_SEGMENT_DEVIATION = 0.35  # a thigh or shank longer/shorter than this fraction of its median is a mis-detection


def implausible_legs(kp: np.ndarray) -> np.ndarray:
    """Boolean (N, 13) mask of leg joints whose thigh or shank length is implausible in that frame.
    Limb lengths are constant, so a frame where a segment stretches by a third is a wrong pose
    (typically the model confidently placing a foot on a bystander or the treadmill frame)."""
    j = {n: i for i, n in enumerate(NAMES)}
    bad = np.zeros(kp.shape[:2], dtype=bool)
    for s in SIDES:
        thigh = np.linalg.norm(kp[:, j[f"hip_{s}"]] - kp[:, j[f"knee_{s}"]], axis=1)
        shank = np.linalg.norm(kp[:, j[f"knee_{s}"]] - kp[:, j[f"ankle_{s}"]], axis=1)
        for seg in (thigh, shank):
            med = np.nanmedian(seg)
            if not np.isfinite(med) or med == 0:
                continue
            wrong = np.abs(seg - med) > MAX_SEGMENT_DEVIATION * med
            for n in ("knee", "ankle", "heel", "toe"):
                bad[wrong, j[f"{n}_{s}"]] = True
        # The foot is rigid too: a heel or toe drifting off the shoe (fast swing with motion blur,
        # or the foot hidden behind the treadmill frame) stretches ankle-heel or heel-toe.
        ankle_heel = np.linalg.norm(kp[:, j[f"ankle_{s}"]] - kp[:, j[f"heel_{s}"]], axis=1)
        heel_toe = np.linalg.norm(kp[:, j[f"heel_{s}"]] - kp[:, j[f"toe_{s}"]], axis=1)
        for seg, joints in ((ankle_heel, ("heel",)), (heel_toe, ("heel", "toe"))):
            med = np.nanmedian(seg)
            if not np.isfinite(med) or med == 0:
                continue
            wrong = np.abs(seg - med) > MAX_SEGMENT_DEVIATION * med
            for n in joints:
                bad[wrong, j[f"{n}_{s}"]] = True
    return bad


def missing_mask(kp: np.ndarray, sc: np.ndarray) -> np.ndarray:
    """Boolean (N, J) mask of keypoints clean() discards: low score or implausible limb geometry."""
    bad = sc < MIN_SCORE
    if kp.shape[1] == len(NAMES) and kp.shape[2] == 2:
        bad = bad | implausible_legs(np.where(bad[..., None], np.nan, kp))
    return bad


def clean(kp: np.ndarray, sc: np.ndarray, fps: float, cutoff_hz: float = 8.0):
    """Drop low-confidence and implausible keypoints, interpolate them, then low-pass filter each trajectory."""
    out = kp.copy()
    out[missing_mask(kp, sc)] = np.nan
    n = len(out)
    t = np.arange(n)
    for j in range(out.shape[1]):
        for axis in range(out.shape[2]):
            y = out[:, j, axis]
            ok = ~np.isnan(y)
            if ok.sum() < 2:
                continue
            out[:, j, axis] = np.interp(t, t[ok], y[ok])
    b, a = butter(4, cutoff_hz / (fps / 2), btype="low")
    return filtfilt(b, a, out, axis=0)


# ---------------------------------------------------------------- gait events


@dataclass
class Events:
    direction: int  # +1 runner faces right in the image, -1 faces left
    ic: dict[str, np.ndarray]  # initial contact frames per side
    to: dict[str, np.ndarray]  # toe-off frames per side


def detect_events(kp: np.ndarray, fps: float) -> Events:
    j = {n: i for i, n in enumerate(NAMES)}
    hip = (kp[:, j["hip_L"]] + kp[:, j["hip_R"]]) / 2
    direction = int(np.sign(np.nanmean(kp[:, j["nose"], 0] - hip[:, 0]))) or 1
    min_gap = int(0.45 * fps)  # strides last > 0.5 s even at very high cadence
    ic, to = {}, {}
    def spread(x):
        # Robust range: a few bad frames must not inflate the prominence threshold.
        return float(np.percentile(x, 95) - np.percentile(x, 5))

    for s in SIDES:
        heel_rel = direction * (kp[:, j[f"heel_{s}"], 0] - hip[:, 0])
        toe_rel = direction * (kp[:, j[f"toe_{s}"], 0] - hip[:, 0])
        ic[s], _ = find_peaks(heel_rel, distance=min_gap, prominence=spread(heel_rel) * 0.3)
        to_zeni, _ = find_peaks(-toe_rel, distance=min_gap, prominence=spread(toe_rel) * 0.3)
        # Zeni's toe-off (toe furthest behind the hip) is late for running: the
        # foot keeps trailing back after it leaves the ground. Refine it to the
        # frame where the toe starts lifting, i.e. its upward velocity first
        # reaches 30% of the cycle's peak, searching between the previous
        # initial contact and the Zeni candidate.
        toe_up = -np.gradient(kp[:, j[f"toe_{s}"], 1]) * fps
        refined = []
        for t in to_zeni:
            prior = ic[s][ic[s] < t]
            if len(prior) == 0:
                continue
            a = int(prior[-1])
            seg = toe_up[a : t + 1]
            if seg.max() <= 0:
                refined.append(t)
                continue
            refined.append(a + int(np.argmax(seg >= 0.3 * seg.max())))
        to[s] = np.array(refined, dtype=int)
    return Events(direction, ic, to)


# -------------------------------------------------------------------- metrics


def angle_deg(a, b, c):
    """Interior angle at b (degrees) for points a-b-c."""
    v1, v2 = a - b, c - b
    cos = np.sum(v1 * v2, axis=-1) / (np.linalg.norm(v1, axis=-1) * np.linalg.norm(v2, axis=-1))
    return np.degrees(np.arccos(np.clip(cos, -1, 1)))


def segment_lean_deg(top, bottom, direction):
    """Signed angle of segment bottom->top from vertical; positive = top leans forward."""
    dx = direction * (top[..., 0] - bottom[..., 0])
    dy = bottom[..., 1] - top[..., 1]  # image y grows downward
    return np.degrees(np.arctan2(dx, dy))


def summarize(values, scores, label, unit, n_min=MIN_CYCLES):
    values = np.asarray(values, dtype=float)
    values = values[~np.isnan(values)]
    reliable = len(values) >= n_min and float(np.mean(scores)) >= 0.5
    return {
        "label": label,
        "unit": unit,
        "mean": round(float(values.mean()), 2) if len(values) else None,
        "sd": round(float(values.std()), 2) if len(values) else None,
        "n": int(len(values)),
        "mean_score": round(float(np.mean(scores)), 2),
        "state": "measured" if reliable else "unmeasurable",
    }


def compute_metrics(kp, sc, ev: Events, fps, speed_kmh, height_cm):
    j = {n: i for i, n in enumerate(NAMES)}
    d = ev.direction
    hip = (kp[:, j["hip_L"]] + kp[:, j["hip_R"]]) / 2
    head = kp[:, j["nose"]]
    shoulder = (kp[:, j["shoulder_L"]] + kp[:, j["shoulder_R"]]) / 2
    speed_ms = speed_kmh / 3.6

    # Pixel scale from leg length (thigh + shank), median over the video.
    leg_px = []
    for s in SIDES:
        thigh = np.linalg.norm(kp[:, j[f"hip_{s}"]] - kp[:, j[f"knee_{s}"]], axis=1)
        shank = np.linalg.norm(kp[:, j[f"knee_{s}"]] - kp[:, j[f"ankle_{s}"]], axis=1)
        leg_px.append(np.median(thigh + shank))
    cm_per_px = (height_cm * LEG_LENGTH_RATIO) / float(np.max(leg_px))

    # Cadence from all initial contacts, both feet.
    all_ic = np.sort(np.concatenate([ev.ic["L"], ev.ic["R"]]))
    step_intervals = np.diff(all_ic) / fps
    cadence = 60.0 / step_intervals
    metrics = {
        "cadence": summarize(cadence, sc[all_ic].mean(axis=1), "Cadence", "steps/min"),
        "step_length": summarize(speed_ms * step_intervals * 100, sc[all_ic].mean(axis=1), "Step length (from speed and cadence)", "cm"),
    }

    per_side = {k: {"L": [], "R": []} for k in [
        "contact_time", "flight_time", "knee_flexion_ic", "tibia_angle_ic", "foot_angle_ic",
        "overstride", "trunk_lean_midstance", "vertical_oscillation",
    ]}
    side_scores = {"L": [], "R": []}
    for s in SIDES:
        H, K, A, He, T = (kp[:, j[f"{n}_{s}"]] for n in ["hip", "knee", "ankle", "heel", "toe"])
        for i, f in enumerate(ev.ic[s]):
            later_to = ev.to[s][ev.to[s] > f]
            next_ic = ev.ic[s][ev.ic[s] > f]
            if len(later_to) == 0 or len(next_ic) == 0:
                continue
            t_off, f_next = later_to[0], next_ic[0]
            if t_off >= f_next:
                continue
            side_scores[s].append(sc[f, [j[f"hip_{s}"], j[f"knee_{s}"], j[f"ankle_{s}"], j[f"heel_{s}"], j[f"toe_{s}"]]].mean())
            per_side["contact_time"][s].append((t_off - f) / fps * 1000)
            # Flight = this foot's toe-off to the other foot's next contact.
            other = ev.ic["R" if s == "L" else "L"]
            nxt = other[(other > t_off) & (other < f_next)]
            if len(nxt):
                per_side["flight_time"][s].append((nxt[0] - t_off) / fps * 1000)
            per_side["knee_flexion_ic"][s].append(180 - angle_deg(H[f], K[f], A[f]))
            per_side["tibia_angle_ic"][s].append(segment_lean_deg(K[f], A[f], d))
            foot = T[f] - He[f]
            per_side["foot_angle_ic"][s].append(np.degrees(np.arctan2(-(foot[1]), d * foot[0])))
            per_side["overstride"][s].append(d * (A[f, 0] - hip[f, 0]) * cm_per_px)
            mid = (f + t_off) // 2
            per_side["trunk_lean_midstance"][s].append(segment_lean_deg(shoulder[mid], hip[mid], d))
            # The head, not the hips: the model's hip point follows the thigh and doubles the
            # oscillation (10-04 validation: hips 15–18 cm, head 8–9.5 cm, trunk is rigid).
            per_side["vertical_oscillation"][s].append(np.ptp(head[f:f_next, 1]) * cm_per_px)

    labels = {
        "contact_time": ("Ground contact time", "ms"),
        "flight_time": ("Flight time", "ms"),
        "knee_flexion_ic": ("Knee flexion at initial contact", "deg"),
        "tibia_angle_ic": ("Tibia angle at initial contact (+ = shank leaning forward)", "deg"),
        "foot_angle_ic": ("Foot angle at initial contact (+ = toe up, rearfoot)", "deg"),
        "overstride": ("Ankle ahead of hip at initial contact", "cm"),
        "trunk_lean_midstance": ("Trunk forward lean at midstance", "deg"),
        "vertical_oscillation": ("Vertical oscillation of the head", "cm"),
    }
    for key, (label, unit) in labels.items():
        for s in SIDES:
            metrics[f"{key}_{s}"] = summarize(per_side[key][s], side_scores[s] or [0], f"{label} ({s})", unit)

    # Foot strike pattern from the foot angle (Altman & Davis 2012 thresholds).
    fa = np.concatenate([per_side["foot_angle_ic"]["L"], per_side["foot_angle_ic"]["R"]])
    if len(fa):
        m = float(np.mean(fa))
        pattern = "rearfoot" if m > 8 else "forefoot" if m < -1.6 else "midfoot"
        metrics["foot_strike_pattern"] = {"label": "Foot strike pattern", "value": pattern, "mean_foot_angle_deg": round(m, 1), "state": "descriptor"}

    # The leg nearer the camera is tracked better; report which one it is.
    side_score = {s: float(np.mean(sc[:, [j[f"{n}_{s}"] for n in JOINTS]])) for s in SIDES}
    metrics["_info"] = {
        "cm_per_px": round(cm_per_px, 4),
        "direction": "right" if d > 0 else "left",
        "near_side": max(side_score, key=side_score.get),
        "side_scores": {s: round(v, 3) for s, v in side_score.items()},
        "initial_contact_frames": {s: ev.ic[s].tolist() for s in SIDES},
        "toe_off_frames": {s: ev.to[s].tolist() for s in SIDES},
        "mean_keypoint_score": round(float(sc.mean()), 3),
    }
    return metrics


# --------------------------------------------------------------------- output

BONES = [("shoulder", "hip"), ("hip", "knee"), ("knee", "ankle"), ("ankle", "heel"), ("heel", "toe"), ("ankle", "toe")]
COLORS = {"L": (0, 200, 255), "R": (255, 120, 0)}  # BGR


def write_overlay(frames, size, kp, sc, ev: Events, fps, path: Path):
    w, h = size
    # Play back at <= 60 fps so a 240 fps clip becomes a slow-motion overlay.
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), min(fps, 60), (w, h))
    j = {n: i for i, n in enumerate(NAMES)}
    ic_frames = {s: set(ev.ic[s].tolist()) for s in SIDES}
    to_frames = {s: set(ev.to[s].tolist()) for s in SIDES}
    for i, frame in enumerate(frames):
        if i >= len(kp):
            break
        img = frame.copy()
        for s in SIDES:
            for a, b in BONES:
                pa, pb = kp[i, j[f"{a}_{s}"]], kp[i, j[f"{b}_{s}"]]
                cv2.line(img, tuple(pa.astype(int)), tuple(pb.astype(int)), COLORS[s], 2)
            for n in JOINTS:
                p = kp[i, j[f"{n}_{s}"]]
                low = sc[i, j[f"{n}_{s}"]] < MIN_SCORE
                cv2.circle(img, tuple(p.astype(int)), 5, (0, 0, 255) if low else COLORS[s], -1)
            if i in ic_frames[s]:
                cv2.putText(img, f"IC {s}", (20, 40 + 30 * SIDES.index(s)), cv2.FONT_HERSHEY_SIMPLEX, 1, COLORS[s], 2)
            if i in to_frames[s]:
                cv2.putText(img, f"TO {s}", (150, 40 + 30 * SIDES.index(s)), cv2.FONT_HERSHEY_SIMPLEX, 1, COLORS[s], 2)
        cv2.putText(img, f"{i / fps:6.2f}s  f{i}", (w - 220, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        out.write(img)
    out.release()


def write_plots(kp, ev: Events, fps, path: Path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    j = {n: i for i, n in enumerate(NAMES)}
    t = np.arange(len(kp)) / fps
    fig, axes = plt.subplots(3, 1, figsize=(14, 9), sharex=True)
    for s in SIDES:
        H, K, A = kp[:, j[f"hip_{s}"]], kp[:, j[f"knee_{s}"]], kp[:, j[f"ankle_{s}"]]
        axes[0].plot(t, 180 - angle_deg(H, K, A), label=f"knee flexion {s}")
        hip = (kp[:, j["hip_L"]] + kp[:, j["hip_R"]]) / 2
        axes[1].plot(t, ev.direction * (kp[:, j[f"heel_{s}"], 0] - hip[:, 0]), label=f"heel-hip x {s}")
        for f in ev.ic[s]:
            axes[1].axvline(f / fps, color="g", alpha=0.3)
        for f in ev.to[s]:
            axes[1].axvline(f / fps, color="r", alpha=0.3)
    axes[2].plot(t, -((kp[:, j["hip_L"], 1] + kp[:, j["hip_R"], 1]) / 2), label="hip height (px)")
    axes[0].set_ylabel("deg")
    axes[1].set_ylabel("px (green=IC, red=TO)")
    axes[2].set_ylabel("px")
    axes[2].set_xlabel("s")
    for ax in axes:
        ax.legend(loc="upper right")
        ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=100)


def main():
    global POSE_MODE
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video", type=Path)
    p.add_argument("--speed-kmh", type=float, required=True)
    p.add_argument("--height-cm", type=float, required=True)
    p.add_argument("--model", choices=["rtmpose", "mediapipe"], default="rtmpose")
    p.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    p.add_argument("--out", type=Path, default=None, help="output dir (default: data/out/<video>_<model>)")
    p.add_argument("--start-seconds", type=float, default=0.0, help="skip the first N seconds of real time (camera setup, getting up to speed)")
    p.add_argument("--max-seconds", type=float, default=None, help="only analyze the first N seconds of real time (counted from the start of the file)")
    p.add_argument("--fps", type=float, default=None, help="real capture fps, overriding the container (for slow-motion clips)")
    p.add_argument("--reuse-pose", action="store_true", help="reuse keypoints.parquet from a previous run instead of rerunning pose estimation")
    p.add_argument("--auto-window", type=float, default=None, metavar="SECONDS", help="find the steadiest SECONDS of running automatically (coarse pose pass at ~30 fps first)")
    p.add_argument("--det-every", type=int, default=DET_EVERY, help="run the person detector every N frames (1 = every frame)")
    p.add_argument("--pose-mode", choices=["lightweight", "balanced", "performance"], default="performance", help="rtmlib model preset (size/accuracy trade-off)")
    args = p.parse_args()
    POSE_MODE = args.pose_mode

    out = args.out or Path(__file__).parent.parent / "data" / "out" / f"{args.video.stem}_{args.model}"
    out.mkdir(parents=True, exist_ok=True)

    container_fps, n_total, w, h, capture_fps = probe(args.video)
    # A slow-motion clip stores every captured frame but plays at 30 fps: the
    # real time between frames is 1 / capture fps, not 1 / container fps.
    fps = args.fps or (capture_fps if capture_fps and capture_fps > container_fps + 1 else container_fps)
    # The analysis window [start, end) in file frames; everything downstream
    # (keypoints, events, overlay) is indexed from `start`.
    start = int(args.start_seconds * fps)
    end = min(n_total, int(args.max_seconds * fps)) if args.max_seconds else n_total

    if args.auto_window:
        # Coarse pass: ~30 fps is enough to find the steady stretch, and costs
        # 1/8 of the full pass on a 240 fps clip.
        step = max(1, int(round(fps / 30)))
        coarse_fps = fps / step
        t0 = time.time()
        # Coarse frames are ~33 ms apart, so detect more often than in the full pass.
        kp_c, sc_c = run_pose(iter_frames(args.video, (end - start) // step, skip=start, step=step), args.model, args.device, coarse_fps, det_every=max(1, args.det_every // step))
        kp_c = clean(kp_c, sc_c, coarse_fps)
        found = find_steady_window(kp_c, sc_c, coarse_fps, args.auto_window)
        print(f"coarse pass: {len(kp_c)} frames at {coarse_fps:.0f} fps in {time.time() - t0:.0f}s")
        if found is None:
            sys.exit("no steady running window found: is the runner in frame and running for the whole window?")
        start = start + found[0] * step
        end = min(end, start + int(args.auto_window * fps))
        print(f"steady window: {start / fps:.1f}-{end / fps:.1f} s (step-interval CV {found[1]:.3f})")
    n = end - start
    print(f"frames {start}-{end} of {n_total}, {w}x{h}, container {container_fps:.1f} fps, using {fps:.0f} fps" + (f" (capture fps tag {capture_fps:.0f})" if capture_fps else ""))

    t0 = time.time()
    cached = out / "keypoints.parquet"
    if args.reuse_pose and cached.exists():
        df = pd.read_parquet(cached)
        df = df[(df.frame >= start) & (df.frame < end)]
        if df.frame.nunique() != n:
            sys.exit(f"cached keypoints cover frames {df.frame.min()}-{df.frame.max()}, not {start}-{end}: rerun without --reuse-pose")
        kp_raw = np.stack([df.pivot(index="frame", columns="joint", values=c)[NAMES].values for c in ("x_raw", "y_raw")], axis=-1)
        sc = df.pivot(index="frame", columns="joint", values="score")[NAMES].values
    else:
        kp_raw, sc = run_pose(iter_frames(args.video, n, skip=start), args.model, args.device, fps, det_every=args.det_every)
    n = len(kp_raw)
    pose_s = time.time() - t0
    print(f"pose: {pose_s:.1f}s ({pose_s / n * 1000:.0f} ms/frame), mean score {sc.mean():.2f}")

    kp = clean(kp_raw, sc, fps)
    ev = detect_events(kp, fps)
    print(f"events: IC L={len(ev.ic['L'])} R={len(ev.ic['R'])}, TO L={len(ev.to['L'])} R={len(ev.to['R'])}, facing {'right' if ev.direction > 0 else 'left'}")

    metrics = compute_metrics(kp, sc, ev, fps, args.speed_kmh, args.height_cm)
    # Event frames are reported as file frame numbers, so they can be looked up in the source video.
    metrics["_info"]["initial_contact_frames"] = {s: (ev.ic[s] + start).tolist() for s in SIDES}
    metrics["_info"]["toe_off_frames"] = {s: (ev.to[s] + start).tolist() for s in SIDES}
    metrics["_info"].update({"model": args.model, "fps": fps, "container_fps": container_fps, "start_frame": start, "frames": n, "pose_seconds": round(pose_s, 1)})
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))

    rows = []
    for i in range(len(kp)):
        for j_i, joint in enumerate(NAMES):
            rows.append((start + i, joint, kp_raw[i, j_i, 0], kp_raw[i, j_i, 1], kp[i, j_i, 0], kp[i, j_i, 1], sc[i, j_i]))
    pd.DataFrame(rows, columns=["frame", "joint", "x_raw", "y_raw", "x", "y", "score"]).to_parquet(out / "keypoints.parquet")

    write_overlay(iter_frames(args.video, n, skip=start), (w, h), kp, sc, ev, fps, out / "overlay.mp4")
    write_plots(kp, ev, fps, out / "plots.png")

    print(f"\nresults in {out}\n")
    for k, m in metrics.items():
        if k.startswith("_"):
            continue
        if m["state"] == "descriptor":
            print(f"  {m['label']:<55} {m['value']} ({m['mean_foot_angle_deg']} deg)")
        else:
            val = f"{m['mean']} ± {m['sd']} {m['unit']}" if m["mean"] is not None else "-"
            print(f"  {m['label']:<55} {val:<22} n={m['n']:<3} score={m['mean_score']}  {m['state']}")


if __name__ == "__main__":
    main()
