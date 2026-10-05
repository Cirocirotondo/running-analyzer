"use client";

import Link from "next/link";
import { useState } from "react";

import InfoButton from "@/components/InfoButton";
import SkeletonPlayer from "@/components/SkeletonPlayer";
import { Card } from "@/components/ui";
import { SOURCES, TOPIC_BY_METRIC } from "@/content/learn";
import type { Analysis, Metric } from "@/lib/api";

const REASON_TEXT: Record<string, string> = {
  too_few_cycles: "fewer than 6 gait cycles",
  low_confidence: "keypoints not tracked reliably",
};

/** Why a value may be biased (Recording Check warnings). */
const UNRELIABLE_TEXT: Record<string, string> = {
  camera_low: "the camera was below hip height, which changes how knee, shin and foot angles look",
  camera_high: "the camera was well above hip height, which changes how knee, shin and foot angles look",
  tilted: "the phone was tilted more than we can correct",
  runner_small: "the runner is small in the frame, so each body segment spans few pixels",
};

export const VIEW_LABEL: Record<string, string> = {
  left_side: "Left side",
  right_side: "Right side",
  rear: "Rear",
  side_a: "Side",
  side_b: "Side 2",
};
const VIEW_ORDER = ["left_side", "right_side", "side_a", "side_b", "rear"];
// Display order of the Metric cards.
const ORDER = [
  "cadence", "step_length", "vertical_oscillation", "trunk_lean_midstance",
  "contact_time", "flight_time", "knee_flexion_ic", "tibia_angle_ic", "overstride", "foot_angle_ic", "foot_strike_pattern",
  "pelvic_drop", "hip_adduction", "hip_adduction_rel_pelvis",
];

type Sources = Record<string, { title: string; url: string }>;

function num(v: number, unit: string | null) {
  const digits = unit === "deg" || unit === "cm" ? 1 : 0;
  // Typographic minus: "−12.7" reads better than "-12.7" next to dashes.
  return v.toFixed(digits).replace("-", "−");
}

function suffix(unit: string | null) {
  return unit === "deg" ? "°" : unit ? ` ${unit}` : "";
}

function fmt(v: number | null, unit: string | null) {
  if (v === null) return "–";
  return `${num(v, unit)}${suffix(unit)}`;
}

/** "168–188 steps/min", or "−11.0° to −2.0°" when a bound is negative (a dash would read as a minus). */
function fmtRange(lo: number, hi: number, unit: string | null) {
  if (lo < 0 || hi < 0) return `${fmt(lo, unit)} to ${fmt(hi, unit)}`;
  return `${num(lo, unit)}–${num(hi, unit)}${suffix(unit)}`;
}

/** What this particular value means, for the metric's info popup. */
function Interpretation({ m, speed, sources, hasAdvice }: { m: Metric; speed: number; sources: Sources; hasAdvice: boolean }) {
  const side = m.side === "L" ? " (left)" : m.side === "R" ? " (right)" : "";
  if (m.state === "unmeasurable") {
    return <>Not measured in this video{side}: {REASON_TEXT[m.reason ?? ""] ?? "not available"}.</>;
  }
  const value = m.value_text ?? fmt(m.mean, m.unit);
  const spread = m.sd !== null && !m.value_text ? ` ± ${fmt(m.sd, m.unit)}` : "";
  const over = m.n_cycles ? `, averaged over ${m.n_cycles} ${m.n_cycles === 1 ? "cycle" : "cycles"}` : "";
  const perView = m.per_view && Object.keys(m.per_view).length > 1 && (
    <>
      {" "}
      Mean of the two side videos:{" "}
      {Object.entries(m.per_view)
        .map(([v, x]) => `${VIEW_LABEL[v] ?? v} ${x === null ? "–" : fmt(x, m.unit)}`)
        .join(", ")}
      . They are two separate recordings, so small differences are normal.
    </>
  );
  const unreliable = m.unreliable_reason && (
    <> Marked not reliable because {UNRELIABLE_TEXT[m.unreliable_reason] ?? m.unreliable_reason}: no advice is given on it.</>
  );
  if (m.state === "descriptor" || m.typical_low === null || m.typical_high === null || m.mean === null) {
    return (
      <>
        Your value{side}: <strong>{value}</strong>
        {spread}
        {over}. It describes your running and is not compared with a typical range.
        {perView}
        {unreliable}
      </>
    );
  }
  const where = m.mean < m.typical_low ? "below" : m.mean > m.typical_high ? "above" : "within";
  const src = m.source_id ? (sources[m.source_id]?.title ?? SOURCES[m.source_id]?.cite)?.split(",")[0] : null;
  return (
    <>
      Your value{side}: <strong>{value}</strong>
      {spread}
      {over}. Typical range{m.metric_key === "cadence" ? ` at ${speed} km/h` : ""}: {fmtRange(m.typical_low, m.typical_high, m.unit)}
      {src ? ` (${src})` : ""}. You are <strong>{where}</strong> it.
      {where !== "within" &&
        !m.unreliable_reason &&
        (hasAdvice
          ? " See the advice above."
          : m.advice_eligible
            ? ` Advice is given only when the value is ${m.metric_key === "cadence" ? "below" : "above"} the range, where research links it to higher loads.`
            : " For this metric being outside the range is not a problem by itself: the evidence is too weak to give advice.")}
      {perView}
      {unreliable}
    </>
  );
}

