// node --experimental-strip-types --test src/lib  (Node 22.6+; on by default from Node 23.6)
import assert from "node:assert/strict";
import { test } from "node:test";

import { EPS, rowAt, timeOfRow, windowEnd } from "./frames.ts";

// A slow-motion clip as the phone writes it: first frame at 0.0476 s, then a 1.6 s gap, then 30 fps,
// with 5 frames dropped after frame 150 (see worker/tests/synthetic.py).
const pts = [0.0476];
for (let i = 1; i < 300; i++) pts.push(pts[i - 1] + (i === 1 ? 1.6067 : i === 151 ? 6 / 30 : 1 / 30));

function table(start, step, rows) {
  return { fps: 30 / step, container_fps: 30, start_frame: start, frame_step: step, frames: new Array(rows).fill(0), times: Array.from({ length: rows }, (_, i) => pts[start + i * step]) };
}

test("every row is found at its own presentation time", () => {
  const kp = table(100, 1, 120);
  for (let i = 0; i < 120; i++) {
    assert.equal(rowAt(kp, kp.times[i] + EPS), i);
    // and stays the shown row until the next frame's time
    const next = i + 1 < 120 ? kp.times[i + 1] : kp.times[i] + 1 / 30;
    assert.equal(rowAt(kp, (kp.times[i] + next) / 2), i);
  }
});

test("a dropped-frame gap does not shift the rows after it", () => {
  const kp = table(140, 1, 30);
  const after = 151 + 3 - 140; // row of file frame 154, after the gap
  assert.equal(rowAt(kp, pts[154] + EPS), after);
  // the fps formula would have been off by the 5 dropped frames
  const naive = Math.round(Math.round((pts[154] + EPS) * 30) - 140);
  assert.notEqual(naive, after);
});

test("rows with a frame step map to every other file frame", () => {
  const kp = table(10, 2, 50);
  assert.equal(rowAt(kp, pts[30] + EPS), 10);
  assert.equal(timeOfRow(kp, 10), pts[30]);
});

test("times before and after the window are outside it", () => {
  const kp = table(100, 1, 20);
  assert.equal(rowAt(kp, pts[99]), -1);
  assert.equal(rowAt(kp, pts[119] + 1), 20);
});

test("older analyses without times fall back to the fps formula", () => {
  const kp = { container_fps: 30, start_frame: 30, frame_step: 1, frames: new Array(60).fill(0) };
  assert.equal(rowAt(kp, 2.0), 30);
  assert.equal(timeOfRow(kp, 30), 2.0);
});

test("on a Playback Video row i is frame i, shown from i / fps", () => {
  for (const fps of [119.88, 120, 240]) {
    const kp = { fps, container_fps: 30, start_frame: 4000, frame_step: 2, frames: new Array(2400).fill(0), playback: true };
    for (const i of [0, 1, 599, 1200, 2399]) {
      assert.equal(timeOfRow(kp, i), i / fps);
      assert.equal(rowAt(kp, timeOfRow(kp, i) + EPS), i);
      assert.equal(rowAt(kp, (i + 0.85) / fps), i);
      assert.equal(rowAt(kp, i / fps - 1e-6), i); // clock rounded just below the frame's start
    }
    assert.equal(rowAt(kp, windowEnd(kp) + 0.01), kp.frames.length); // past the end: outside the window
  }
});
