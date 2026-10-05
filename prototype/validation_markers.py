"""Belt speed and pixel scale from the tape markers of the 10-04 validation clips.

Two fixed markers on the near deck edge, 100 cm apart (inner edges), give the scale in the plane of
the deck edge. A third marker on the belt edge crosses them on every revolution: the time between the
two inner edges gives the real belt speed.

    uv run python validation_markers.py <clip.mp4> --rail-band 1520 1550 --belt-band 1465 1500

Bands are image rows (y from, y to) of the deck edge with the fixed markers and of the belt strip the
belt marker travels on. Prints the marker positions, every pass and the mean speed in the plane of the
fixed markers (depth corrections are applied by the caller, who knows the distances).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def blobs(profile: np.ndarray, thresh: float, min_w: int = 4) -> list[tuple[int, int]]:
    on = profile > thresh
    edges = np.flatnonzero(np.diff(on.astype(int)))
    starts = list(edges[on[edges + 1]] + 1)
    ends = list(edges[~on[edges + 1]] + 1)
    if on[0]:
        starts = [0] + starts
    if on[-1]:
        ends = ends + [len(on)]
    return [(a, b) for a, b in zip(starts, ends) if b - a >= min_w]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    ap.add_argument("--rail-band", type=int, nargs=2, required=True)
    ap.add_argument("--belt-band", type=int, nargs=2, required=True)
    ap.add_argument("--fps", type=float, default=240.0)
    ap.add_argument("--start", type=int, default=0, help="first file frame")
    ap.add_argument("--frames", type=int, default=None)
    ap.add_argument("--out", type=Path)
    args = ap.parse_args()

    cap = cv2.VideoCapture(str(args.video))
    cap.set(cv2.CAP_PROP_POS_FRAMES, args.start)
    rail, belt = [], []
    i = 0
    while args.frames is None or i < args.frames:
        ok, f = cap.read()
        if not ok:
            break
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY).astype(np.float32)
        if i % 24 == 0:
            rail.append(np.median(g[args.rail_band[0]:args.rail_band[1]], axis=0))
        belt.append(g[args.belt_band[0]:args.belt_band[1]].max(axis=0))
        i += 1
    belt = np.array(belt)

    # Fixed markers: bright blobs on the dark deck edge, from the median profile over the clip
    # (a passing shoe only hides them for a few samples).
    prof = np.median(np.array(rail), axis=0)
    thr = np.median(prof) + 0.5 * (np.percentile(prof, 99.5) - np.median(prof))
    found = blobs(prof, thr)
    found = sorted(found, key=lambda ab: -prof[ab[0]:ab[1]].mean())[:2]
    (l0, l1), (r0, r1) = sorted(found)
    inner_left, inner_right = float(l1), float(r0)
    print(f"fixed markers: left {l0}-{l1}, right {r0}-{r1}; inner edges {inner_left:.0f} and {inner_right:.0f} = {inner_right - inner_left:.0f} px for 100 cm")

    # Belt marker: the brightest column in the belt strip, when clearly brighter than the strip.
    base = np.median(belt, axis=0)
    xs = np.full(len(belt), np.nan)
    for k, row in enumerate(belt):
        d = row - base
        j = int(np.argmax(d))
        if d[j] > 60:
            xs[k] = j
    # Passes: detections grouped by time (a pass lasts ~0.1 s, revolutions are ~1 s apart; the handrail
    # post hides the marker for a few frames, so gaps inside a pass are allowed). Robust line fit of
    # x(frame), then the time to go from one inner edge to the other.
    det = np.flatnonzero(~np.isnan(xs))
    groups = np.split(det, np.flatnonzero(np.diff(det) > 30) + 1) if len(det) else []
    passes = []
    for g in groups:
        t, x = g.astype(float), xs[g]
        keep = (x > inner_left - 60) & (x < inner_right + 60)
        if keep.sum() < 10:
            continue
        for _ in range(3):
            slope, icpt = np.polyfit(t[keep], x[keep], 1)
            resid = np.abs(x - (slope * t + icpt))
            keep = keep & (resid < 6)
            if keep.sum() < 10:
                break
        if keep.sum() < 10 or x[keep].min() > inner_left + 20 or x[keep].max() < inner_right - 20:
            continue
        dt = (inner_right - inner_left) / abs(slope) / args.fps
        passes.append({"frame": args.start + int(g[0]), "px_per_frame": float(slope), "seconds_for_100cm": float(dt), "points": int(keep.sum())})
    secs = np.array([p["seconds_for_100cm"] for p in passes])
    starts = np.array([p["frame"] for p in passes])
    period = float(np.median(np.diff(starts))) / args.fps if len(starts) > 2 else None
    v = 1.0 / secs  # m/s in the plane of the fixed markers
    print(f"{len(passes)} passes; 100 cm in {secs.mean() * 1000:.1f} ± {secs.std() * 1000:.1f} ms; speed {v.mean() * 3.6:.2f} ± {v.std() * 3.6:.2f} km/h in the marker plane; revolution {period if period is None else round(period, 3)} s")
    if args.out:
        args.out.write_text(json.dumps({
            "inner_left": inner_left, "inner_right": inner_right, "px_per_100cm": inner_right - inner_left,
            "passes": passes, "speed_kmh_marker_plane": float(v.mean() * 3.6), "speed_sd": float(v.std() * 3.6),
            "revolution_s": period,
        }, indent=1))


if __name__ == "__main__":
    main()
