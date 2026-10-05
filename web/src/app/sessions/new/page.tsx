"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import InfoButton from "@/components/InfoButton";
import RecordingSetup from "@/components/RecordingSetup";
import { Button, Card, ErrorBox, Field, inputClass } from "@/components/ui";
import { api, FAILURE_TEXT, type Session, type UploadTarget, type Video } from "@/lib/api";

type Slot = "side_a" | "side_b" | "rear";

// Playback seconds, a loose pre-check: the server measures the real duration (slow motion plays 4-8x longer).
const MIN_SECONDS: Record<Slot, number> = { side_a: 20, side_b: 20, rear: 6 };
const SLOTS: { slot: Slot; title: string; hint: string; required: boolean }[] = [
  { slot: "side_a", title: "Side video", hint: "Filmed from one side of the treadmill. It measures the leg nearer the camera.", required: true },
  { slot: "side_b", title: "Side video from the other side", hint: "Optional. Filmed from the other side of the treadmill, to measure the other leg too.", required: false },
  { slot: "rear", title: "Rear video", hint: "Optional. Filmed from directly behind the belt.", required: false },
];

const VIEW_TEXT: Record<string, string> = { left_side: "left side of the runner", right_side: "right side of the runner", rear: "rear view" };

/** What a Recording Check warning means for the Runner, and what to do about it. */
const WARNING_TEXT: Record<string, string> = {
  camera_low: "The camera was below hip height: knee, shin and foot angles will be marked not reliable. For accurate angles, film again with the phone at hip height.",
  camera_high: "The camera was well above hip height: knee, shin and foot angles will be marked not reliable. Lower the phone to hip height.",
  tilted: "The phone was tilted. Keep it upright and level (use the camera grid).",
  runner_small: "The runner is small in the frame. Move the phone closer (3–4 m) or use the main camera instead of the 0.5× lens.",
};

const REJECT_TEXT: Record<string, string> = {
  runner_not_found: "No runner was found in the video. Make sure the whole body is in frame.",
  body_not_fully_visible: "The head or the feet are out of the frame. Move the phone back, leaving room above the head and below the feet.",
  not_side_view: "The running direction cannot be recognized: film from the side, with the phone perpendicular to the belt.",
  unreadable: "The file could not be read as a video.",
};

function probe(file: File): Promise<{ duration: number; width: number; height: number }> {
  return new Promise((resolve, reject) => {
    const video = document.createElement("video");
    video.preload = "metadata";
    video.onloadedmetadata = () => {
      resolve({ duration: video.duration, width: video.videoWidth, height: video.videoHeight });
      URL.revokeObjectURL(video.src);
    };
    video.onerror = () => reject(new Error("This file cannot be read as a video"));
    video.src = URL.createObjectURL(file);
  });
}

function putWithProgress(url: string, file: File, onProgress: (pct: number) => void): Promise<void> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("PUT", url);
    xhr.setRequestHeader("Content-Type", "video/mp4");
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(Math.round((e.loaded / e.total) * 100));
    xhr.onload = () => (xhr.status < 300 ? resolve() : reject(new Error(`Upload failed (${xhr.status})`)));
    xhr.onerror = () => reject(new Error("Upload failed: network error"));
    xhr.send(file);
  });
}

function outcomeOf(v: Video | undefined): string | null {
  return (v?.check_result?.outcome as string | undefined) ?? null;
}

