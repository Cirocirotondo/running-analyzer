"use client";

import { useRouter } from "next/navigation";
import { use, useEffect, useState } from "react";

import AnalysisView from "@/components/AnalysisView";
import { Button, Card, ErrorBox } from "@/components/ui";
import { api, ApiError, FAILURE_TEXT, formatEta, type Analysis, type Session } from "@/lib/api";

export default function SessionPage(props: PageProps<"/sessions/[id]">) {
  const { id } = use(props.params);
  const router = useRouter();
  const [session, setSession] = useState<Session | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | undefined;
    let cancelled = false;
    const poll = async () => {
      try {
        const s = await api<Session>(`/sessions/${id}`);
        if (cancelled) return;
        setSession(s);
        if (s.state === "done" || s.state === "videos_deleted") {
          setAnalysis(await api<Analysis>(`/sessions/${id}/analysis`));
        } else if (s.state === "queued" || s.state === "processing") {
          timer = setTimeout(poll, 5000);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof ApiError ? err.message : "Could not load the session");
      }
    };
    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [id]);

  async function remove(what: "session" | "videos") {
    if (!confirm(what === "session" ? "Delete this session, its videos and analysis?" : "Delete the videos and keep the analysis?")) return;
    if (what === "session") {
      await api(`/sessions/${id}`, { method: "DELETE" });
      router.replace("/");
    } else {
      setSession(await api<Session>(`/sessions/${id}/videos`, { method: "DELETE" }));
      setAnalysis(await api<Analysis>(`/sessions/${id}/analysis`));
    }
  }

  if (error) return <ErrorBox message={error} />;
  if (!session) return <p className="text-sm text-neutral-500">Loading…</p>;

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
        <div>
          <h1 className="text-xl font-semibold">
            {session.recorded_on} · {session.speed_kmh} km/h{session.incline_pct ? ` · ${session.incline_pct} %` : ""}
          </h1>
          <p className="text-sm text-neutral-600">{session.shoes ?? "No shoes noted"}</p>
        </div>
        <div className="flex gap-2 text-sm">
          {session.state === "done" && (
            <button className="text-neutral-600 underline" onClick={() => remove("videos")}>
              Delete videos
            </button>
          )}
          <button className="text-red-700 underline" onClick={() => remove("session")}>
            Delete session
          </button>
        </div>
      </div>

      {(session.state === "queued" || session.state === "processing") && (
        <Card>
          <div className="flex items-center gap-3">
            <span className="h-3 w-3 animate-pulse rounded-full bg-neutral-800" />
            <div className="flex-1">
              <div className="flex items-baseline justify-between">
                <span className="font-medium">{session.state === "queued" ? "Waiting in the queue" : "Analyzing your run"}</span>
                {session.eta_seconds !== null && <span className="text-sm text-neutral-600">{formatEta(session.eta_seconds)} left</span>}
              </div>
              <div className="mt-2 h-2 rounded bg-neutral-200">
                <div className="h-2 rounded bg-neutral-800 transition-all" style={{ width: `${Math.max(1, session.progress_pct ?? 0)}%` }} />
              </div>
              <div className="mt-2 text-sm text-neutral-600">
                {session.state === "queued"
                  ? session.queue_position === 0
                    ? "Next in line: processing starts as soon as the current analysis finishes."
                    : `${session.queue_position ?? "?"} ${session.queue_position === 1 ? "analysis" : "analyses"} ahead of yours.`
                  : `${session.analysis_progress ?? "Starting"} · ${Math.round(session.progress_pct ?? 0)} %`}
              </div>
              <div className="mt-1 text-xs text-neutral-500">You can close this page; we will email you when it is ready.</div>
            </div>
          </div>
        </Card>
      )}

      {session.state === "failed" && (
        <Card className="border-red-200">
          {session.failure_reason === "internal_error" ? (
            <div className="font-medium text-red-800">Something went wrong on our side.</div>
          ) : (
            <>
              <div className="font-medium text-red-800">We couldn&apos;t analyze your video.</div>
              <p className="mt-1 text-sm text-neutral-700">{FAILURE_TEXT[session.failure_reason ?? ""] ?? session.failure_reason}</p>
            </>
          )}
          <FailureReport session={session} onAnswer={setSession} />
          <div className="mt-3">
            <Button onClick={() => router.push("/sessions/new")}>Record again</Button>
          </div>
        </Card>
      )}

      {session.state === "draft" && (
        <Card>
          <p className="text-sm text-neutral-700">The upload of this session was not completed.</p>
        </Card>
      )}

      {analysis && <AnalysisView analysis={analysis} />}
    </div>
  );
}

/** Failure Report (docs/SPEC.md §11): after a failure that may be our mistake, the Runner can send the
 *  Videos to the team; without an answer they are deleted after 7 days. */
function FailureReport({ session, onAnswer }: { session: Session; onAnswer: (s: Session) => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState(false);

  async function answer(send: boolean) {
    setBusy(true);
    setError(null);
    try {
      onAnswer(await api<Session>(`/sessions/${session.id}/failure-report`, { method: "POST", body: JSON.stringify({ send }) }));
      setSent(send);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Could not send your answer");
    } finally {
      setBusy(false);
    }
  }

  if (session.failure_report === "open")
    return (
      <p className="mt-3 text-sm text-neutral-700">
        <span className="font-medium">{sent ? "Thanks! " : ""}Our team will look into it.</span> We&apos;ll email you if we can analyze your videos again.
      </p>
    );
  if (session.failure_report !== "asked") return null;
  const internal = session.failure_reason === "internal_error";
  return (
    <div className="mt-3 rounded-md bg-neutral-50 p-3 text-sm">
      <p className="text-neutral-800">
        {internal ? (
          "Send your videos to our team so we can fix it? We'll delete them once it's solved."
        ) : (
          <>
            <span className="font-medium">Think it was fine?</span> Send it to our team and we&apos;ll take a look.
          </>
        )}
      </p>
      <ErrorBox message={error} />
      <div className="mt-2 flex gap-3">
        <Button disabled={busy} onClick={() => answer(true)}>
          Send to the team
        </Button>
        <button className="text-neutral-600 underline disabled:opacity-50" disabled={busy} onClick={() => answer(false)}>
          {internal ? "Delete them" : "Delete"}
        </button>
      </div>
    </div>
  );
}
