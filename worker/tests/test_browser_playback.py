"""The end-to-end check that motivated the Playback Video (ADR 0008): in a real browser, seeking to the
time the player computes for row i shows exactly the frame row i was measured on. Needs Node and
Playwright with Chromium; point PLAYWRIGHT_DIR at a folder holding node_modules/playwright.

    PLAYWRIGHT_DIR=~/.local/share/claude-browser uv run pytest tests -m browser
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from test_frames import playback_from

PLAYWRIGHT_DIR = Path(os.environ.get("PLAYWRIGHT_DIR", "~/.local/share/claude-browser")).expanduser()
EPS = 0.002  # web/src/lib/frames.ts: the player seeks to timeOfRow(i) + EPS

pytestmark = [
    pytest.mark.browser,
    pytest.mark.skipif(shutil.which("node") is None or not (PLAYWRIGHT_DIR / "node_modules" / "playwright").exists(), reason="Node or Playwright not available"),
]


@pytest.mark.parametrize("fps", [120.0, 240.0])
def test_browser_shows_the_frame_of_each_row(phone_video, tmp_path, fps):
    path, rows = playback_from(phone_video, tmp_path, skip=140, step=2, n=60, fps=fps)
    picks = list(range(0, 60, 7)) + [59]
    (tmp_path / "times.json").write_text(json.dumps([i / fps + EPS for i in picks]))  # timeOfRow on a Playback Video
    out = subprocess.run(["node", str(Path(__file__).with_name("browser_frames.mjs")), str(path), str(tmp_path / "times.json")],
                         capture_output=True, text=True, timeout=120, check=False, env={**os.environ, "PLAYWRIGHT_DIR": str(PLAYWRIGHT_DIR)})
    assert out.returncode == 0, out.stderr
    assert json.loads(out.stdout) == [rows[i] for i in picks]
