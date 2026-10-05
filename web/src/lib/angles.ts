/**
 * Joint angles drawn on the skeleton player, frame by frame.
 *
 * The formulas mirror the pipeline (prototype/analyze.py: compute_metrics, analyze_rear.py), so at an
 * initial contact the number on the video equals that cycle's value behind the Metric cards.
 * Angles are in degrees; directions for drawing are canvas radians (y grows downward).
 */

export type Pt = [number, number];
export type Row = number[][]; // [joint] = [x, y, score]

export type AngleKey = "knee" | "hip" | "tibia" | "foot" | "trunk" | "pelvis" | "adduction" | "shin";

export interface AngleMark {
  key: AngleKey;
  side: "L" | "R" | "C"; // C = whole body (trunk, pelvis)
  value: number; // degrees, signed as in the Metric definitions
  text: string;
  center: Pt;
  from: number; // reference direction (radians, canvas)
  to: number; // segment direction (radians, canvas)
}

export const ANGLE_INFO: Record<AngleKey, { label: string; help: string; view: "side" | "rear" }> = {
  knee: { label: "Knee", help: "knee flexion, 0° = straight leg", view: "side" },
  hip: { label: "Hip", help: "thigh vs vertical, + = knee ahead of the hip", view: "side" },
  tibia: { label: "Tibia", help: "shank vs vertical, + = shank leaning forward", view: "side" },
  foot: { label: "Foot", help: "heel-to-toe line vs horizontal, + = toe up", view: "side" },
  trunk: { label: "Trunk", help: "shoulders vs hips from vertical, + = leaning forward", view: "side" },
  pelvis: { label: "Pelvis", help: "hip line vs the runner's average level; the label says which side is lower", view: "rear" },
  adduction: { label: "Hip adduction", help: "thigh vs vertical, + = knee towards the midline", view: "rear" },
  shin: { label: "Tibia", help: "shin vs vertical seen from behind, + = knee nearer the midline than the ankle", view: "rear" },
};

/** Per-file constants the angles need: running direction, near leg, pelvis baseline, medial sides. */
export interface FileStats {
  view: "side" | "rear";
  roll: number; // camera roll in radians, from the worker: angles are measured against the scene's horizontal
  direction: 1 | -1; // side view: +1 runner faces image right
  nearSide: "L" | "R";
  pelvisBaseline: number; // rear view: mean hip-line tilt (camera roll + posture), degrees
  medial: { L: 1 | -1; R: 1 | -1 }; // rear view: +x is medial for that leg when 1
}

const deg = (r: number) => (r * 180) / Math.PI;
const dir = (a: Pt, b: Pt) => Math.atan2(b[1] - a[1], b[0] - a[0]); // direction a -> b
const ok = (p: number[] | undefined): p is number[] => !!p && p[0] != null && p[1] != null;

export function fileStats(joints: string[], frames: Row[], isRear: boolean, rollDeg = 0): FileStats {
  const j = (n: string) => joints.indexOf(n);
  const r = (-rollDeg * Math.PI) / 180;
  const lev = (v: number[]): number[] => [v[0] * Math.cos(r) - v[1] * Math.sin(r), v[0] * Math.sin(r) + v[1] * Math.cos(r)];
  let facing = 0;
  let leftMinusRight = 0;
  let pelvisSum = 0;
  let pelvisN = 0;
  const score = { L: 0, R: 0 };
  for (const row of frames) {
    const [hl, hr, nose] = [row[j("hip_L")], row[j("hip_R")], row[j("nose")]];
    if (ok(hl) && ok(hr)) {
      leftMinusRight += hl[0] - hr[0];
      if (ok(nose)) facing += nose[0] - (hl[0] + hr[0]) / 2;
      const [a, b] = [lev(hl), lev(hr)]; // same levelled points computeAngles measures on
      pelvisSum += deg(Math.atan2(a[1] - b[1], Math.abs(a[0] - b[0])));
      pelvisN += 1;
    }
    for (const s of ["L", "R"] as const) {
      for (const n of ["hip", "knee", "ankle", "heel", "toe"]) score[s] += row[j(`${n}_${s}`)]?.[2] ?? 0;
    }
  }
  const leftIsLeft = leftMinusRight < 0;
  return {
    view: isRear ? "rear" : "side",
    roll: (rollDeg * Math.PI) / 180,
    direction: facing >= 0 ? 1 : -1,
    nearSide: score.L >= score.R ? "L" : "R",
    pelvisBaseline: pelvisN ? pelvisSum / pelvisN : 0,
    medial: { L: leftIsLeft ? 1 : -1, R: leftIsLeft ? -1 : 1 },
  };
}

