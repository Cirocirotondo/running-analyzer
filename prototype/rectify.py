"""Experiment: undo the camera tilt using the runner as the calibration object.

The runner's thigh and shank have constant lengths, and in a side view they move
in one vertical plane. A camera that is not perpendicular to that plane (too
low, or angled) makes those lengths vary with position in the frame. We fit a
rectifying homography H = K R K^-1 (focal length f, tilt, pan) that makes the
2D segment lengths as constant as possible across all frames, then recompute
the angles on the rectified keypoints.

Usage:
    uv run rectify.py data/out/<video>_rtmpose --start-seconds 9 --fps 240
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.optimize import minimize

sys.path.insert(0, str(Path(__file__).parent))
from analyze import NAMES, SIDES, angle_deg, clean, segment_lean_deg  # noqa: E402


def homography(f, tilt, pan, cx, cy):
    K = np.array([[f, 0, cx], [0, f, cy], [0, 0, 1.0]])
    ct, st, cp, sp = np.cos(tilt), np.sin(tilt), np.cos(pan), np.sin(pan)
    Rx = np.array([[1, 0, 0], [0, ct, -st], [0, st, ct]])
    Ry = np.array([[cp, 0, sp], [0, 1, 0], [-sp, 0, cp]])
    return K @ (Ry @ Rx) @ np.linalg.inv(K)


def apply(H, pts):
    """pts (..., 2) -> rectified (..., 2)."""
    p = np.concatenate([pts, np.ones(pts.shape[:-1] + (1,))], axis=-1) @ H.T
    return p[..., :2] / p[..., 2:3]


def segment_cv(pts, j):
    segs = [(f"hip_{s}", f"knee_{s}") for s in SIDES] + [(f"knee_{s}", f"ankle_{s}") for s in SIDES]
    cv = []
    for a, b in segs:
        L = np.linalg.norm(pts[:, j[a]] - pts[:, j[b]], axis=1)
        cv.append(L.std() / L.mean())
    return float(np.mean(cv))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir", type=Path, help="output dir of analyze.py (has keypoints.parquet and metrics.json)")
    ap.add_argument("--start-seconds", type=float, default=0.0)
    ap.add_argument("--fps", type=float, required=True)
    ap.add_argument("--width", type=int, default=1080)
    ap.add_argument("--height", type=int, default=1920)
    args = ap.parse_args()

    df = pd.read_parquet(args.run_dir / "keypoints.parquet")
    piv = lambda c: df.pivot(index="frame", columns="joint", values=c)[NAMES].values
    kp_raw, sc = np.stack([piv("x_raw"), piv("y_raw")], axis=-1), piv("score")
    kp = clean(kp_raw, sc, args.fps)
    start = int(args.start_seconds * args.fps)
    kp, sc = kp[start:], sc[start:]
    info = json.loads((args.run_dir / "metrics.json").read_text())["_info"]
    j = {n: i for i, n in enumerate(NAMES)}
    cx, cy = args.width / 2, args.height / 2
    d = 1 if info["direction"] == "right" else -1

    cv0 = segment_cv(kp, j)

    def loss(x):
        f, tilt, pan = x
        if f < 300:
            return 10.0
        return segment_cv(apply(homography(f, tilt, pan, cx, cy), kp), j)

    best = None
    for f0 in (800, 1500, 3000):
        for t0 in (-0.3, 0.0, 0.3):
            r = minimize(loss, [f0, t0, 0.0], method="Nelder-Mead", options={"xatol": 1e-3, "fatol": 1e-5, "maxiter": 2000})
            if best is None or r.fun < best.fun:
                best = r
    f, tilt, pan = best.x
    H = homography(f, tilt, pan, cx, cy)
    kr = apply(H, kp)
    print(f"segment-length CV: before {cv0:.4f}  after {best.fun:.4f}")
    print(f"fitted focal {f:.0f} px ({f / args.width * 36:.0f} mm equiv.), tilt {np.degrees(tilt):+.1f} deg, pan {np.degrees(pan):+.1f} deg")

    def angles(pts):
        out = {}
        hip = (pts[:, j["hip_L"]] + pts[:, j["hip_R"]]) / 2
        shoulder = (pts[:, j["shoulder_L"]] + pts[:, j["shoulder_R"]]) / 2
        for s in SIDES:
            ic = [i - start for i in info["initial_contact_frames"][s] if i - start >= 0]
            to = [i - start for i in info["toe_off_frames"][s] if i - start >= 0]
            H_, K, A, He, T = (pts[:, j[f"{n}_{s}"]] for n in ("hip", "knee", "ankle", "heel", "toe"))
            knee = 180 - angle_deg(H_[ic], K[ic], A[ic])
            tibia = segment_lean_deg(K[ic], A[ic], d)
            mids = [(a + b) // 2 for a in ic for b in to if b > a and b - a < 0.5 * args.fps][: len(ic)]
            trunk = segment_lean_deg(shoulder[mids], hip[mids], d)
            thigh = np.linalg.norm(H_ - K, axis=1)
            shank = np.linalg.norm(K - A, axis=1)
            out[s] = {
                "knee_ic": (knee.mean(), knee.std()),
                "tibia_ic": (tibia.mean(), tibia.std()),
                "trunk_mid": (trunk.mean(), trunk.std()),
                "thigh_px": (thigh.mean(), thigh.std()),
                "shank_px": (shank.mean(), shank.std()),
            }
        return out

    a0, a1 = angles(kp), angles(kr)
    print(f"\n{'':22s} {'original L':>16s} {'rectified L':>16s} {'original R':>16s} {'rectified R':>16s}")
    for k in a0["L"]:
        row = f"{k:22s}"
        for s in SIDES:
            for a in (a0, a1):
                m, sd = a[s][k]
                row += f" {m:8.1f} ± {sd:4.1f} "
        print(row)
    (args.run_dir / "rectify.json").write_text(json.dumps({"focal_px": f, "tilt_deg": float(np.degrees(tilt)), "pan_deg": float(np.degrees(pan)), "cv_before": cv0, "cv_after": float(best.fun)}, indent=2))


if __name__ == "__main__":
    main()
