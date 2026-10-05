"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import InfoButton from "@/components/InfoButton";
import { ANGLE_INFO, type AngleKey, computeAngles, drawAngle, fileStats } from "@/lib/angles";
import { EPS, rowAt, timeOfRow, windowEnd as endOfWindow } from "@/lib/frames";

/** Keypoints JSON written by the worker (worker/pipeline.py: write_browser_keypoints). */
export interface Keypoints {
  fps: number;
  container_fps: number;
  start_frame: number;
  frame_step: number; // row i of frames = file frame start_frame + i * frame_step
  width: number;
  height: number;
  joints: string[];
  frames: number[][][]; // [frame][joint] = [x, y, score], cleaned (filtered) points used by the metrics
  frames_raw?: number[][][]; // the model's output before cleaning (absent in older analyses)
  times?: number[]; // container time (s) at which the browser shows row i; absent in older analyses
  roll_deg?: number | null; // camera roll the metrics were corrected for
  playback?: boolean; // the video is the Playback Video: row i is frame i at i / fps (ADR 0008)
  events: { ic?: Record<string, number[]>; to?: Record<string, number[]>; stance?: Record<string, [number, number][]> };
}

const BONES: [string, string][] = [
  ["shoulder", "hip"],
  ["hip", "knee"],
  ["knee", "ankle"],
  ["ankle", "heel"],
  ["heel", "toe"],
  ["ankle", "toe"],
];
const COLOR = { L: "#ffc800", R: "#0078ff", C: "#ff4fa3" };
const MIN_SCORE = 0.3;
// The Playback Video runs in real time; a stride lasts ~0.7 s, so the default is slow enough to follow the joints.
const DEFAULT_RATE = 0.125;
type VideoWithFrameCallback = HTMLVideoElement & {
  requestVideoFrameCallback?: (cb: (now: number, meta: { mediaTime: number }) => void) => number;
  cancelVideoFrameCallback?: (handle: number) => void;
};

