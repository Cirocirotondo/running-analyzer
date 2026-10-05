"""Regression test on a real slow-motion clip (Simone's, kept outside git in data/fixtures).

Runs the worker's side-view analysis with the real pose model and compares the Metrics with the values
recorded when the clip was added. Run locally, on the GPU if there is one:

    cd prototype && PIPELINE_DEVICE=cuda uv run --with pytest pytest ../worker/tests -m slow

Record new expected values after a deliberate pipeline change with RECORD=1.
"""

import json
import os
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[2] / "data" / "fixtures"
CLIP = FIXTURES / "side_left_hip.mp4"
EXPECTED = FIXTURES / "side_left_hip.expected.json"
# Within-clip spread on 10-04 was cadence ±0.2–1.4, angles ±0.4–2°, contact ±3–8 ms; allow a bit more.
TOLERANCE = {"cadence": 2.0, "step_length": 3.0, "contact_time": 10.0, "flight_time": 10.0, "knee_flexion_ic": 2.0,
             "tibia_angle_ic": 1.5, "foot_angle_ic": 2.0, "overstride": 3.0, "trunk_lean_midstance": 1.5, "vertical_oscillation": 1.0}

pytestmark = [pytest.mark.slow, pytest.mark.skipif(not CLIP.exists(), reason=f"{CLIP} not present (kept outside git)")]


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    from worker import pipeline

    out = tmp_path_factory.mktemp("out")
    _, _, _, _, capture = pipeline.side.probe(CLIP)
    res = pipeline.analyze_side(CLIP, out, speed_kmh=13.7, height_cm=179, progress=lambda *a, **k: None, fps=float(capture))
    return res, out


def test_near_leg_and_metrics_match_the_recorded_values(result):
    res, _ = result
    got = {k: v["mean"] for k, v in res["metrics"].items() if isinstance(v, dict) and v.get("mean") is not None}
    assert res["info"]["near_side"] == "L"  # the clip shows the runner's left side
    if os.environ.get("RECORD") or not EXPECTED.exists():
        EXPECTED.write_text(json.dumps(got, indent=1, sort_keys=True))
        pytest.skip(f"recorded expected values in {EXPECTED}")
    expected = json.loads(EXPECTED.read_text())
    for key, value in expected.items():
        base = key[:-2] if key[-2:] in ("_L", "_R") else key
        assert got.get(key) == pytest.approx(value, abs=TOLERANCE[base]), key


def test_playback_video_has_a_frame_for_every_row(result):
    import cv2

    res, out = result
    doc = json.loads((out / "keypoints.json").read_text())
    cap = cv2.VideoCapture(str(out / "playback.mp4"))
    assert doc["playback"] is True
    assert int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) == len(doc["frames"])
    assert cap.get(cv2.CAP_PROP_FPS) == pytest.approx(doc["fps"], rel=1e-3)
    assert res["window"]["start_frame"] == doc["start_frame"]
