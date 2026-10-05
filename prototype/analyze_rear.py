"""Prototype: rear-view running analysis (frontal-plane metrics).

Usage:
    uv run analyze_rear.py VIDEO [--model rtmpose] [--device cuda] [--start-seconds N] [--max-seconds N]

From behind, the sagittal gait events are not observable, so instead of
measuring at midstance we take the peak of each frontal-plane angle within
each step, which occurs around midstance:

- pelvic drop: angle of the hip-to-hip line from horizontal; positive when the
  swing-side hip is lower than the stance-side hip (contralateral pelvic drop).
- hip adduction: angle of the stance thigh (hip -> knee) from the vertical,
  positive when the knee is medial to the hip; also relative to the pelvis line.

Step timing comes from the vertical motion of the ankles (lowest point = late
stance), which also gives the cadence to cross-check against the side view.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from scipy.signal import find_peaks

sys.path.insert(0, str(Path(__file__).parent))
from analyze import JOINTS, MIN_SCORE, NAMES, SIDES, clean, iter_frames, probe, run_pose, summarize  # noqa: E402


def pelvis_angle(kp, j):
    """Hip-line angle from horizontal, degrees, positive = left hip lower in the image."""
    hl, hr = kp[:, j["hip_L"]], kp[:, j["hip_R"]]
    return np.degrees(np.arctan2(hl[:, 1] - hr[:, 1], np.abs(hl[:, 0] - hr[:, 0])))


def thigh_from_vertical(kp, j, s, medial_sign):
    """Thigh angle from vertical, degrees, positive = knee medial to hip."""
    h, k = kp[:, j[f"hip_{s}"]], kp[:, j[f"knee_{s}"]]
    return np.degrees(np.arctan2(medial_sign * (k[:, 0] - h[:, 0]), k[:, 1] - h[:, 1]))


def running_segment(kp, sc, fps, min_score=0.6, max_gap_s=0.1):
    """(start, end) of the longest stretch where the runner is tracked and stays put on the belt.

    Rear clips start and end with the runner stepping on or off the treadmill or leaving the frame;
    those frames push the ankle percentiles that define stance far from the running range. A frame
    belongs to the stretch when its mean keypoint score is high enough and the pelvis is within half
    a torso length of its median position; gaps up to `max_gap_s` are bridged."""
    j = {n: i for i, n in enumerate(NAMES)}
    hip = (kp[:, j["hip_L"]] + kp[:, j["hip_R"]]) / 2
    shoulder = (kp[:, j["shoulder_L"]] + kp[:, j["shoulder_R"]]) / 2
    torso = np.nanmedian(np.linalg.norm(shoulder - hip, axis=1))
    centre = np.nanmedian(hip, axis=0)
    good = (sc.mean(axis=1) >= min_score) & (np.abs(hip - centre) < 0.5 * torso).all(axis=1)
    # Bridge short dropouts, then take the longest run.
    gap = int(max_gap_s * fps)
    idx = np.flatnonzero(good)
    if len(idx) == 0:
        return 0, 0
    breaks = np.flatnonzero(np.diff(idx) > gap + 1)
    starts = np.r_[idx[0], idx[breaks + 1]]
    ends = np.r_[idx[breaks], idx[-1]] + 1
    k = int(np.argmax(ends - starts))
    return int(starts[k]), int(ends[k])


def compute(kp, sc, fps):
    j = {n: i for i, n in enumerate(NAMES)}
    min_gap = int(0.45 * fps)
    # Seen from behind, the runner's left is on the image left. Medial direction
    # for the left leg is +x (towards the right leg), for the right leg -x.
    left_is_left = np.nanmean(kp[:, j["hip_L"], 0] - kp[:, j["hip_R"], 0]) < 0
    medial = {"L": 1 if left_is_left else -1, "R": -1 if left_is_left else 1}

    pelvis_raw = pelvis_angle(kp, j)  # + = left hip lower
    # A camera that is not level adds a constant tilt to every angle. Over
    # whole strides the pelvis averages out to level, so use its mean as the
    # horizon; report it so a large value can flag a badly placed camera.
    baseline = float(np.nanmean(pelvis_raw))
    pelvis = pelvis_raw - baseline
    stance_steps = {}
    metrics, info = {}, {"view": "rear", "left_on_image_left": bool(left_is_left), "pelvis_baseline_deg": round(baseline, 2)}
    contacts = []
    for s in SIDES:
        ankle_y = kp[:, j[f"ankle_{s}"], 1]
        lo, hi = np.percentile(ankle_y, 5), np.percentile(ankle_y, 95)
        # The foot on the belt sits on a plateau at the bottom of the ankle's
        # vertical range; stance = each contiguous run inside the bottom 25 %.
        on_ground = ankle_y >= hi - 0.25 * (hi - lo)
        edges = np.flatnonzero(np.diff(on_ground.astype(int)))
        starts = edges[on_ground[edges + 1]] + 1
        ends = edges[~on_ground[edges + 1]] + 1
        if on_ground[0]:
            starts = np.r_[0, starts]
        if on_ground[-1]:
            ends = np.r_[ends, len(ankle_y)]
        windows = [(int(a), int(b)) for a, b in zip(starts, ends) if b - a >= 0.1 * fps]
        contacts.extend(a for a, _ in windows)
        stance_steps[s] = windows
        # Contralateral pelvic drop during this leg's stance: the other hip drops.
        sign = -1 if s == "L" else 1  # pelvis + = left hip lower; during L stance the right hip drops -> negative
        drops = [float(np.max(sign * pelvis[a:b])) for a, b in windows if b > a]
        thigh = thigh_from_vertical(kp, j, s, medial[s])
        adduction = [float(np.max(thigh[a:b])) for a, b in windows if b > a]
        # Hip adduction relative to the pelvis line (femur vs perpendicular to pelvis).
        adduction_rel = [float(np.max(thigh[a:b] + (-sign) * pelvis[a:b])) for a, b in windows if b > a]
        score = [float(sc[a:b, [j[f"hip_{s}"], j[f"knee_{s}"], j[f"hip_L"], j[f"hip_R"]]].mean()) for a, b in windows if b > a]
        metrics[f"pelvic_drop_{s}"] = summarize(drops, score or [0], f"Contralateral pelvic drop, peak in stance ({s} stance)", "deg")
        metrics[f"hip_adduction_{s}"] = summarize(adduction, score or [0], f"Hip adduction vs vertical, peak in stance ({s})", "deg")
        metrics[f"hip_adduction_rel_pelvis_{s}"] = summarize(adduction_rel, score or [0], f"Hip adduction vs pelvis, peak in stance ({s})", "deg")
        info[f"stance_windows_{s}"] = windows
    # Left and right stance can start in the same frame after smoothing: keep one, or the
    # zero interval becomes an infinite cadence.
    contacts = np.unique(np.array(contacts))
    if len(contacts) > 2:
        intervals = np.diff(contacts) / fps
        metrics["cadence"] = summarize(60.0 / intervals, sc[contacts].mean(axis=1), "Cadence (from stance starts)", "steps/min")
    metrics["step_count"] = {"label": "Stance phases found", "value": {s: len(stance_steps[s]) for s in SIDES}, "state": "descriptor"}
    info["mean_keypoint_score"] = round(float(sc.mean()), 3)
    return metrics, info, pelvis


def write_overlay(frames, size, kp, sc, info, fps, path):
    w, h = size
    out = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), min(fps, 60), (w, h))
    j = {n: i for i, n in enumerate(NAMES)}
    colors = {"L": (0, 200, 255), "R": (255, 120, 0)}
    bones = [("shoulder", "hip"), ("hip", "knee"), ("knee", "ankle"), ("ankle", "heel"), ("heel", "toe")]
    in_stance = {s: np.zeros(len(kp), bool) for s in SIDES}
    for s in SIDES:
        for a, b in info[f"stance_windows_{s}"]:
            in_stance[s][a:b] = True
    for i, frame in enumerate(frames):
        if i >= len(kp):
            break
        img = frame.copy()
        cv2.line(img, tuple(kp[i, j["hip_L"]].astype(int)), tuple(kp[i, j["hip_R"]].astype(int)), (255, 255, 255), 3)
        for s in SIDES:
            for a, b in bones:
                cv2.line(img, tuple(kp[i, j[f"{a}_{s}"]].astype(int)), tuple(kp[i, j[f"{b}_{s}"]].astype(int)), colors[s], 2)
            for n in JOINTS:
                low = sc[i, j[f"{n}_{s}"]] < MIN_SCORE
                cv2.circle(img, tuple(kp[i, j[f"{n}_{s}"]].astype(int)), 5, (0, 0, 255) if low else colors[s], -1)
            if in_stance[s][i]:
                cv2.putText(img, f"stance {s}", (20, 40 + 30 * SIDES.index(s)), cv2.FONT_HERSHEY_SIMPLEX, 1, colors[s], 2)
        cv2.putText(img, f"{i / fps:6.2f}s f{i}", (w - 220, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        out.write(img)
    out.release()


def write_plots(kp, pelvis, info, fps, path):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    j = {n: i for i, n in enumerate(NAMES)}
    t = np.arange(len(kp)) / fps
    fig, axes = plt.subplots(3, 1, figsize=(14, 9), sharex=True)
    axes[0].plot(t, pelvis, label="pelvis angle (+ = left hip lower)")
    for s, c in zip(SIDES, ("tab:blue", "tab:orange")):
        axes[1].plot(t, -kp[:, j[f"ankle_{s}"], 1], color=c, label=f"ankle height {s} (px)")
        for a, b in info[f"stance_windows_{s}"]:
            for ax in axes:
                ax.axvspan(a / fps, b / fps, color=c, alpha=0.08)
        medial = 1 if (s == "L") == info["left_on_image_left"] else -1
        axes[2].plot(t, thigh_from_vertical(kp, j, s, medial), color=c, label=f"thigh from vertical {s} (+ = knee medial)")
    for ax in axes:
        ax.legend(loc="upper right")
        ax.grid(alpha=0.3)
    axes[2].set_xlabel("s")
    fig.tight_layout()
    fig.savefig(path, dpi=100)


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("video", type=Path)
    p.add_argument("--model", choices=["rtmpose", "mediapipe"], default="rtmpose")
    p.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    p.add_argument("--start-seconds", type=float, default=0.0)
    p.add_argument("--max-seconds", type=float, default=None)
    p.add_argument("--fps", type=float, default=None)
    p.add_argument("--reuse-pose", action="store_true")
    args = p.parse_args()

    out = Path(__file__).parent.parent / "data" / "out" / f"{args.video.stem}_{args.model}_rear"
    out.mkdir(parents=True, exist_ok=True)
    container_fps, n_total, w, h, capture_fps = probe(args.video)
    fps = args.fps or (capture_fps if capture_fps and capture_fps > container_fps + 1 else container_fps)
    n = min(n_total, int(args.max_seconds * fps)) if args.max_seconds else n_total
    print(f"{n} of {n_total} frames, {w}x{h}, container {container_fps:.1f} fps, using {fps:.0f} fps")

    t0 = time.time()
    cached = out / "keypoints.parquet"
    if args.reuse_pose and cached.exists():
        df = pd.read_parquet(cached)
        kp_raw = np.stack([df.pivot(index="frame", columns="joint", values=c)[NAMES].values for c in ("x_raw", "y_raw")], axis=-1)[:n]
        sc = df.pivot(index="frame", columns="joint", values="score")[NAMES].values[:n]
    else:
        kp_raw, sc = run_pose(iter_frames(args.video, n), args.model, args.device, fps)
    n = len(kp_raw)
    print(f"pose: {time.time() - t0:.1f}s, mean score {sc.mean():.2f}")

    kp = clean(kp_raw, sc, fps)
    start = int(args.start_seconds * fps)
    metrics, info, pelvis = compute(kp[start:], sc[start:], fps)
    for s in SIDES:
        info[f"stance_windows_{s}"] = [(a + start, b + start) for a, b in info[f"stance_windows_{s}"]]
    pelvis = np.concatenate([np.full(start, np.nan), pelvis])
    info.update({"model": args.model, "fps": fps, "frames": n, "start_frame": start})
    metrics["_info"] = info
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))

    rows = [(i, joint, kp_raw[i, k, 0], kp_raw[i, k, 1], kp[i, k, 0], kp[i, k, 1], sc[i, k]) for i in range(n) for k, joint in enumerate(NAMES)]
    pd.DataFrame(rows, columns=["frame", "joint", "x_raw", "y_raw", "x", "y", "score"]).to_parquet(cached)
    write_overlay(iter_frames(args.video, n), (w, h), kp, sc, info, fps, out / "overlay.mp4")
    write_plots(kp, pelvis, info, fps, out / "plots.png")

    print(f"\nresults in {out}\n")
    for k, m in metrics.items():
        if k.startswith("_"):
            continue
        if m["state"] == "descriptor":
            print(f"  {m['label']:<58} {m['value']}")
            continue
        val = f"{m['mean']} ± {m['sd']} {m['unit']}" if m["mean"] is not None else "-"
        print(f"  {m['label']:<58} {val:<22} n={m['n']:<3} score={m['mean_score']}  {m['state']}")


if __name__ == "__main__":
    main()
