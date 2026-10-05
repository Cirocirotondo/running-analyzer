"""Recording Check decisions on hand-built skeletons (no video, no model)."""

import numpy as np

import analyze as side
from worker.checks import judge

W, H = 1080, 1920
J = {n: i for i, n in enumerate(side.NAMES)}


def runner(facing: int = -1, hip_y: float = 1100, ground: float = 1500, nose_y: float = 700, x: float = 540, frames: int = 12):
    """A standing-ish runner: facing -1 = towards the image left (the camera sees the left side)."""
    kp = np.zeros((frames, len(side.NAMES), 2))
    for s, dx in (("L", -10), ("R", 10)):
        kp[:, J[f"shoulder_{s}"]] = (x + dx, nose_y + 120)
        kp[:, J[f"hip_{s}"]] = (x + dx, hip_y)
        kp[:, J[f"knee_{s}"]] = (x + dx, (hip_y + ground) / 2)
        kp[:, J[f"ankle_{s}"]] = (x + dx, ground - 30)
        kp[:, J[f"heel_{s}"]] = (x + dx - facing * 20, ground)
        kp[:, J[f"toe_{s}"]] = (x + dx + facing * 60, ground)
    kp[:, J["nose"]] = (x + facing * 80, nose_y)
    return kp, np.full((frames, len(side.NAMES)), 0.9)


def blank(n=12):
    return [np.zeros((H, W, 3), np.uint8) for _ in range(n)]


def test_hip_height_camera_is_ok_and_the_view_follows_the_running_direction():
    kp, sc = runner(facing=-1, hip_y=1000, ground=1500)  # image centre (960) above the hips: camera at hip height
    v = judge(blank(), kp, sc, "side", W, H)
    assert v["outcome"] == "ok" and v["view"] == "left_side"
    kp, sc = runner(facing=+1, hip_y=1000, ground=1500)
    assert judge(blank(), kp, sc, "side", W, H)["view"] == "right_side"


def test_camera_on_the_floor_is_a_warning():
    kp, sc = runner(hip_y=500, ground=1000, nose_y=150)  # feet near the image centre: camera at belt level
    v = judge(blank(), kp, sc, "side", W, H)
    assert v["outcome"] == "warning" and "camera_low" in v["warnings"]


def test_head_cut_off_is_rejected():
    kp, sc = runner(nose_y=20)
    v = judge(blank(), kp, sc, "side", W, H)
    assert v["outcome"] == "rejected" and v["reason"] == "body_not_fully_visible"


def test_no_runner_is_rejected():
    kp, sc = runner()
    v = judge(blank(), kp, sc * 0.1, "side", W, H)
    assert v["reason"] == "runner_not_found"


def test_unclear_running_direction_is_rejected():
    kp, sc = runner()
    kp[::2, J["nose"], 0] = 540 + 80  # half the frames facing each way: filmed head-on or from behind
    v = judge(blank(), kp, sc, "side", W, H)
    assert v["outcome"] == "rejected" and v["reason"] == "not_side_view"


def test_small_runner_is_a_warning():
    kp, sc = runner(nose_y=1150, hip_y=1300, ground=1500)  # body 350 px of 1920
    kp[:, :, 1] -= 400  # keep the camera height plausible
    v = judge(blank(), kp, sc, "side", W, H)
    assert "runner_small" in v["warnings"]
