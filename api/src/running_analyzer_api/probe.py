"""Reads a video's fps, frame count and slow-motion capture rate with ffprobe, straight from storage."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass

from .workload import effective_fps


@dataclass
class VideoInfo:
    container_fps: float
    capture_fps: float | None
    frames: int
    width: int
    height: int

    @property
    def fps(self) -> float:
        return effective_fps(self.container_fps, self.capture_fps)

    @property
    def duration_s(self) -> float:
        """Real duration: for a slow-motion clip, frames / capture fps, not the container's playback length."""
        return self.frames / self.fps if self.fps else 0.0


async def probe_url(url: str) -> VideoInfo | None:
    """ffprobe over HTTP reads only the headers of a fast-start MP4; a file without fast start costs a
    second range request for the trailing index, still no full download."""
    proc = await asyncio.create_subprocess_exec(
        "ffprobe", "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=r_frame_rate,avg_frame_rate,nb_frames,width,height,duration:format_tags=com.android.capture.fps",
        "-of", "json", url,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    out, _ = await asyncio.wait_for(proc.communicate(), timeout=60)
    if proc.returncode != 0:
        return None
    data = json.loads(out)
    streams = data.get("streams") or []
    if not streams:
        return None
    s = streams[0]
    num, _, den = (s.get("avg_frame_rate") or s.get("r_frame_rate") or "0/1").partition("/")
    container_fps = float(num) / float(den or 1) if float(den or 1) else 0.0
    frames = int(s.get("nb_frames") or 0)
    if not frames and s.get("duration"):
        frames = int(float(s["duration"]) * container_fps)
    tag = (data.get("format", {}).get("tags") or {}).get("com.android.capture.fps")
    return VideoInfo(
        container_fps=container_fps, capture_fps=float(tag) if tag else None, frames=frames,
        width=int(s.get("width") or 0), height=int(s.get("height") or 0),
    )