function SlotCard({
  spec,
  video,
  progress,
  error,
  sameSide,
  onFile,
  onRemove,
}: {
  spec: (typeof SLOTS)[number];
  video?: Video;
  progress?: number;
  error?: string;
  sameSide: boolean;
  onFile: (f: File) => void;
  onRemove: () => void;
}) {
  const outcome = outcomeOf(video);
  const check = video?.check_result ?? {};
  const warnings = (check.warnings as string[] | undefined) ?? [];
  const uploading = progress !== undefined;
  return (
    <Card className="space-y-2">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-medium">
            {spec.title} {spec.required && <span className="text-sm font-normal text-neutral-500">(required)</span>}
          </div>
          <p className="text-xs text-neutral-500">{spec.hint}</p>
        </div>
        {video?.uploaded && !uploading && (
          <button type="button" className="shrink-0 text-sm text-neutral-600 underline" onClick={onRemove}>
            Remove
          </button>
        )}
      </div>

      {uploading && (
        <div>
          <div className="mb-1 flex justify-between text-sm">
            <span>Uploading</span>
            <span>{progress} %</span>
          </div>
          <div className="h-2 rounded bg-neutral-200">
            <div className="h-2 rounded bg-neutral-800" style={{ width: `${progress}%` }} />
          </div>
        </div>
      )}
      {!uploading && video?.uploaded && outcome === "pending" && <p className="text-sm text-neutral-600">Checking the recording…</p>}
      {!uploading && video?.uploaded && outcome === "ok" && (
        <p className="text-sm text-green-800">✓ Recording OK{video.view in VIEW_TEXT ? ` · ${VIEW_TEXT[video.view]}` : ""}</p>
      )}
      {!uploading && video?.uploaded && outcome === "warning" && (
        <div className="rounded-md border border-amber-200 bg-amber-50 p-2 text-sm text-amber-900">
          <div className="font-medium">⚠ Usable, with a problem{video.view in VIEW_TEXT ? ` · ${VIEW_TEXT[video.view]}` : ""}</div>
          <ul className="mt-1 list-disc pl-5">
            {warnings.map((w) => (
              <li key={w}>{WARNING_TEXT[w] ?? w}</li>
            ))}
          </ul>
          <p className="mt-1">You can analyze it as it is, or replace the video below.</p>
        </div>
      )}
      {!uploading && (error || (video?.uploaded && outcome === "rejected")) && (
        <p className="rounded-md border border-red-200 bg-red-50 p-2 text-sm text-red-800">
          ✗ {error ?? REJECT_TEXT[check.reason as string] ?? FAILURE_TEXT[check.reason as string] ?? (check.reason as string)}
        </p>
      )}
      {sameSide && <p className="text-sm text-red-800">✗ Both side videos show the same side of the runner. Replace one with a video from the other side.</p>}

      {!uploading && (
        <label className="block text-sm">
          <span className="sr-only">{spec.title}</span>
          <input
            className={inputClass}
            type="file"
            accept="video/mp4,video/quicktime,.mp4,.mov"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onFile(f);
              e.target.value = "";
            }}
          />
          {video?.uploaded && <span className="mt-1 block text-xs text-neutral-500">Choose another file to replace this video.</span>}
        </label>
      )}
    </Card>
  );
}