function signed(v: number) {
  const r = Math.round(v);
  return `${r > 0 ? "+" : ""}${r}°`;
}

export function computeAngles(joints: string[], row: Row, stats: FileStats, sides: ("L" | "R")[]): AngleMark[] {
  // Values are computed on points levelled for the camera roll (as the worker does for the metrics);
  // marks are drawn on the image, with the reference lines tilted by the roll.
  const c = Math.cos(-stats.roll);
  const s0 = Math.sin(-stats.roll);
  const p = (n: string): Pt | null => {
    const v = row[joints.indexOf(n)];
    return ok(v) ? [v[0] * c - v[1] * s0, v[0] * s0 + v[1] * c] : null;
  };
  const img = (q: Pt): Pt => [q[0] * c + q[1] * s0, -q[0] * s0 + q[1] * c]; // levelled -> image
  const marks: AngleMark[] = [];
  const d = stats.direction;
  const DOWN = Math.PI / 2;
  const UP = -Math.PI / 2;
  const hl = p("hip_L");
  const hr = p("hip_R");

  if (stats.view === "side") {
    for (const s of sides) {
      const [H, K, A, He, T] = ["hip", "knee", "ankle", "heel", "toe"].map((n) => p(`${n}_${s}`));
      if (H && K && A) {
        // Flexion = angle between the thigh's continuation and the shank.
        const from = dir(H, K);
        const to = dir(K, A);
        let flex = Math.abs(deg(to - from));
        if (flex > 180) flex = 360 - flex;
        marks.push({ key: "knee", side: s, value: flex, text: `${Math.round(flex)}°`, center: K, from, to });
      }
      if (H && K) {
        const v = deg(Math.atan2(d * (K[0] - H[0]), K[1] - H[1]));
        marks.push({ key: "hip", side: s, value: v, text: signed(v), center: H, from: DOWN, to: dir(H, K) });
      }
      if (K && A) {
        const v = deg(Math.atan2(d * (K[0] - A[0]), A[1] - K[1]));
        marks.push({ key: "tibia", side: s, value: v, text: signed(v), center: A, from: UP, to: dir(A, K) });
      }
      if (He && T) {
        const v = deg(Math.atan2(-(T[1] - He[1]), d * (T[0] - He[0])));
        marks.push({ key: "foot", side: s, value: v, text: signed(v), center: He, from: d > 0 ? 0 : Math.PI, to: dir(He, T) });
      }
    }
    const sl = p("shoulder_L");
    const sr = p("shoulder_R");
    if (hl && hr && sl && sr) {
      const Hm: Pt = [(hl[0] + hr[0]) / 2, (hl[1] + hr[1]) / 2];
      const Sm: Pt = [(sl[0] + sr[0]) / 2, (sl[1] + sr[1]) / 2];
      const v = deg(Math.atan2(d * (Sm[0] - Hm[0]), Hm[1] - Sm[1]));
      marks.push({ key: "trunk", side: "C", value: v, text: signed(v), center: Hm, from: UP, to: dir(Hm, Sm) });
    }
    return marks.map((m) => toImage(m, img, stats.roll));
  }

  // Rear view.
  if (hl && hr) {
    const mid: Pt = [(hl[0] + hr[0]) / 2, (hl[1] + hr[1]) / 2];
    const raw = deg(Math.atan2(hl[1] - hr[1], Math.abs(hl[0] - hr[0])));
    const v = raw - stats.pelvisBaseline; // + = left hip lower than the runner's average level
    // Reference: the average level line, drawn towards the left hip.
    const ux = Math.sign(hl[0] - mid[0]) || 1;
    const b = (stats.pelvisBaseline * Math.PI) / 180;
    const from = Math.atan2(Math.tan(b), ux);
    const lower = Math.abs(v) < 0.5 ? "" : v > 0 ? " L low" : " R low";
    marks.push({ key: "pelvis", side: "C", value: v, text: `${Math.abs(v).toFixed(1)}°${lower}`, center: mid, from, to: dir(mid, hl) });
  }
  for (const s of sides) {
    const H = s === "L" ? hl : hr;
    const K = p(`knee_${s}`);
    if (H && K) {
      const v = deg(Math.atan2(stats.medial[s] * (K[0] - H[0]), K[1] - H[1]));
      marks.push({ key: "adduction", side: s, value: v, text: signed(v), center: H, from: DOWN, to: dir(H, K) });
    }
    const A = p(`ankle_${s}`);
    if (K && A) {
      // Frontal-plane shin tilt; negative = ankle under or across the midline (narrow, "crossover" landing).
      const v = deg(Math.atan2(stats.medial[s] * (K[0] - A[0]), A[1] - K[1]));
      marks.push({ key: "shin", side: s, value: v, text: signed(v), center: A, from: UP, to: dir(A, K) });
    }
  }
  return marks.map((m) => toImage(m, img, stats.roll));
}

