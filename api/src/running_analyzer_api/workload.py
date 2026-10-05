"""How much pose-estimation work a Session needs, in frames, mirroring worker/pipeline.py.

Side view: a coarse pass at ~30 fps over the whole clip to find the steady stretch, then the full pass
at <= MAX_FPS over a WINDOW_SECONDS window. Rear view: only the full pass over the first window.
Keep these constants equal to the worker's.
"""

from __future__ import annotations

COARSE_FPS = 30.0
MAX_FPS = 120.0
WINDOW_SECONDS = 20.0
MIN_FPS = 60.0
# Minimum real duration per View. The rear view needs only a few gait cycles for its peak-based
# metrics; 6 s is provisional until rear-view validation says otherwise.
MIN_SECONDS = {"side": 20.0, "rear": 6.0}


def family(view_or_slot: str) -> str:
    """"side" for any side slot or Side View (side_a, side_b, left_side, right_side, side), else "rear"."""
    return "rear" if view_or_slot == "rear" else "side"
DEFAULT_SECONDS_PER_FRAME = 0.6  # 4-CPU container, RTMPose performance preset (prototype/EXPERIMENTS.md)
FIXED_OVERHEAD_SECONDS = 60.0  # download, checks, uploads, bookkeeping


def effective_fps(container_fps: float | None, capture_fps: float | None) -> float:
    container_fps = container_fps or 30.0
    return capture_fps if capture_fps and capture_fps > container_fps + 1 else container_fps


COARSE_COST = 0.2  # a coarse-pass frame (smaller model) relative to a full-pass frame; keep equal to the worker's


def planned_frames(view: str, total_frames: int, fps: float) -> int:
    """Full-pass-equivalent frames."""
    sub = max(1, round(fps / MAX_FPS))
    full = min(total_frames, int(WINDOW_SECONDS * fps)) // sub
    if view == "side":
        step = max(1, round(fps / COARSE_FPS))
        return int(total_frames // step * COARSE_COST) + full
    return full


def estimate_seconds(frames: int, seconds_per_frame: float) -> float:
    return FIXED_OVERHEAD_SECONDS + frames * seconds_per_frame