function RangeBar({ m, compact = false }: { m: Metric; compact?: boolean }) {
  if (m.typical_low === null || m.typical_high === null || m.mean === null) return null;
  const span = m.typical_high - m.typical_low;
  const lo = m.typical_low - span;
  const hi = m.typical_high + span;
  const pos = Math.min(100, Math.max(0, ((m.mean - lo) / (hi - lo)) * 100));
  const inRange = m.mean >= m.typical_low && m.mean <= m.typical_high;
  return (
    <div className="mt-3">
      <div className="relative h-2 rounded bg-neutral-200">
        <div className="absolute h-2 rounded bg-green-200" style={{ left: "33.3%", width: "33.3%" }} />
        <div className={`absolute -top-1 h-4 w-1 rounded ${inRange ? "bg-green-700" : "bg-amber-600"}`} style={{ left: `calc(${pos}% - 2px)` }} />
      </div>
      <div className="mt-1 flex justify-between gap-2 text-xs text-neutral-500">
        <span className="flex items-center gap-0.5">
          typical {fmtRange(m.typical_low, m.typical_high, m.unit)}
          {!compact && <InfoButton slug="typical-range" className="h-4 w-4" />}
        </span>
        <span>{inRange ? "within" : "outside"}</span>
      </div>
    </div>
  );
}

function StateBadge({ m }: { m: Metric }) {
  const badge =
    m.state === "measured" ? "bg-green-100 text-green-800" : m.state === "descriptor" ? "bg-neutral-100 text-neutral-700" : "bg-amber-100 text-amber-800";
  return (
    <span className="flex shrink-0 flex-wrap items-center justify-end gap-1">
      {m.unreliable_reason && m.state !== "unmeasurable" && (
        <span className="rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-900" title={`Not reliable: ${UNRELIABLE_TEXT[m.unreliable_reason] ?? m.unreliable_reason}`}>
          ! not reliable
        </span>
      )}
      <span className={`rounded-full px-2 py-0.5 text-xs ${badge}`}>{m.state === "unmeasurable" ? "not measurable" : m.state === "descriptor" ? "descriptive" : "measured"}</span>
      <InfoButton slug="metric-states" className="h-4 w-4" />
    </span>
  );
}

function Value({ m, size = "text-2xl" }: { m: Metric; size?: string }) {
  return (
    <div className={`mt-1 font-semibold ${size}`}>
      {m.state === "unmeasurable" ? "—" : m.value_text ?? fmt(m.mean, m.unit)}
      {m.state !== "unmeasurable" && m.sd !== null && !m.value_text && <span className="ml-1 text-sm font-normal text-neutral-500">± {fmt(m.sd, m.unit)}</span>}
    </div>
  );
}

function Footer({ m, sources }: { m: Metric; sources: Sources }) {
  const src = m.source_id ? sources[m.source_id] : null;
  return (
    <div className="mt-2 flex justify-between gap-2 text-xs text-neutral-400">
      <span className="flex items-center gap-0.5">
        {/* A classification (foot strike) has no cycle count of its own. */}
        {m.n_cycles > 0 ? `${m.n_cycles} cycles` : "from all contacts"}
        {m.mean_score !== null ? ` · confidence ${(m.mean_score * 100).toFixed(0)} %` : ""}
        <InfoButton slug="confidence" className="h-4 w-4" />
      </span>
      {src && (
        <a href={src.url} target="_blank" rel="noreferrer" className="underline">
          {src.title.split(",")[0]}
        </a>
      )}
    </div>
  );
}

