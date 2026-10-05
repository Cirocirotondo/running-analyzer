/**
 * Mapping between the <video> clock and keypoint rows (worker/pipeline.py: write_browser_keypoints).
 * Kept free of React so it can be tested with node --test (frames.test.mjs).
 */

export interface FrameTable {
  fps: number;
  container_fps: number;
  start_frame: number;
  frame_step: number;
  frames: unknown[];
  times?: number[];
  playback?: boolean;
}

// A frame is shown from its timestamp until the next one; a small margin absorbs float rounding.
export const EPS = 0.002;

/** Row shown at container time t. On a Playback Video row i is frame i, shown from i / fps (ADR 0008).
 *  Older analyses play the uploaded file: phones drop frames and trimmed clips start late, so when the
 *  worker recorded the real timestamps the lookup is by time; otherwise frame = time * container fps. */
export function rowAt(kp: FrameTable, t: number): number {
  if (kp.playback) {
    // A tenth of a frame of margin for float rounding of the element's clock.
    const f = Math.floor(t * kp.fps + 0.1);
    return f < 0 ? -1 : Math.min(f, kp.frames.length);
  }
  if (kp.times && kp.times.length === kp.frames.length) {
    const times = kp.times;
    if (t + EPS < times[0]) return -1;
    let lo = 0;
    let hi = times.length - 1;
    while (lo < hi) {
      const mid = (lo + hi + 1) >> 1;
      if (times[mid] <= t + EPS) lo = mid;
      else hi = mid - 1;
    }
    // Past the last analyzed frame (by more than one frame interval) means outside the window.
    const interval = kp.frame_step / kp.container_fps;
    return t > times[times.length - 1] + 1.5 * interval ? kp.frames.length : lo;
  }
  const fileFrame = Math.round(t * kp.container_fps);
  return Math.round((fileFrame - kp.start_frame) / (kp.frame_step || 1));
}

/** Time the analyzed window ends: one frame interval after its last row is shown. */
export function windowEnd(kp: FrameTable): number {
  return timeOfRow(kp, kp.frames.length - 1) + (kp.playback ? 1 / kp.fps : (kp.frame_step || 1) / kp.container_fps);
}

export function timeOfRow(kp: FrameTable, i: number): number {
  if (kp.playback) return Math.min(Math.max(i, 0), kp.frames.length - 1) / kp.fps;
  if (kp.times && kp.times.length === kp.frames.length) return kp.times[Math.min(Math.max(i, 0), kp.times.length - 1)];
  return (kp.start_frame + i * (kp.frame_step || 1)) / kp.container_fps;
}

