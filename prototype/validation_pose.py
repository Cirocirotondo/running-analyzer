"""Pose estimation over whole validation clips, saved for repeated metric computation.

    uv run python validation_pose.py ../videos/nuovi_video/*.mp4 --out ../data/validation --device cuda

For each clip writes <stem>.npz with kp_raw (N, 13, 2), sc (N, 13), fps (real frames per second of the
saved rows) and frame_step (rows are file frames 0, step, 2·step, ...). Clips already done are skipped.
"""

from __future__ import annotations

import argparse
import time
from pathlib import Path

import numpy as np

import analyze as side


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("videos", nargs="+", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--max-fps", type=float, default=120.0)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    for video in args.videos:
        dest = args.out / f"{video.stem}.npz"
        if dest.exists():
            print(f"{video.name}: done already")
            continue
        container_fps, n_total, w, h, capture_fps = side.probe(video)
        fps = capture_fps if capture_fps and capture_fps > container_fps + 1 else container_fps
        step = max(1, int(round(fps / args.max_fps)))
        n = n_total // step
        t0 = time.time()
        print(f"{video.name}: {n_total} frames at {fps:.0f} fps, analysing {n} at {fps / step:.0f} fps", flush=True)
        kp_raw, sc = side.run_pose(side.iter_frames(video, n, step=step), "rtmpose", args.device, fps / step)
        np.savez_compressed(dest, kp_raw=kp_raw, sc=sc, fps=fps / step, frame_step=step, width=w, height=h, container_fps=container_fps)
        print(f"{video.name}: {len(kp_raw)} rows in {time.time() - t0:.0f} s, mean score {sc.mean():.2f}", flush=True)


if __name__ == "__main__":
    main()