function Title({ m, children }: { m: Metric; children?: React.ReactNode }) {
  const topic = TOPIC_BY_METRIC[m.metric_key];
  return (
    /* The icon stays right after the last word when the label wraps. */
    <div className="text-sm text-neutral-600">
      {m.label}
      {topic && (
        <InfoButton slug={topic.slug} className="ml-1 -mt-0.5">
          {children}
        </InfoButton>
      )}
    </div>
  );
}

/** A whole-body Metric (or a rear-view one): one value. */
function MetricCard({ m, sources, speed, hasAdvice }: { m: Metric; sources: Sources; speed: number; hasAdvice: boolean }) {
  return (
    <Card>
      <div className="flex items-start justify-between gap-2">
        <div>
          <Title m={m}>
            <Interpretation m={m} speed={speed} sources={sources} hasAdvice={hasAdvice} />
          </Title>
          {m.side !== "both" && <div className="text-xs text-neutral-400">{m.side === "L" ? "left" : "right"}</div>}
          <Value m={m} />
        </div>
        <StateBadge m={m} />
      </div>
      {m.state === "unmeasurable" && <p className="mt-2 text-xs text-neutral-500">{REASON_TEXT[m.reason ?? ""] ?? m.reason ?? "not available for this video"}</p>}
      {m.state === "measured" && <RangeBar m={m} />}
      {m.per_view && Object.keys(m.per_view).length > 1 && (
        <p className="mt-2 text-xs text-neutral-500">
          {Object.entries(m.per_view)
            .map(([v, x]) => `${VIEW_LABEL[v] ?? v}: ${x === null ? "–" : fmt(x, m.unit)}`)
            .join(" · ")}
        </p>
      )}
      <Footer m={m} sources={sources} />
    </Card>
  );
}

/** A leg Metric: left and right side by side, each from the Side View that sees that leg. */
function LegCard({ left, right, sources, speed, advice }: { left?: Metric; right?: Metric; sources: Sources; speed: number; advice: Set<string> }) {
  const any = (left ?? right)!;
  const both = left && right && left.mean !== null && right.mean !== null && left.state !== "unmeasurable" && right.state !== "unmeasurable" && !left.value_text;
  const diff = both ? right!.mean! - left!.mean! : null;
  return (
    <Card>
      <Title m={any}>
        {left && <Interpretation m={left} speed={speed} sources={sources} hasAdvice={advice.has(left.metric_key)} />}
        {left && right && <div className="my-2 border-t border-neutral-200" />}
        {right && <Interpretation m={right} speed={speed} sources={sources} hasAdvice={advice.has(right.metric_key)} />}
        {diff !== null && <> The two legs come from two separate recordings, so a difference of a few units can be recording-to-recording variation.</>}
      </Title>
      <div className="mt-2 grid grid-cols-2 gap-3">
        {(
          [
            ["Left", left, "right side"],
            ["Right", right, "left side"],
          ] as const
        ).map(([label, m, other]) => (
          <div key={label} className="min-w-0">
            <div className="text-xs font-medium uppercase tracking-wide text-neutral-400">{label}</div>
            {m ? (
              <>
                <Value m={m} size="text-xl" />
                <div className="mt-1">
                  <StateBadge m={m} />
                </div>
                {m.state === "unmeasurable" && <p className="mt-1 text-xs text-neutral-500">{REASON_TEXT[m.reason ?? ""] ?? m.reason}</p>}
                {m.state === "measured" && <RangeBar m={m} compact />}
              </>
            ) : (
              <p className="mt-2 text-xs text-neutral-500">Not recorded: add a video filmed from the runner&apos;s {label.toLowerCase()} side (opposite to the {other} video).</p>
            )}
          </div>
        ))}
      </div>
      {diff !== null && (
        <p className="mt-3 text-sm text-neutral-600">
          Right {diff >= 0 ? "+" : "−"}
          {fmt(Math.abs(diff), any.unit)} compared with left
        </p>
      )}
      <Footer m={any} sources={sources} />
    </Card>
  );
}

function MetricsGrid({ metrics, analysis, sources }: { metrics: Metric[]; analysis: Analysis; sources: Sources }) {
  const advice = new Set(analysis.advice.map((a) => a.metric_key));
  const speed = analysis.session.speed_kmh;
  const keys = [...new Set(metrics.map((m) => m.metric_key))].sort((a, b) => (ORDER.indexOf(a) + 1 || 99) - (ORDER.indexOf(b) + 1 || 99));
  return (
    <div className="grid gap-3 sm:grid-cols-2">
      {keys.map((k) => {
        const rows = metrics.filter((m) => m.metric_key === k);
        const left = rows.find((m) => m.side === "L");
        const right = rows.find((m) => m.side === "R");
        if (left || right) return <LegCard key={k} left={left} right={right} sources={sources} speed={speed} advice={advice} />;
        return rows.map((m) => <MetricCard key={`${k}-${m.side}`} m={m} sources={sources} speed={speed} hasAdvice={advice.has(k)} />);
      })}
    </div>
  );
}