export default function NewSessionPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    recorded_on: new Date().toISOString().slice(0, 10),
    speed_kmh: "",
    speed_unit: "kmh",
    incline_pct: "0",
    shoes: "",
    improvement_consent: false,
    processing_consent: false,
  });
  const [session, setSession] = useState<Session | null>(null);
  const [progress, setProgress] = useState<Partial<Record<Slot, number>>>({});
  const [slotErrors, setSlotErrors] = useState<Partial<Record<Slot, string>>>({});
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const video = (slot: Slot) => session?.videos.find((v) => v.slot === slot);
  const pending = session?.videos.some((v) => v.uploaded && outcomeOf(v) === "pending") ?? false;

  // Poll while a Recording Check is running (a few seconds per Video).
  useEffect(() => {
    if (!session || !pending) return;
    const t = setTimeout(async () => setSession(await api<Session>(`/sessions/${session.id}`)), 2000);
    return () => clearTimeout(t);
  }, [session, pending]);

  async function start(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const speed = Number(form.speed_kmh) * (form.speed_unit === "mph" ? 1.609344 : 1);
      const created = await api<{ session: Session; uploads: UploadTarget[] }>("/sessions", {
        method: "POST",
        body: JSON.stringify({
          recorded_on: form.recorded_on,
          speed_kmh: Math.round(speed * 10) / 10,
          incline_pct: Number(form.incline_pct),
          shoes: form.shoes || null,
          side_videos: 2,
          rear_view: true,
          improvement_consent: form.improvement_consent,
          processing_consent: form.processing_consent,
        }),
      });
      setSession(created.session);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the session");
    } finally {
      setBusy(false);
    }
  }

  async function upload(slot: Slot, f: File) {
    if (!session) return;
    setSlotErrors((e) => ({ ...e, [slot]: undefined }));
    try {
      // A quick duration pre-check when the browser can decode the file. Phones record HEVC, which some
      // browsers cannot open: then the server's own check (it reads the real frame rate too) decides.
      const meta = await probe(f).catch(() => null);
      if (meta && meta.duration < MIN_SECONDS[slot]) throw new Error(`The video must be at least ${MIN_SECONDS[slot]} s long.`);
      // A fresh URL every time: it also resets a previous upload of this slot.
      const target = await api<UploadTarget>(`/sessions/${session.id}/videos/${slot}/upload-url`, { method: "POST" });
      if (f.size > target.max_bytes) throw new Error(`The video is larger than ${target.max_bytes >= 2 ** 30 ? `${+(target.max_bytes / 2 ** 30).toFixed(1)} GB` : `${Math.round(target.max_bytes / 2 ** 20)} MB`}.`);
      setProgress((p) => ({ ...p, [slot]: 0 }));
      await putWithProgress(target.url, f, (pct) => setProgress((p) => ({ ...p, [slot]: pct })));
      setSession(
        await api<Session>(`/sessions/${session.id}/videos/${slot}/uploaded`, {
          method: "POST",
          body: JSON.stringify({ size_bytes: f.size, duration_s: meta?.duration ?? null, width: meta?.width ?? null, height: meta?.height ?? null }),
        }),
      );
    } catch (err) {
      const code = err instanceof Error ? err.message : "";
      setSlotErrors((e) => ({ ...e, [slot]: REJECT_TEXT[code] ?? FAILURE_TEXT[code] ?? code }));
      setSession(await api<Session>(`/sessions/${session.id}`));
    } finally {
      setProgress((p) => ({ ...p, [slot]: undefined }));
    }
  }

  async function remove(slot: Slot) {
    if (!session) return;
    setSession(await api<Session>(`/sessions/${session.id}/videos/${slot}`, { method: "DELETE" }));
    setSlotErrors((e) => ({ ...e, [slot]: undefined }));
  }

  async function submit() {
    if (!session) return;
    setError(null);
    setBusy(true);
    try {
      await api(`/sessions/${session.id}/submit`, { method: "POST" });
      router.replace(`/sessions/${session.id}`);
    } catch (err) {
      const code = err instanceof Error ? err.message : "";
      setError(FAILURE_TEXT[code] ?? code);
      setBusy(false);
    }
  }

  const sides = [video("side_a"), video("side_b")].filter((v) => v?.uploaded);
  const sameSide = sides.length === 2 && sides[0]!.view === sides[1]!.view && sides[0]!.view !== "side";
  const rejected = session?.videos.some((v) => v.uploaded && outcomeOf(v) === "rejected") ?? false;
  const uploading = Object.values(progress).some((p) => p !== undefined);
  const canSubmit = !!session && sides.length > 0 && !pending && !rejected && !sameSide && !uploading && !busy;

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="mb-2 text-xl font-semibold">New session</h1>
      <p className="mb-6 text-sm text-neutral-600">
        One run on the treadmill at a constant speed. A side video is required; a second side video (from the other side) and a rear video are optional.
      </p>

      {/* Recording Guide, collapsed: the Recording Check flags the serious mistakes after the upload. */}
      <details className="group mb-6 rounded-lg border border-neutral-200 bg-neutral-50 p-4 text-sm text-neutral-700">
        <summary className="cursor-pointer list-none">
          <span className="font-medium text-neutral-900">How to record:</span> phone at hip height, 3–4 m away, whole body in frame, 60 fps or more.{" "}
          <span className="whitespace-nowrap text-sky-700 underline group-open:hidden">Show all</span>
          <span className="hidden whitespace-nowrap text-sky-700 underline group-open:inline">Hide</span>
        </summary>
        <div className="mt-3">
          <RecordingSetup />
        </div>
        <ul className="mt-3 list-disc space-y-1 pl-5">
          <li>
            <strong>Phone at hip height</strong> (on a tripod, a bench or a box), 3–4 m from the treadmill, perpendicular to the belt.
            Never on the floor or on a neighbouring treadmill: from below, knee and foot angles come out 4–9° wrong.
          </li>
          <li>Phone upright and level: use the camera grid. A tilted phone shifts trunk, shin and foot angles by as much (we correct small tilts).</li>
          <li>Whole body in frame with margin above the head and below the feet; nothing between camera and legs.</li>
          <li>Main camera (no 0.5× ultra-wide). 60 fps or more, or slow motion applied to the whole clip.</li>
          <li>Only the leg nearer the camera is measured from the side. For both legs, film once from each side of the treadmill, on the same day.</li>
          <li>Rear view: from directly behind the belt, at hip height, about 2 m away.</li>
        </ul>
      </details>

      {!session ? (
        <form onSubmit={start} className="space-y-5">
          <Card className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <Field label="Date">
                <input className={inputClass} type="date" required value={form.recorded_on} onChange={(e) => setForm({ ...form, recorded_on: e.target.value })} />
              </Field>
              <Field label="Treadmill speed" info="your-data">
                <div className="flex gap-2">
                  <input className={inputClass} type="number" step="0.1" min={1} required value={form.speed_kmh} onChange={(e) => setForm({ ...form, speed_kmh: e.target.value })} />
                  <select className={`${inputClass} w-28`} value={form.speed_unit} onChange={(e) => setForm({ ...form, speed_unit: e.target.value })}>
                    <option value="kmh">km/h</option>
                    <option value="mph">mph</option>
                  </select>
                </div>
              </Field>
              <Field label="Incline (%)">
                <input className={inputClass} type="number" step="0.5" value={form.incline_pct} onChange={(e) => setForm({ ...form, incline_pct: e.target.value })} />
              </Field>
              <Field label="Shoes (optional)">
                <input className={inputClass} placeholder="Brand and model" value={form.shoes} onChange={(e) => setForm({ ...form, shoes: e.target.value })} />
              </Field>
            </div>
          </Card>

          <Card className="space-y-2 text-sm">
            <label className="flex items-start gap-2">
              <input type="checkbox" className="mt-1" checked={form.processing_consent} onChange={(e) => setForm({ ...form, processing_consent: e.target.checked })} />
              <span>I consent to the processing of these videos to produce my analysis. They stay stored in the EU until I delete them.</span>
            </label>
            <label className="flex items-start gap-2">
              <input type="checkbox" className="mt-1" checked={form.improvement_consent} onChange={(e) => setForm({ ...form, improvement_consent: e.target.checked })} />
              <span>Optional: allow the team to view this session&apos;s videos to improve the analysis.</span>
            </label>
          </Card>

          <ErrorBox message={error} />
          <Button type="submit" disabled={busy || !form.processing_consent}>
            Continue to the videos
          </Button>
        </form>
      ) : (
        <div className="space-y-4">
          <p className="text-sm text-neutral-600">Each video is checked a few seconds after the upload: you can replace it before analyzing.</p>
          {SLOTS.map((spec) => (
            <SlotCard
              key={spec.slot}
              spec={spec}
              video={video(spec.slot)}
              progress={progress[spec.slot]}
              error={slotErrors[spec.slot]}
              sameSide={sameSide && spec.slot === "side_b"}
              onFile={(f) => upload(spec.slot, f)}
              onRemove={() => remove(spec.slot)}
            />
          ))}
          <ErrorBox message={error} />
          <div className="flex items-center gap-2">
            <Button type="button" disabled={!canSubmit} onClick={submit}>
              {pending ? "Checking the videos…" : "Analyze"}
            </Button>
            <InfoButton slug="metric-states" />
          </div>
        </div>
      )}
    </div>
  );
}
