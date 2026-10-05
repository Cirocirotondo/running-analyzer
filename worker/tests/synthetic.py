"""Synthetic phone-like videos for the pipeline tests.

Each frame carries its own index as a 12-bit barcode (black/white columns), so a test can tell exactly
which frame a reader returned. Timestamps reproduce what phones write and what broke the app on 10-03 and
10-04: a slow-motion capture-fps tag, a long gap after the first frame (slow-motion start), dropped
frames (a longer interval in the middle) and an edit list (first frame shown after 0).
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

BITS = 12
W, H = 240, 96


@dataclass
class Synthetic:
    path: Path
    frames: int
    pts: list[float]  # presentation time of every frame as written in the file, seconds (what the browser uses)


def encode_index(i: int) -> np.ndarray:
    img = np.zeros((H, W, 3), np.uint8)
    col = W // BITS
    for b in range(BITS):
        if (i >> b) & 1:
            img[:, b * col:(b + 1) * col] = 255
    return img


def decode_index(img: np.ndarray) -> int:
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
    col = g.shape[1] // BITS
    return sum(1 << b for b in range(BITS) if g[:, b * col + col // 4:(b + 1) * col - col // 4].mean() > 127)


def make_video(dest: Path, frames: int = 300, container_fps: float = 30.0, first_gap: float = 1.6067,
               drop_at: int | None = 150, dropped: int = 5, start_offset: float = 0.0476, capture_fps: int = 240) -> Synthetic:
    """H.264 file whose frame i is shown at pts[i]; `dropped` frames missing after frame `drop_at`."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is needed to build the synthetic videos")
    step = 1.0 / container_fps
    durations = [first_gap] + [step] * (frames - 1)
    if drop_at is not None:
        durations[drop_at] = step * (dropped + 1)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        lines = []
        for i, d in enumerate(durations):
            name = f"f{i:05d}.png"
            cv2.imwrite(str(tmp / name), encode_index(i))
            lines += [f"file '{name}'", f"duration {d:.6f}"]
        lines.append(f"file 'f{frames - 1:05d}.png'")  # the concat demuxer needs the last file twice
        (tmp / "list.txt").write_text("\n".join(lines) + "\n")
        subprocess.run([
            "ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(tmp / "list.txt"),
            "-fps_mode", "passthrough", "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-g", "30",
            "-output_ts_offset", f"{start_offset}", "-metadata", f"com.android.capture.fps={capture_fps}.000000",
            "-movflags", "+use_metadata_tags", str(dest),
        ], check=True)
    # The container rounds timestamps to its time base: the truth is what ended up in the file.
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time", "-of", "csv=p=0", str(dest)],
                         capture_output=True, text=True, check=True).stdout.split()
    pts = sorted(float(x.split(",")[0]) for x in out if x)
    return Synthetic(dest, len(pts), pts)