export default function AnalysisView({ analysis }: { analysis: Analysis }) {
  const views = Object.keys(analysis.video_urls).sort((a, b) => VIEW_ORDER.indexOf(a) - VIEW_ORDER.indexOf(b));
  const [view, setView] = useState(views[0] ?? "left_side");
  const sources = analysis.info?.sources ?? {};
  const sideMetrics = analysis.metrics.filter((m) => m.view === "side");
  const rearMetrics = analysis.metrics.filter((m) => m.view === "rear");
  const sideViews = Object.keys(analysis.keypoints_urls).filter((v) => v === "left_side" || v === "right_side");
  const win = analysis.window?.[view];

  return (
    <div className="space-y-6">
      {views.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {views.map((v) => (
            <button key={v} className={`rounded-md px-3 py-1 text-sm ${view === v ? "bg-neutral-900 text-white" : "bg-neutral-200"}`} onClick={() => setView(v)}>
              {VIEW_LABEL[v] ?? v}
            </button>
          ))}
        </div>
      )}
      {analysis.video_urls[view] ? (
        <SkeletonPlayer key={view} videoUrl={analysis.video_urls[view]} keypointsUrl={analysis.keypoints_urls[view]} />
      ) : (
        <Card>
          <p className="text-sm text-neutral-600">The videos of this session were deleted; the metrics below are kept.</p>
        </Card>
      )}

      {analysis.advice.length > 0 && (
        <section>
          <h2 className="mb-2 flex items-center gap-1 text-lg font-semibold">
            Advice <InfoButton slug="advice" />
          </h2>
          <div className="space-y-2">
            {analysis.advice.map((a) => (
              <Card key={a.metric_key} className="border-amber-200 bg-amber-50 text-sm text-amber-900">
                {a.body}
              </Card>
            ))}
          </div>
          <p className="mt-2 text-xs text-neutral-500">Advice is given only for metrics with at least moderate evidence (cadence, vertical oscillation) and reliable values. It is not a diagnosis.</p>
        </section>
      )}

      {sideMetrics.length > 0 && (
        <section>
          <h2 className="mb-2 flex items-center gap-1 text-lg font-semibold">
            Metrics <InfoButton slug="gait-cycle" />
            <Link href="/learn" className="ml-auto text-sm font-normal text-sky-700 hover:underline">
              Guide to all metrics
            </Link>
          </h2>
          <p className="mb-3 text-sm text-neutral-600">
            {sideViews.length > 1
              ? "Each leg is measured from the video that sees it (left leg from the left-side video, right leg from the right-side video); whole-body metrics are the mean of the two."
              : sideViews.length === 1
                ? `Measured on the ${sideViews[0] === "left_side" ? "left" : "right"} leg, the one nearer the camera. To measure the ${sideViews[0] === "left_side" ? "right" : "left"} leg too, add a video filmed from the other side of the treadmill in your next session.`
                : null}
            <InfoButton slug="skeleton" className="ml-1" />
          </p>
          <MetricsGrid metrics={sideMetrics} analysis={analysis} sources={sources} />
        </section>
      )}

      {rearMetrics.length > 0 && (
        <section>
          <h2 className="mb-2 text-lg font-semibold">From behind</h2>
          <MetricsGrid metrics={rearMetrics} analysis={analysis} sources={sources} />
        </section>
      )}

      <section className="flex flex-wrap items-center gap-1 text-xs text-neutral-500">
        Pipeline {analysis.pipeline_version}
        {win && (
          <>
            {" "}
            {/* Window frames are file frames: divide by the file's real frame rate, not the analysis rate. */}
            · {VIEW_LABEL[view] ?? view}: analyzed window {(win.start_frame / (win.source_fps ?? win.fps)).toFixed(1)}–{(win.end_frame / (win.source_fps ?? win.fps)).toFixed(1)} s at {win.fps} fps
            <InfoButton slug="analyzed-window" className="h-4 w-4" />
          </>
        )}
      </section>
    </div>
  );
}
