"""Recording Check: a quick look at an uploaded Video, seconds after the upload (queue "checks").

Samples a dozen frames from the middle of the clip, finds the runner with the mid-size pose model and
judges the recording: is the runner there and whole, which side of the Runner the camera sees, and how
the camera was placed. The outcome goes to Video.check_result and, for side Videos, the View.

Thresholds come from the 10-04 camera validation (docs/SPEC.md §11): the image centre falls at ~120 % of
hip height for a camera at hip height, ~45 % from a neighbouring treadmill and ~0 % from the floor.
"""

from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime

import cv2
import numpy as np

import analyze as side

SAMPLES = 12
MIN_PRESENT = 0.6  # share of sampled frames with the runner found
MIN_WHOLE = 0.6  # share of frames with head and feet inside the image
MIN_FACING = 0.75  # share of frames agreeing on the running direction
CAMERA_LOW = {"side": 0.75, "rear": 0.6}  # image centre below this share of hip height
CAMERA_HIGH = 1.9  # above about shoulder height
MAX_ROLL = 6.0  # degrees; small tilts are corrected, larger ones are reported
MIN_RUNNER = 0.3  # runner height as a share of the image height


def sample_frames(source: str, samples: int = SAMPLES) -> tuple[list[np.ndarray], int, int, int]:
    """Frames spread over 20–80 % of the clip (skipping the speed-up and slow-down), from a path or URL."""
    cap = cv2.VideoCapture(source)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frames = []
    for i in np.linspace(0.2 * n, 0.8 * n, samples).astype(int):
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(i))  # approximate seeking is fine for a check
        ok, f = cap.read()
        if ok:
            frames.append(f)
    cap.release()
    if frames:  # the decoder applies the rotation tag, the header sizes may not
        h, w = frames[0].shape[:2]
    return frames, n, w, h


def pose(frames: list[np.ndarray], device: str = "cpu") -> tuple[np.ndarray, np.ndarray]:
    previous = side.POSE_MODE
    side.POSE_MODE = "balanced"
    try:
        return side.run_pose(iter(frames), "rtmpose", device, 30.0, det_every=1)
    finally:
        side.POSE_MODE = previous


def judge(frames: list[np.ndarray], kp: np.ndarray, sc: np.ndarray, family: str, width: int, height: int) -> dict:
    """Pure decision on sampled frames and their keypoints. Returns outcome (ok | warning | rejected),
    reason, warnings, the recognized view and the measurements behind them."""
    j = {n: i for i, n in enumerate(side.NAMES)}
    present = sc.mean(axis=1) >= 0.4
    result: dict = {"outcome": "ok", "reason": None, "warnings": [], "view": "rear" if family == "rear" else None,
                    "frames_sampled": len(frames), "present_share": round(float(present.mean()), 2) if len(sc) else 0.0}
    if len(sc) == 0 or present.mean() < MIN_PRESENT:
        return {**result, "outcome": "rejected", "reason": "runner_not_found"}
    k, s = kp[present], sc[present]

    # Head and feet inside the image (1 % margin), with some confidence.
    margin = 0.01
    need = [j["nose"], j["ankle_L"], j["ankle_R"], j["toe_L"], j["toe_R"]]
    pts = k[:, need]
    inside = (pts[..., 0] > margin * width) & (pts[..., 0] < (1 - margin) * width) & (pts[..., 1] > margin * height) & (pts[..., 1] < (1 - margin) * height)
    whole = (inside & (s[:, need] > 0.3)).all(axis=1)
    # The nose is ~1/16 of the body height below the top of the head: ask for that much room, since the
    # head is needed (vertical oscillation is measured on it).
    body_est = np.max(k[:, [j["toe_L"], j["toe_R"]], 1], axis=1) - k[:, j["nose"], 1]
    whole &= k[:, j["nose"], 1] > body_est / 16
    result["whole_share"] = round(float(whole.mean()), 2)
    if whole.mean() < MIN_WHOLE:
        return {**result, "outcome": "rejected", "reason": "body_not_fully_visible"}

    hip = (k[:, j["hip_L"]] + k[:, j["hip_R"]]) / 2
    feet_y = np.max(k[:, [j["heel_L"], j["heel_R"], j["toe_L"], j["toe_R"]], 1], axis=1)
    body_h = feet_y - k[:, j["nose"], 1]
    result["runner_height_share"] = round(float(np.median(body_h) / height), 2)

    if family == "side":
        # Facing left in the image means the camera sees the runner's left side.
        dx = k[:, j["nose"], 0] - hip[:, 0]
        clear = np.abs(dx) > 0.03 * body_h
        if clear.sum() < 0.5 * len(dx):
            return {**result, "outcome": "rejected", "reason": "not_side_view"}
        facing = np.sign(dx[clear])
        agree = max((facing > 0).mean(), (facing < 0).mean())
        result["facing_agreement"] = round(float(agree), 2)
        if agree < MIN_FACING:
            return {**result, "outcome": "rejected", "reason": "not_side_view"}
        result["view"] = "left_side" if (facing < 0).mean() > 0.5 else "right_side"

    # Camera height: where the image centre falls between the feet on the belt and the hips, as a share
    # of hip height (level phone). The feet's lowest point over the samples is the belt.
    ground = float(np.max(feet_y))
    hip_y = float(np.median(hip[:, 1]))
    ratio = (ground - height / 2) / max(1.0, ground - hip_y)
    result["camera_height_ratio"] = round(float(ratio), 2)
    if ratio < CAMERA_LOW[family]:
        result["warnings"].append("camera_low")
    elif ratio > CAMERA_HIGH:
        result["warnings"].append("camera_high")

    roll = side.roll_from_frames(frames, kp, sc, below=1.6 if family == "rear" else 0.6, max_deg=15.0)
    result["roll_deg"] = None if roll is None else round(roll, 1)
    if roll is not None and abs(roll) > MAX_ROLL:
        result["warnings"].append("tilted")

    if result["runner_height_share"] < MIN_RUNNER:
        result["warnings"].append("runner_small")
    if result["warnings"]:
        result["outcome"] = "warning"
    return result


def check_video(video_id: str) -> None:
    """RQ job. Reads the Video straight from storage over HTTP (no download of the whole file)."""
    import uuid

    import boto3
    from botocore.client import Config

    from running_analyzer_api.models import Video

    from .jobs import BUCKET, S3, Db

    s3 = boto3.client("s3", **S3)
    with Db() as db:
        video = db.get(Video, uuid.UUID(video_id))
        if video is None:
            return
        url = s3.generate_presigned_url("get_object", Params={"Bucket": BUCKET, "Key": video.storage_key}, ExpiresIn=600)
        family = "rear" if video.slot == "rear" else "side"
        try:
            frames, _, w, h = sample_frames(url)
            kp, sc = pose(frames, os.environ.get("PIPELINE_DEVICE", "cpu")) if frames else (np.zeros((0, 13, 2)), np.zeros((0, 13)))
            verdict = judge(frames, kp, sc, family, w, h)
        except (cv2.error, subprocess.SubprocessError, ValueError) as e:
            verdict = {"outcome": "rejected", "reason": "unreadable", "warnings": [], "error": str(e)[:200]}
        verdict["checked_at"] = datetime.now(UTC).isoformat()
        video.check_result = {**(video.check_result or {}), **verdict}
        if family == "side" and verdict.get("view"):
            video.view = verdict["view"]
        db.commit()
