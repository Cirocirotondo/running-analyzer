"""Camera-placement validation of 2026-10-04: metrics per clip and window, true scale from the markers.

Reads the pose files written by validation_pose.py and the clip geometry below (from Simone's tape
measurements and the 100 cm deck markers), and prints:

- every side-view Metric per clip, as mean ± SD over non-overlapping 20 s windows of steady running;
- the pixel scale the app derives from body height against the true scale from the markers;
- the rear-view Metrics, with the camera roll measured from the treadmill's rear edge.

    uv run python validation_analysis.py --data ../data/validation --speed-kmh 13.7
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

import analyze as side
import analyze_rear as rear

HEIGHT_CM = 179.0
# Focal length in pixels, from the 100 cm deck markers: 521 px at 252 cm (hip-height camera),
# 588 / 583 px at 224 cm (other treadmill, right / left). f = px_per_cm × distance.
FOCAL_PX = np.mean([5.21 * 252, 5.88 * 224, 5.83 * 224])
# Horizontal distance from the camera to the line the feet land on (≈ belt centre line), cm,
# and camera height relative to the belt surface, cm.
# Facing left in the image means the camera sees the runner's left side (near leg L).
CLIPS = {
    "20261004_152455": {"view": "side", "near": "L", "position": "A hip height", "distance": 296, "height": 105},
    "20261004_152819": {"view": "side", "near": "L", "position": "B floor", "distance": 194, "height": -17},
    "20261004_153106": {"view": "side", "near": "L", "position": "C other treadmill", "distance": 268, "height": 14},
    "20261004_150255": {"view": "side", "near": "R", "position": "A hip height", "distance": 296, "height": 105},
    "20261004_150556": {"view": "side", "near": "R", "position": "B floor", "distance": 194, "height": -17},
    "20261004_151306": {"view": "side", "near": "R", "position": "C other treadmill", "distance": 268, "height": 14},
    "20261004_151921": {"view": "rear", "position": "rear, 2 m", "distance": 200, "height": 74},
}
WINDOW_S = 20.0


def steady_range(ev, fps, n):
    """Frames between the first and last contact of the longest run of steps whose interval stays
    within 8 % of the median (excludes speeding up and slowing down)."""
    ic = np.sort(np.concatenate([ev.ic["L"], ev.ic["R"]]))
    iv = np.diff(ic)
    med = np.median(iv)
    good = np.abs(iv - med) < 0.08 * med
    best, cur, start = (0, 0), 0, 0
    for i, g in enumerate(good):
        if g:
            if cur == 0:
                start = i
            cur += 1
            if cur > best[1] - best[0]:
                best = (start, start + cur)
        else:
            cur = 0
    return int(ic[best[0]]), int(ic[min(best[1], len(ic) - 1)])


def side_clip(name, meta, data, speed):
    d = np.load(data / f"{name}.npz")
    kp_raw, sc, fps = d["kp_raw"], d["sc"], float(d["fps"])
    kp = side.clean(kp_raw, sc, fps)
    ev = side.detect_events(kp, fps)
    a, b = steady_range(ev, fps, len(kp))
    w = int(WINDOW_S * fps)
    windows = [(s, s + w) for s in range(a, b - w + 1, w)]
    true_cm_per_px = meta["distance"] / FOCAL_PX  # in the plane of the belt centre line
    rows = []
    for s, e in windows:
        kw, sw = kp[s:e], sc[s:e]
        evw = side.detect_events(kw, fps)
        m = side.compute_metrics(kw, sw, evw, fps, speed, HEIGHT_CM)
        info = m.pop("_info")
        rows.append({"metrics": {k: v.get("mean") for k, v in m.items() if isinstance(v, dict) and "mean" in v},
                     "n": {k: v.get("n") for k, v in m.items() if isinstance(v, dict)},
                     "cm_per_px_height": info["cm_per_px"], "near_side_detected": info["near_side"]})
    j = {n: i for i, n in enumerate(side.NAMES)}
    leg_px = {s: float(np.median(np.linalg.norm(kp[a:b, j[f"hip_{s}"]] - kp[a:b, j[f"knee_{s}"]], axis=1)
                                 + np.linalg.norm(kp[a:b, j[f"knee_{s}"]] - kp[a:b, j[f"ankle_{s}"]], axis=1))) for s in "LR"}
    vo = {}
    ic = np.sort(ev.ic[meta["near"]][(ev.ic[meta["near"]] >= a) & (ev.ic[meta["near"]] < b)])
    for label, idx in (("nose", ["nose"]), ("shoulders", ["shoulder_L", "shoulder_R"]), ("hips", ["hip_L", "hip_R"])):
        y = kp[:, [j[n] for n in idx], 1].mean(axis=1)
        vo[label] = float(np.median([np.ptp(y[f0:f1]) for f0, f1 in zip(ic[:-1], ic[1:])]) * true_cm_per_px)
    return {"windows": rows, "steady_s": (b - a) / fps, "true_cm_per_px": true_cm_per_px, "leg_px": leg_px, "vo_by_landmark_cm": vo,
            "mean_score": float(sc[a:b].mean())}


def rear_clip(name, meta, data):
    d = np.load(data / f"{name}.npz")
    kp_raw, sc, fps = d["kp_raw"], d["sc"], float(d["fps"])
    kp = rear.clean(kp_raw, sc, fps)
    a, b = rear.running_segment(kp, sc, fps)
    w = int(WINDOW_S * fps)
    out = []
    for s in range(a, b - w + 1, w):
        m, info, _ = rear.compute(kp[s:s + w], sc[s:s + w], fps)
        out.append({k: (v.get("mean"), v.get("n")) for k, v in m.items() if isinstance(v, dict) and "mean" in v} | {"_baseline": info["pelvis_baseline_deg"]})
    j = {n: i for i, n in enumerate(rear.NAMES)}
    hip_w = float(np.median(np.linalg.norm(kp[a:b, j["hip_L"]] - kp[a:b, j["hip_R"]], axis=1)))
    return {"windows": out, "running_s": (b - a) / fps, "hip_width_px": hip_w, "mean_score": float(sc[a:b].mean())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--speed-kmh", type=float, required=True)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()
    results = {}
    for name, meta in CLIPS.items():
        if not (args.data / f"{name}.npz").exists():
            print(f"{name}: no pose file yet")
            continue
        results[name] = (side_clip(name, meta, args.data, args.speed_kmh) if meta["view"] == "side" else rear_clip(name, meta, args.data)) | {"meta": meta}
    if args.out:
        args.out.write_text(json.dumps(results, indent=1, default=float))
    print(f"focal length from the markers: {FOCAL_PX:.0f} px")
    for name, r in results.items():
        meta = r["meta"]
        if meta["view"] != "side":
            continue
        ch = np.mean([w["cm_per_px_height"] for w in r["windows"]])
        print(f"\n{name} {meta['position']}, near leg {meta['near']}: {len(r['windows'])} windows of {WINDOW_S:.0f} s, steady {r['steady_s']:.0f} s, score {r['mean_score']:.2f}")
        print(f"  scale: from height {ch:.4f} cm/px, from markers {r['true_cm_per_px']:.4f} cm/px -> height-based error {100 * (ch / r['true_cm_per_px'] - 1):+.1f} %")
        for s in "LR":
            print(f"  leg {s} (thigh+shank): {r['leg_px'][s]:.0f} px = {r['leg_px'][s] * r['true_cm_per_px']:.1f} cm at the belt centre plane (app assumes {0.49 * HEIGHT_CM:.1f})")
        print("  vertical oscillation per stride, true scale: " + ", ".join(f"{k} {v:.1f} cm" for k, v in r["vo_by_landmark_cm"].items()))
        keys = sorted({k for w in r["windows"] for k in w["metrics"]})
        for k in keys:
            vals = np.array([w["metrics"][k] for w in r["windows"] if w["metrics"].get(k) is not None], dtype=float)
            ns = [w["n"].get(k) for w in r["windows"]]
            print(f"  {k:28s} {vals.mean():8.2f} ± {vals.std():5.2f}   windows: {np.round(vals, 1).tolist()}  n={ns}")
    for name, r in results.items():
        if r["meta"]["view"] != "rear":
            continue
        print(f"\n{name} rear: running {r['running_s']:.0f} s, hip width {r['hip_width_px']:.0f} px, score {r['mean_score']:.2f}")
        keys = sorted({k for w in r["windows"] for k in w if not k.startswith("_")})
        for k in keys:
            vals = np.array([w[k][0] for w in r["windows"] if w.get(k) and w[k][0] is not None], dtype=float)
            print(f"  {k:28s} {vals.mean():8.2f} ± {vals.std():5.2f}   windows: {np.round(vals, 1).tolist()}")
        print(f"  pelvis baseline per window: {[w['_baseline'] for w in r['windows']]}")


if __name__ == "__main__":
    main()
