"""Adapter between the worker and the prototype scripts (prototype/analyze.py, analyze_rear.py).

Keeps the prototype's CLI untouched: the functions below call its building blocks directly.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import numpy as np
import onnxruntime as ort
import pandas as pd

# ONNX Runtime sizes its thread pool from the host's CPU count, which inside a
# container with a CPU quota means dozens of threads fighting for a few cores
# (measured: 20x slower). rtmlib does not expose session options, so inject them.
ORT_THREADS = int(os.environ.get("ORT_THREADS", "4"))
_InferenceSession = ort.InferenceSession


class _BoundedSession(_InferenceSession):
    def __init__(self, *args, **kwargs):
        if os.environ.get("PIPELINE_DEVICE", "cpu") == "cpu":
            so = kwargs.get("sess_options") or ort.SessionOptions()
            so.intra_op_num_threads = ORT_THREADS
            so.inter_op_num_threads = 1
            kwargs["sess_options"] = so
        super().__init__(*args, **kwargs)


ort.InferenceSession = _BoundedSession

import analyze as side  # noqa: E402  prototype/analyze.py
import analyze_rear as rear  # noqa: E402  prototype/analyze_rear.py

MIN_FPS = 60
MIN_SECONDS = {"side": 20, "rear": 6}  # keep equal to api/workload.py
WINDOW_SECONDS = 20
DEVICE = os.environ.get("PIPELINE_DEVICE", "cpu")  # cpu | cuda
if DEVICE == "cuda" and hasattr(ort, "preload_dlls"):
    ort.preload_dlls()  # finds the pip-installed CUDA libraries
# Frames above this rate are subsampled: on CPU every frame costs ~0.6 s, and 120 fps
# still times gait events to ±8 ms. The prototype at 240 fps is the accuracy reference.
MAX_FPS = float(os.environ.get("PIPELINE_MAX_FPS", "120"))
# Coarse pass (steady-window search) model and its cost relative to a full-pass frame.
COARSE_POSE_MODE = "balanced"
COARSE_COST = 0.2  # keep equal to api/workload.py
# Playback Video quality (docs/SPEC.md §11): CRF 23 is ~19 MB per 20 s of 1080p; 26 (~12 MB) was judged
# acceptable too, should storage need to shrink.
PLAYBACK_CRF = int(os.environ.get("PLAYBACK_CRF", "23"))


def planned_frames(view: str, total: int, fps: float) -> int:
    """Same arithmetic as the API's workload.planned_frames, with this module's constants."""
    sub = max(1, int(round(fps / MAX_FPS)))
    full = min(total, int(WINDOW_SECONDS * fps)) // sub
    if view == "side":
        step = max(1, int(round(fps / 30)))
        return int(total // step * COARSE_COST) + full
    return full


def rear_window(n_total: int, fps: float, sub: int) -> tuple[int, int]:
    """(first file frame, rows to analyse) for the rear view. A clip longer than the window starts with
    the runner getting on the belt and speeding up and ends with the slow-down, so take the middle
    (10-04: the first 20 s of a 99 s clip gave cadence 136 instead of 166). Short clips, the usual rear
    recording, are used whole."""
    n = min(n_total, int(WINDOW_SECONDS * fps)) // sub
    return max(0, (n_total - n * sub) // 2), n


def scoped_progress(progress, lo: float, hi: float):
    """Maps a 0-1 fraction reported by a pipeline step onto the [lo, hi] slice of the overall bar."""

    def report(msg: str, fraction: float | None = None, eta_seconds: float | None = None):
        progress(msg, pct=None if fraction is None else lo + fraction * (hi - lo), eta_seconds=eta_seconds)

    return report


def counting(frames, total: int, progress, label: str, lo: float, hi: float, remaining_after: float = 0.0):
    """Wraps a frame iterator: every 2 s reports the fraction done in [lo, hi] and an ETA from the
    measured rate (plus `remaining_after`, the estimated seconds for the steps that follow, as a
    multiple of this step's total duration)."""
    import time

    t0 = time.time()
    last = t0
    for i, frame in enumerate(frames, 1):
        now = time.time()
        if now - last >= 2 or i == total:
            rate = i / (now - t0)
            left_this = (total - i) / rate if rate else 0
            total_this = total / rate if rate else 0
            progress(f"{label} ({i}/{total} frames)", lo + (hi - lo) * i / total, left_this + remaining_after * total_this)
            last = now
        yield frame


class PlaybackWriter:
    """Writes the Playback Video (docs/SPEC.md §11, ADR 0008) from the frames the pose model sees: every
    analyzed frame once, in order, at a regular pace from time 0, upright, H.264. Row i of the keypoints
    is then frame i, shown at i / fps in any browser, whatever quirks the uploaded file had (edit lists,
    slow-motion gaps, dropped frames, HEVC)."""

    def __init__(self, path: Path, fps: float):
        self.path, self.fps, self.count, self.proc = path, fps, 0, None

    def tee(self, frames):
        for frame in frames:
            self._write(frame)
            yield frame

    def _write(self, frame: np.ndarray) -> None:
        if self.proc is None:
            h, w = frame.shape[:2]
            self.proc = subprocess.Popen(
                ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-framerate", f"{self.fps:.6f}", "-i", "-",
                 # 4:2:0 needs even sizes; padding right and bottom keeps the pixel coordinates.
                 "-vf", "pad=ceil(iw/2)*2:ceil(ih/2)*2", "-an", "-c:v", "libx264", "-preset", "medium", "-crf", str(PLAYBACK_CRF),
                 "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(self.path)],
                stdin=subprocess.PIPE,
            )
        self.proc.stdin.write(np.ascontiguousarray(frame).tobytes())
        self.count += 1

    def close(self) -> int:
        """Waits for the encoder; returns the number of frames written."""
        if self.proc is not None:
            self.proc.stdin.close()
            if self.proc.wait(timeout=600) != 0:
                raise RuntimeError(f"ffmpeg failed writing the Playback Video ({self.proc.returncode})")
        return self.count


def effective_fps(container_fps: float, capture_fps: float | None) -> float:
    return capture_fps if capture_fps and capture_fps > container_fps + 1 else container_fps


def check_video(path: Path, capture_fps_hint: float | None = None, view: str = "side") -> dict:
    """`capture_fps_hint` is what the browser read from the file; used when the tag
    did not survive a re-encode or an export from the phone's gallery."""
    container_fps, n_total, w, h, capture_fps = side.probe(path)
    capture_fps = capture_fps or capture_fps_hint
    fps = effective_fps(container_fps, capture_fps)
    duration = n_total / fps if fps else 0
    info = {"container_fps": container_fps, "capture_fps": capture_fps, "fps": fps, "frames": n_total, "duration_s": round(duration, 1), "width": w, "height": h}
    if fps < MIN_FPS:
        return {"passed": False, "reason": "fps_too_low", **info}
    if duration < MIN_SECONDS[view]:
        return {"passed": False, "reason": "too_short", **info}
    return {"passed": True, "reason": None, **info}


def analyze_side(path: Path, out: Path, speed_kmh: float, height_cm: float, progress, fps: float) -> dict:
    container_fps, n_total, w, h, _ = side.probe(path)
    step = max(1, int(round(fps / 30)))
    sub = max(1, int(round(fps / MAX_FPS)))
    n_coarse = n_total // step
    n_full = int(WINDOW_SECONDS * fps) // sub
    # The bar is split in proportion to the cost of the two passes.
    coarse_share = n_coarse * COARSE_COST / (n_coarse * COARSE_COST + n_full)
    progress("finding steady running (coarse pass)", 0.0)
    frames = counting(side.iter_frames(path, n_coarse, step=step), n_coarse, progress, "finding steady running", 0.0, coarse_share, remaining_after=n_full / n_coarse / COARSE_COST)
    # The coarse pass only needs cadence and the runner's position, so the mid-size
    # model is enough: ~10x cheaper than the preset used for the metrics.
    side.POSE_MODE = COARSE_POSE_MODE
    try:
        kp_c, sc_c = side.run_pose(frames, "rtmpose", DEVICE, fps / step, det_every=max(1, 8 // step))
    finally:
        side.POSE_MODE = "performance"
    kp_c = side.clean(kp_c, sc_c, fps / step)
    if sc_c.mean() < 0.3:
        raise_rejected("runner_not_found")
    found = side.find_steady_window(kp_c, sc_c, fps / step, WINDOW_SECONDS)
    if found is None:
        raise_rejected("no_steady_running")
    start = found[0] * step
    end = min(n_total, start + int(WINDOW_SECONDS * fps))
    # Full pass, subsampled to at most MAX_FPS.
    fps_eff = fps / sub
    n = (end - start) // sub

    playback = PlaybackWriter(out / "playback.mp4", fps_eff)
    frames = counting(side.iter_frames(path, n, skip=start, step=sub), n, progress, f"estimating pose at {fps_eff:.0f} fps", coarse_share, 0.98)
    kp_raw, sc = side.run_pose(playback.tee(frames), "rtmpose", DEVICE, fps_eff, det_every=max(1, 8 // sub))
    check_playback(playback.close(), len(kp_raw))
    # Metrics are computed on keypoints levelled for the camera roll (from the treadmill deck edge);
    # the browser gets image coordinates, so the skeleton stays on the video.
    roll = side.camera_roll(path, kp_raw, sc)
    kp_lev_raw = side.level(kp_raw, roll, w, h)
    kp = side.clean(kp_lev_raw, sc, fps_eff)
    discarded = side.missing_mask(kp_lev_raw, sc)  # points clean() replaced by interpolation
    progress("computing metrics", 0.98, 5)
    ev = side.detect_events(kp, fps_eff)
    metrics = side.compute_metrics(kp, sc, ev, fps_eff, speed_kmh, height_cm)
    info = metrics.pop("_info")
    info["initial_contact_frames"] = {s: (ev.ic[s] * sub + start).tolist() for s in side.SIDES}
    info["toe_off_frames"] = {s: (ev.to[s] * sub + start).tolist() for s in side.SIDES}

    info["camera_roll_deg"] = roll
    kp_img = side.level(kp, -roll if roll else None, w, h)  # back to image coordinates
    rows = [(start + i * sub, joint, kp_raw[i, j, 0], kp_raw[i, j, 1], kp_img[i, j, 0], kp_img[i, j, 1], sc[i, j]) for i in range(len(kp)) for j, joint in enumerate(side.NAMES)]
    pd.DataFrame(rows, columns=["frame", "joint", "x_raw", "y_raw", "x", "y", "score"]).to_parquet(out / "keypoints.parquet")
    (out / "metrics.json").write_text(json.dumps({**metrics, "_info": info}, indent=2, default=float))
    # The player draws points with score 0 in red: the discarded ones, so the viewer sees where the pose was not trusted.
    write_browser_keypoints(out / "keypoints.json", kp_img, np.where(discarded, 0.0, sc), side.NAMES, fps_eff, start, w, h, events={"ic": info["initial_contact_frames"], "to": info["toe_off_frames"]}, container_fps=container_fps, frame_step=sub, kp_raw=kp_raw, roll_deg=roll, playback=True)
    return {
        "metrics": metrics,
        "info": info,
        "frames_processed": int(n_coarse * COARSE_COST) + n,  # full-pass-equivalent frames, for the rate estimate
        "window": {"start_frame": int(start), "end_frame": int(end), "fps": fps_eff, "source_fps": fps, "frame_step": sub, "step_interval_cv": found[1]},
        "camera_check": {"near_side": info.get("near_side"), "mean_keypoint_score": info.get("mean_keypoint_score"), "discarded_frames": int(discarded.any(axis=1).sum()), "frames": int(n), "roll_deg": None if roll is None else round(roll, 2)},
    }


def analyze_rear(path: Path, out: Path, progress, fps: float) -> dict:
    container_fps, n_total, w, h, _ = rear.probe(path)
    sub = max(1, int(round(fps / MAX_FPS)))
    fps_eff = fps / sub
    start, n = rear_window(n_total, fps, sub)
    playback = PlaybackWriter(out / "playback.mp4", fps_eff)
    frames = counting(rear.iter_frames(path, n, skip=start, step=sub), n, progress, f"estimating pose on rear view at {fps_eff:.0f} fps", 0.0, 0.98)
    kp_raw, sc = rear.run_pose(playback.tee(frames), "rtmpose", DEVICE, fps_eff, det_every=max(1, 8 // sub))
    check_playback(playback.close(), len(kp_raw))
    roll = side.camera_roll(path, kp_raw, sc, below=1.6)  # hip adduction is measured against the vertical
    kp = rear.clean(side.level(kp_raw, roll, w, h), sc, fps_eff)
    # Only the stretch of steady running: stepping on/off the belt or leaving the frame would
    # distort the stance detection (it is percentile-based).
    a, b = rear.running_segment(kp, sc, fps_eff)
    metrics, info, _ = rear.compute(kp[a:b], sc[a:b], fps_eff)
    for s in rear.SIDES:
        info[f"stance_windows_{s}"] = [(start + (x + a) * sub, start + (y + a) * sub) for x, y in info[f"stance_windows_{s}"]]
    info["running_segment_frames"] = [start + a * sub, start + b * sub]
    kp_img = side.level(kp, -roll if roll else None, w, h)
    rows = [(start + i * sub, joint, kp_raw[i, j, 0], kp_raw[i, j, 1], kp_img[i, j, 0], kp_img[i, j, 1], sc[i, j]) for i in range(len(kp)) for j, joint in enumerate(rear.NAMES)]
    pd.DataFrame(rows, columns=["frame", "joint", "x_raw", "y_raw", "x", "y", "score"]).to_parquet(out / "keypoints.parquet")
    write_browser_keypoints(out / "keypoints.json", kp_img, sc, rear.NAMES, fps_eff, start, w, h, events={"stance": {s: info[f"stance_windows_{s}"] for s in rear.SIDES}}, container_fps=container_fps, frame_step=sub, kp_raw=kp_raw, roll_deg=roll, playback=True)
    return {
        "metrics": metrics,
        "info": info,
        "frames_processed": n,
        "window": {"start_frame": int(start), "end_frame": int(start + n * sub), "fps": fps_eff, "source_fps": fps, "frame_step": sub},
        "camera_check": {"pelvis_baseline_deg": info.get("pelvis_baseline_deg"), "mean_keypoint_score": info.get("mean_keypoint_score"), "roll_deg": None if roll is None else round(roll, 2)},
    }


def check_playback(written: int, rows: int) -> None:
    if written != rows:
        raise RuntimeError(f"Playback Video has {written} frames for {rows} keypoint rows")


def write_browser_keypoints(path: Path, kp, sc, names, fps, start_frame, width, height, events, container_fps, frame_step=1, kp_raw=None, roll_deg=None, playback=False) -> None:
    """Compact JSON the web player draws from: one row per analyzed frame, [x, y, score] per joint, in pixels.
    Row i is file frame start_frame + i * frame_step of the uploaded Video (events use these numbers).
    With `playback` the player shows the Playback Video, where row i is frame i at time i / fps (older
    analyses played the uploaded file and carry the container time of each row in `times`).
    `frames` are the cleaned (filtered) points the metrics use; `frames_raw` are the model's output, so
    the viewer can tell model error from filter error."""

    def rows(points):
        arr = np.concatenate([np.round(points, 1), np.round(sc, 2)[..., None]], axis=-1).astype(object)
        arr[np.isnan(arr.astype(float))] = None  # JSON has no NaN
        return arr.tolist()

    doc = {
        "fps": fps, "container_fps": container_fps, "start_frame": int(start_frame), "frame_step": int(frame_step), "width": width, "height": height,
        "joints": list(names), "frames": rows(kp), "events": events,
        # Camera roll the metrics were corrected for: the player measures its angles against the
        # scene's horizontal, not the image's, so they match the Metric cards.
        "roll_deg": roll_deg,
    }
    if playback:
        doc["playback"] = True
    if kp_raw is not None:
        doc["frames_raw"] = rows(kp_raw)
    path.write_text(json.dumps(doc, separators=(",", ":")))


def raise_rejected(reason: str):
    from .jobs import VideoRejected

    raise VideoRejected(reason)