/** Levelled coordinates back to the image: centre rotated back, directions tilted by the roll. */
function toImage(m: AngleMark, img: (q: Pt) => Pt, roll: number): AngleMark {
  return { ...m, center: img(m.center), from: m.from + roll, to: m.to + roll };
}

/** Draws one angle: dashed reference line, filled wedge from the reference to the segment, value chip. */
export function drawAngle(ctx: CanvasRenderingContext2D, m: AngleMark, sx: number, sy: number, color: string, unit: number) {
  const cx = m.center[0] * sx;
  const cy = m.center[1] * sy;
  const r = unit * 9;
  let delta = m.to - m.from;
  while (delta > Math.PI) delta -= 2 * Math.PI;
  while (delta < -Math.PI) delta += 2 * Math.PI;

  ctx.save();
  ctx.setLineDash([unit * 1.5, unit * 1.5]);
  ctx.strokeStyle = "rgba(255,255,255,0.85)";
  ctx.lineWidth = Math.max(1, unit * 0.35);
  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.lineTo(cx + Math.cos(m.from) * r * 1.7, cy + Math.sin(m.from) * r * 1.7);
  ctx.stroke();
  ctx.setLineDash([]);

  ctx.beginPath();
  ctx.moveTo(cx, cy);
  ctx.arc(cx, cy, r, m.from, m.from + delta, delta < 0);
  ctx.closePath();
  ctx.globalAlpha = 0.28;
  ctx.fillStyle = color;
  ctx.fill();
  ctx.globalAlpha = 1;
  ctx.beginPath();
  ctx.arc(cx, cy, r, m.from, m.from + delta, delta < 0);
  ctx.strokeStyle = color;
  ctx.lineWidth = Math.max(1.5, unit * 0.5);
  ctx.stroke();

  // Value chip on the wedge's bisector, outside the arc.
  const mid = m.from + delta / 2;
  const fontPx = Math.round(unit * 3.4);
  ctx.font = `600 ${fontPx}px ui-sans-serif, system-ui, sans-serif`;
  const w = ctx.measureText(m.text).width + fontPx * 0.9;
  const h = fontPx * 1.5;
  const lx = cx + Math.cos(mid) * (r + h * 1.1) - w / 2;
  const ly = cy + Math.sin(mid) * (r + h * 1.1) - h / 2;
  ctx.fillStyle = "rgba(15,15,20,0.82)";
  ctx.beginPath();
  ctx.roundRect(lx, ly, w, h, h / 2);
  ctx.fill();
  ctx.strokeStyle = color;
  ctx.lineWidth = Math.max(1, unit * 0.3);
  ctx.stroke();
  ctx.fillStyle = "#ffffff";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(m.text, lx + w / 2, ly + h / 2 + fontPx * 0.05);
  ctx.restore();
}