export default function SkeletonPlayer({ videoUrl, keypointsUrl }: { videoUrl: string; keypointsUrl?: string }) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const boxRef = useRef<HTMLDivElement>(null);
  // Exact presentation time of the frame on screen (requestVideoFrameCallback), when the browser offers it.
  const presentedRef = useRef<{ mediaTime: number; currentTime: number } | null>(null);
  const [kp, setKp] = useState<Keypoints | null>(null);
  const [show, setShow] = useState(true);
  const [rate, setRate] = useState(DEFAULT_RATE);
  const [frameInfo, setFrameInfo] = useState("");
  const [fullscreen, setFullscreen] = useState(false);
  const [source, setSource] = useState<"filtered" | "raw">("filtered");
  const [angles, setAngles] = useState<Set<AngleKey>>(new Set(["knee", "hip", "tibia", "foot", "trunk", "pelvis", "adduction", "shin"]));
  const [legs, setLegs] = useState<"near" | "both">("near");
  const isRear = !!kp?.events.stance;
  const stats = useMemo(() => (kp ? fileStats(kp.joints, kp.frames, !!kp.events.stance, kp.roll_deg ?? 0) : null), [kp]);

  // Full screen must apply to the box holding both the video and the canvas: the browser's own
  // button on the <video> would show the video alone, without the skeleton. The button is hidden
  // where supported (controlsList); where it is not, or on double-click, we redirect to the box.
  useEffect(() => {
    const onChange = () => {
      const el = document.fullscreenElement;
      setFullscreen(el === boxRef.current);
      if (el && el === videoRef.current) {
        document
          .exitFullscreen()
          .then(() => boxRef.current?.requestFullscreen())
          .catch(() => undefined);
      }
    };
    document.addEventListener("fullscreenchange", onChange);
    return () => document.removeEventListener("fullscreenchange", onChange);
  }, []);

  const toggleFullscreen = () => {
    if (document.fullscreenElement) document.exitFullscreen().catch(() => undefined);
    else boxRef.current?.requestFullscreen().catch(() => undefined);
  };

  useEffect(() => {
    if (!keypointsUrl) return;
    fetch(keypointsUrl)
      .then((r) => r.json())
      .then(setKp)
      .catch(() => setKp(null));
  }, [keypointsUrl]);

  // Track the presentation time of the displayed frame; currentTime alone can be a frame or two off.
  useEffect(() => {
    const video = videoRef.current as VideoWithFrameCallback | null;
    if (!video?.requestVideoFrameCallback) return;
    let handle = 0;
    const onFrame = (_now: number, meta: { mediaTime: number }) => {
      presentedRef.current = { mediaTime: meta.mediaTime, currentTime: video.currentTime };
      handle = video.requestVideoFrameCallback!(onFrame);
    };
    handle = video.requestVideoFrameCallback(onFrame);
    return () => video.cancelVideoFrameCallback?.(handle);
  }, []);

  useEffect(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    let raf = 0;
    const idx = (name: string) => kp?.joints.indexOf(name) ?? -1;

    const draw = () => {
      raf = requestAnimationFrame(draw);
      if (canvas.width !== video.videoWidth || canvas.height !== video.videoHeight) {
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
      }
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      if (!kp || !show) return;
      // The frame callback's time is used only while it still matches the element's clock
      // (after a seek while paused the callback may not fire again).
      const presented = presentedRef.current;
      const t = presented && Math.abs(presented.currentTime - video.currentTime) < 0.001 ? presented.mediaTime : video.currentTime;
      const i = rowAt(kp, t);
      const fileFrame = kp.start_frame + i * (kp.frame_step || 1);
      const seconds = (fileFrame / (kp.fps * (kp.frame_step || 1))).toFixed(2);
      if (i < 0 || i >= kp.frames.length) {
        setFrameInfo(`${t.toFixed(2)} s of playback · outside the analyzed window`);
        return;
      }
      const row = (source === "raw" && kp.frames_raw ? kp.frames_raw : kp.frames)[i];
      const sx = canvas.width / kp.width;
      const sy = canvas.height / kp.height;
      // The canvas is in video pixels and shrunk by CSS (object-contain): size strokes and labels in
      // screen pixels, so they stay readable in the page and in full screen alike.
      const shown = Math.min(canvas.clientWidth / canvas.width, canvas.clientHeight / canvas.height) || 1;
      const px = 1 / shown; // video pixels per screen pixel
      ctx.lineWidth = 2.5 * px;
      for (const side of ["L", "R"] as const) {
        ctx.strokeStyle = COLOR[side];
        ctx.fillStyle = COLOR[side];
        for (const [a, b] of BONES) {
          const pa = row[idx(`${a}_${side}`)];
          const pb = row[idx(`${b}_${side}`)];
          if (!pa || !pb || pa[0] == null || pb[0] == null) continue;
          ctx.beginPath();
          ctx.moveTo(pa[0] * sx, pa[1] * sy);
          ctx.lineTo(pb[0] * sx, pb[1] * sy);
          ctx.stroke();
        }
        for (const name of ["shoulder", "hip", "knee", "ankle", "heel", "toe"]) {
          const p = row[idx(`${name}_${side}`)];
          if (!p || p[0] == null) continue;
          ctx.beginPath();
          ctx.fillStyle = p[2] < MIN_SCORE ? "#ff2a2a" : COLOR[side];
          ctx.arc(p[0] * sx, p[1] * sy, ctx.lineWidth * 2, 0, Math.PI * 2);
          ctx.fill();
        }
      }
      if (stats && angles.size) {
        // Seen from the side the far leg is often hidden, so by default only the near leg gets angles.
        const sides: ("L" | "R")[] = stats.view === "rear" || legs === "both" ? ["L", "R"] : [stats.nearSide];
        const unit = 3.5 * px; // chip text ≈ 12 screen px, arc radius ≈ 32
        for (const m of computeAngles(kp.joints, row, stats, sides)) {
          if (angles.has(m.key)) drawAngle(ctx, m, sx, sy, COLOR[m.side], unit);
        }
      }
      const hl = row[idx("hip_L")];
      const hr = row[idx("hip_R")];
      if (hl && hr && hl[0] != null && hr[0] != null && kp.events.stance) {
        ctx.strokeStyle = "#ffffff";
        ctx.beginPath();
        ctx.moveTo(hl[0] * sx, hl[1] * sy);
        ctx.lineTo(hr[0] * sx, hr[1] * sy);
        ctx.stroke();
      }
      const tags: string[] = [];
      for (const side of ["L", "R"]) {
        const tol = kp.frame_step || 1;
        if (kp.events.ic?.[side]?.some((f) => Math.abs(f - fileFrame) <= tol)) tags.push(`contact ${side}`);
        if (kp.events.to?.[side]?.some((f) => Math.abs(f - fileFrame) <= tol)) tags.push(`toe-off ${side}`);
        if (kp.events.stance?.[side]?.some(([a, b]) => fileFrame >= a && fileFrame < b)) tags.push(`stance ${side}`);
      }
      setFrameInfo(`${seconds} s · frame ${fileFrame}${tags.length ? " · " + tags.join(", ") : ""}`);
    };
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [kp, show, source, stats, angles, legs]);

  // The load algorithm resets playbackRate to defaultPlaybackRate, so set both.
  useEffect(() => {
    const v = videoRef.current;
    if (!v) return;
    v.defaultPlaybackRate = DEFAULT_RATE;
    v.playbackRate = DEFAULT_RATE;
  }, [videoUrl]);

  // Playback is confined to the analyzed window (the only part with a skeleton and metrics).
  const windowStart = kp ? timeOfRow(kp, 0) : 0;
  const windowEnd = kp ? endOfWindow(kp) : Infinity;

  useEffect(() => {
    const v = videoRef.current;
    if (!v || !kp) return;
    const clamp = () => {
      if (v.currentTime < windowStart - 0.05) v.currentTime = windowStart;
      if (v.currentTime > windowEnd) {
        v.pause();
        v.currentTime = windowStart;
      }
    };
    const start = () => {
      v.currentTime = windowStart;
    };
    if (v.readyState >= 1) start();
    v.addEventListener("loadedmetadata", start);
    v.addEventListener("timeupdate", clamp);
    v.addEventListener("seeking", clamp);
    return () => {
      v.removeEventListener("loadedmetadata", start);
      v.removeEventListener("timeupdate", clamp);
      v.removeEventListener("seeking", clamp);
    };
  }, [kp, windowStart, windowEnd]);

  const step = (rows: number) => {
    const v = videoRef.current;
    if (!v || !kp) return;
    v.pause();
    const i = Math.min(kp.frames.length - 1, Math.max(0, rowAt(kp, v.currentTime) + rows));
    // Land just inside the frame's display interval so the lookup is unambiguous.
    v.currentTime = timeOfRow(kp, i) + EPS;
  };

  return (
    <div>
      <div ref={boxRef} className="relative flex items-center justify-center overflow-hidden rounded-lg bg-black">
        <video
          ref={videoRef}
          src={videoUrl}
          controls
          controlsList="nofullscreen"
          playsInline
          className={fullscreen ? "max-h-screen max-w-full" : "max-h-[70vh] max-w-full"}
          onRateChange={(e) => setRate((e.target as HTMLVideoElement).playbackRate)}
        />
        <canvas ref={canvasRef} className="pointer-events-none absolute inset-0 h-full w-full object-contain" />
        {fullscreen && (
          <span className="pointer-events-none absolute left-3 top-3 rounded bg-black/60 px-2 py-1 font-mono text-xs text-white">{frameInfo}</span>
        )}
      </div>
      <div className="mt-2 flex flex-wrap items-center gap-3 text-sm text-neutral-600">
        <span className="flex items-center gap-1">
          <label className="flex items-center gap-1">
            <input type="checkbox" checked={show} onChange={(e) => setShow(e.target.checked)} /> Skeleton
          </label>
          <InfoButton slug="skeleton" />
        </span>
        {kp?.frames_raw && (
          <span className="flex items-center gap-1" title="Filtered: the smoothed points the metrics use. Raw: what the pose model output, before cleaning. Red points were discarded (low confidence or implausible limb length) and interpolated.">
            {(["filtered", "raw"] as const).map((s) => (
              <button key={s} className={`rounded px-2 py-0.5 ${source === s ? "bg-neutral-900 text-white" : "bg-neutral-200"}`} onClick={() => setSource(s)}>
                {s}
              </button>
            ))}
          </span>
        )}
        <span>Speed:</span>
        {[0.125, 0.25, 0.5, 1].map((r) => (
          <button
            key={r}
            className={`rounded px-2 py-0.5 ${rate === r ? "bg-neutral-900 text-white" : "bg-neutral-200"}`}
            onClick={() => {
              if (videoRef.current) videoRef.current.playbackRate = r;
              setRate(r);
            }}
          >
            {r}×
          </button>
        ))}
        <button className="rounded bg-neutral-200 px-2 py-0.5" onClick={() => step(-1)}>
          ◀ frame
        </button>
        <button className="rounded bg-neutral-200 px-2 py-0.5" onClick={() => step(1)}>
          frame ▶
        </button>
        <button className="inline-flex items-center gap-1 rounded bg-neutral-200 px-2 py-0.5" onClick={toggleFullscreen} title="Full screen with the skeleton">
          <svg viewBox="0 0 16 16" className="h-3.5 w-3.5" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round">
            <path d="M2 6V2h4M10 2h4v4M14 10v4h-4M6 14H2v-4" />
          </svg>
          Full screen
        </button>
        <span className="ml-auto font-mono text-xs">{frameInfo}</span>
      </div>
      {kp && (
        <div className="mt-2 flex flex-wrap items-center gap-2 text-sm text-neutral-600">
          <span className="flex items-center gap-0.5">
            Angles <InfoButton slug="joint-angles" />
          </span>
          {(Object.keys(ANGLE_INFO) as AngleKey[])
            .filter((k) => ANGLE_INFO[k].view === (isRear ? "rear" : "side"))
            .map((k) => (
              <button
                key={k}
                title={ANGLE_INFO[k].help}
                className={`rounded-full px-2.5 py-0.5 ${angles.has(k) ? "bg-neutral-900 text-white" : "bg-neutral-200"}`}
                onClick={() =>
                  setAngles((prev) => {
                    const next = new Set(prev);
                    if (next.has(k)) next.delete(k);
                    else next.add(k);
                    return next;
                  })
                }
              >
                {ANGLE_INFO[k].label}
              </button>
            ))}
          {!isRear && (
            <span className="ml-2 flex items-center gap-1">
              Legs:
              {(["near", "both"] as const).map((l) => (
                <button key={l} className={`rounded px-2 py-0.5 ${legs === l ? "bg-neutral-900 text-white" : "bg-neutral-200"}`} onClick={() => setLegs(l)}>
                  {l === "near" ? "near leg" : "both (far leg approximate)"}
                </button>
              ))}
            </span>
          )}
        </div>
      )}
      {kp && angles.size > 0 && (
        <p className="mt-1 text-xs text-neutral-500">
          {(Object.keys(ANGLE_INFO) as AngleKey[])
            .filter((k) => angles.has(k) && ANGLE_INFO[k].view === (isRear ? "rear" : "side"))
            .map((k) => `${ANGLE_INFO[k].label}: ${ANGLE_INFO[k].help}`)
            .join(" · ")}
          . At a contact frame the values match the Metric cards.
        </p>
      )}
      {kp && (
        <p className="mt-1 text-xs text-neutral-500">
          <InfoButton slug="analyzed-window" className="mr-0.5 h-4 w-4" />
          Red points were discarded (low confidence or implausible limb length) and replaced by interpolation. Showing the analyzed window: {(kp.start_frame / (kp.fps * (kp.frame_step || 1))).toFixed(1)}–
          {((kp.start_frame + kp.frames.length * (kp.frame_step || 1)) / (kp.fps * (kp.frame_step || 1))).toFixed(1)} s of the recording
          {kp.playback
            ? `, in real time (${Math.round(kp.fps)} frames per second; slow it down with Speed)`
            : kp.fps * (kp.frame_step || 1) > kp.container_fps + 1 &&
              ` · slow motion: 1 s of playback is ${(kp.container_fps / (kp.fps * (kp.frame_step || 1))).toFixed(3)} s of real time (${kp.fps * (kp.frame_step || 1)} fps captured, analyzed at ${kp.fps} fps)`}
          .
          {!kp.playback && kp.fps * (kp.frame_step || 1) > kp.container_fps + 1 && <InfoButton slug="slow-motion" className="ml-0.5 h-4 w-4" />}
        </p>
      )}
    </div>
  );
}
