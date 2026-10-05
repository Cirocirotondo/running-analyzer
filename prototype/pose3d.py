"""Experiment: 3D pose (RTMW3D via rtmlib) vs 2D pose on the same clip.

RTMW3D gives, per keypoint, image x/y in pixels plus a root-relative depth z in
metres. To measure angles in 3D the pixel axes must be in metres too, so we
solve for one scale s (m/px, constant because the camera is fixed) that makes
the thigh and shank lengths as constant as possible over time, then compare the
knee angle computed in 3D with the 2D one at the same frames.

Usage:
    uv run pose3d.py VIDEO --start-seconds 9 --max-seconds 20 [--fps 240] [--device cuda]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from analyze import angle_deg, clean, iter_frames, probe  # noqa: E402

# COCO-WholeBody (133) indices for the joints we use.
WB = {
    "shoulder_L": 5, "hip_L": 11, "knee_L": 13, "ankle_L": 15, "heel_L": 19, "toe_L": 17,
    "shoulder_R": 6, "hip_R": 12, "knee_R": 14, "ankle_R": 16, "heel_R": 22, "toe_R": 20,
    "nose": 0,
}
NAMES = list(WB)


def run_3d(video: Path, start: int, n: int, device: str):
    import onnxruntime as ort
    from rtmlib import Wholebody3d

    if hasattr(ort, "preload_dlls"):
        ort.preload_dlls()
    model = Wholebody3d(mode="balanced", backend="onnxruntime", device=device)
    rows = []
    prev_hip = None
    for i, frame in enumerate(iter_frames(video, start + n)):
        if i < start:
            continue
        kp3, sc, _, kp2 = model(frame)
        if len(kp3) == 0:
            continue
        heights = kp2[:, :, 1].max(axis=1) - kp2[:, :, 1].min(axis=1)
        hips = (kp2[:, 11] + kp2[:, 12]) / 2
        largest = int(np.argmax(heights))
        best = largest if prev_hip is None else int(np.argmin(np.linalg.norm(hips - prev_hip, axis=1)))
        if heights[largest] > 1.5 * heights[best]:
            best = largest
        prev_hip = hips[best]
        for name, idx in WB.items():
            rows.append((i, name, kp2[best, idx, 0], kp2[best, idx, 1], kp3[best, idx, 2], sc[best, idx]))
    return pd.DataFrame(rows, columns=["frame", "joint", "x", "y", "z", "score"])


def to_arrays(df: pd.DataFrame):
    frames = np.sort(df.frame.unique())
    piv = lambda c: df.pivot(index="frame", columns="joint", values=c).reindex(frames)[NAMES].values
    return frames, np.stack([piv("x"), piv("y"), piv("z")], axis=-1), piv("score")


def solve_scale(p: np.ndarray, j: dict) -> float:
    """m/px that makes thigh and shank lengths most constant over time (in 3D)."""
    segs = [(j["hip_L"], j["knee_L"]), (j["knee_L"], j["ankle_L"]), (j["hip_R"], j["knee_R"]), (j["knee_R"], j["ankle_R"])]
    best, best_cv = None, np.inf
    for s in np.linspace(0.0005, 0.01, 400):
        cv = 0.0
        for a, b in segs:
            d = p[:, a] - p[:, b]
            L = np.sqrt((s * d[:, 0]) ** 2 + (s * d[:, 1]) ** 2 + d[:, 2] ** 2)
            cv += L.std() / L.mean()
        if cv < best_cv:
            best, best_cv = s, cv
    return float(best), float(best_cv / len(segs))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("video", type=Path)
    ap.add_argument("--start-seconds", type=float, default=0.0)
    ap.add_argument("--max-seconds", type=float, required=True, help="end of the window, counted from the start of the file")
    ap.add_argument("--fps", type=float, default=None)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--height-cm", type=float, default=None, help="runner height, to check the solved scale against 0.49 x height")
    ap.add_argument("--reuse", action="store_true")
    args = ap.parse_args()

    out = Path(__file__).parent.parent / "data" / "out" / f"{args.video.stem}_3d"
    out.mkdir(parents=True, exist_ok=True)
    container_fps, n_total, w, h, capture_fps = probe(args.video)
    fps = args.fps or (capture_fps if capture_fps and capture_fps > container_fps + 1 else container_fps)
    start, end = int(args.start_seconds * fps), min(n_total, int(args.max_seconds * fps))

    cached = out / "keypoints3d.parquet"
    if args.reuse and cached.exists():
        df = pd.read_parquet(cached)
    else:
        t0 = time.time()
        df = run_3d(args.video, start, end - start, args.device)
        print(f"3d pose: {time.time() - t0:.0f}s for {end - start} frames")
        df.to_parquet(cached)

    frames, p, sc = to_arrays(df)
    j = {n: i for i, n in enumerate(NAMES)}
    # Smooth x, y, z with the same filter as the 2D pipeline (scores gate x/y and z alike).
    p_s = np.concatenate([clean(p[:, :, :2], sc, fps), clean(p[:, :, 2:], sc, fps)], axis=-1)

    s, cv = solve_scale(p_s, j)
    leg = []
    for side in "LR":
        d1, d2 = p_s[:, j[f"hip_{side}"]] - p_s[:, j[f"knee_{side}"]], p_s[:, j[f"knee_{side}"]] - p_s[:, j[f"ankle_{side}"]]
        L = lambda d: np.sqrt((s * d[:, 0]) ** 2 + (s * d[:, 1]) ** 2 + d[:, 2] ** 2)
        leg.append(float(np.median(L(d1) + L(d2))))
    print(f"scale {s * 100:.3f} cm/px (segment length CV {cv:.3f}); 3D leg length L={leg[0] * 100:.1f} cm R={leg[1] * 100:.1f} cm"
          + (f"; expected ~{0.49 * args.height_cm:.1f} cm from height" if args.height_cm else ""))

    metric = p_s.copy()
    metric[:, :, :2] *= s
    res = {"scale_m_per_px": s, "segment_cv": cv, "leg_length_m": leg, "frames": [int(frames[0]), int(frames[-1])], "fps": fps}
    for side in "LR":
        H, K, A = (metric[:, j[f"{n}_{side}"]] for n in ("hip", "knee", "ankle"))
        knee3d = 180 - angle_deg(H, K, A)
        H2, K2, A2 = (p_s[:, j[f"{n}_{side}"], :2] for n in ("hip", "knee", "ankle"))
        knee2d = 180 - angle_deg(H2, K2, A2)
        res[f"knee_{side}"] = {"3d_mean": float(knee3d.mean()), "2d_mean": float(knee2d.mean()), "3d_range": [float(knee3d.min()), float(knee3d.max())], "2d_range": [float(knee2d.min()), float(knee2d.max())]}
        pd.DataFrame({"frame": frames, "knee3d": knee3d, "knee2d": knee2d}).to_parquet(out / f"knee_{side}.parquet")
    # Trunk lean in 3D vs 2D (shoulder-hip segment from vertical, sagittal component).
    (out / "summary.json").write_text(json.dumps(res, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
