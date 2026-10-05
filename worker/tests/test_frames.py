"""Frame identity and timing through the pipeline: which frame a reader returns, and which frame of the
Playback Video carries it. These broke on real phone clips (10-03: dropped frames and an edit list put
the skeleton 4 frames late; 10-04: OpenCV's seek landed 21 frames early after a slow-motion start, and
frames hidden by an edit list shifted a trimmed clip by 31 frames)."""

import json
import subprocess

import cv2
import numpy as np
import pytest

import analyze as side
from synthetic import decode_index
from worker import pipeline


def test_probe_reads_the_slow_motion_capture_rate(phone_video):
    container_fps, n, w, h, capture_fps = side.probe(phone_video.path)
    assert n == phone_video.frames
    assert capture_fps == 240


@pytest.mark.parametrize("skip", [0, 1, 2, 37, 151, 152, 250])
def test_iter_frames_skip_returns_the_exact_frame(phone_video, skip):
    frame = next(side.iter_frames(phone_video.path, 1, skip=skip))
    assert decode_index(frame) == skip


def test_iter_frames_step_keeps_counting_frames_not_time(phone_video):
    got = [decode_index(f) for f in side.iter_frames(phone_video.path, 20, skip=140, step=2)]
    assert got == list(range(140, 180, 2))


def test_rear_window_uses_the_middle_of_long_clips():
    start, n = pipeline.rear_window(n_total=24000, fps=240.0, sub=2)  # 100 s clip, 20 s window
    assert n == 2400 and start == (24000 - 4800) // 2


def test_rear_window_uses_short_clips_whole():
    assert pipeline.rear_window(n_total=1669, fps=240.0, sub=2) == (0, 834)


def playback_from(video, tmp_path, skip=140, step=2, n=60, fps=120.0):
    """Playback Video of `n` analyzed frames, written the way the pipeline does it."""
    writer = pipeline.PlaybackWriter(tmp_path / "playback.mp4", fps)
    rows = [decode_index(f) for f in writer.tee(side.iter_frames(video.path, n, skip=skip, step=step))]
    assert writer.close() == len(rows) == n
    return writer.path, rows


def test_playback_video_has_one_frame_per_row_at_a_regular_pace(phone_video, tmp_path):
    # The source has a slow-motion start gap, dropped frames after frame 150 and starts at 0.0476 s.
    path, rows = playback_from(phone_video, tmp_path)
    assert rows == list(range(140, 260, 2))
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout.split()
    pts = sorted(float(x.split(",")[0]) for x in out if x)
    np.testing.assert_allclose(pts, np.arange(len(rows)) / 120.0, atol=1e-4)  # frame i at i / fps, from 0
    cap = cv2.VideoCapture(str(path))
    shown = []
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        shown.append(decode_index(frame))
    assert shown == rows  # frame i of the Playback Video is the frame row i was measured on


def test_browser_json_marks_the_playback_video(tmp_path):
    out = tmp_path / "kp.json"
    pipeline.write_browser_keypoints(out, np.zeros((5, 2, 2)), np.ones((5, 2)), ["a", "b"], 120.0, 140, 240, 96, {}, 30.0, frame_step=2, playback=True)
    doc = json.loads(out.read_text())
    assert doc["playback"] is True and doc["fps"] == 120.0 and "times" not in doc


def test_playback_writer_refuses_a_row_count_mismatch():
    with pytest.raises(RuntimeError):
        pipeline.check_playback(59, 60)
