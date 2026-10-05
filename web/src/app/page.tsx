"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import { Button, Card } from "@/components/ui";
import { api, FAILURE_TEXT, type Session } from "@/lib/api";

const STATE_LABEL: Record<string, string> = {
  draft: "Upload not finished",
  queued: "Queued",
  processing: "Processing",
  done: "Ready",
  failed: "Failed",
  videos_deleted: "Ready (videos deleted)",
};

const VIEW_NAME: Record<string, string> = { left_side: "left side", right_side: "right side", rear: "rear", side: "side" };

export default function HomePage() {
  const [sessions, setSessions] = useState<Session[] | null>(null);

  useEffect(() => {
    api<Session[]>("/sessions").then(setSessions);
  }, []);

  if (!sessions) return <p className="text-sm text-neutral-500">Loading…</p>;

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Your sessions</h1>
        <Link href="/sessions/new">
          <Button>New session</Button>
        </Link>
      </div>
      {sessions.length === 0 ? (
        <Card>
          <p className="text-sm text-neutral-600">No sessions yet. Record a side-view video on the treadmill and create your first session.</p>
        </Card>
      ) : (
        <ul className="space-y-3">
          {sessions.map((s) => (
            <li key={s.id}>
              <Link href={`/sessions/${s.id}`} className="block">
                <Card className="flex items-center justify-between hover:border-neutral-400">
                  <div>
                    <div className="font-medium">
                      {s.recorded_on} · {s.speed_kmh} km/h{s.incline_pct ? ` · ${s.incline_pct} %` : ""}
                    </div>
                    <div className="text-sm text-neutral-600">
                      {s.shoes ?? "No shoes noted"} · {s.videos.map((v) => VIEW_NAME[v.view] ?? "side").join(" + ")}
                    </div>
                  </div>
                  <div className="text-right text-sm">
                    <span
                      className={`rounded-full px-2 py-0.5 ${
                        s.state === "done" || s.state === "videos_deleted"
                          ? "bg-green-100 text-green-800"
                          : s.state === "failed"
                            ? "bg-red-100 text-red-800"
                            : "bg-neutral-100 text-neutral-700"
                      }`}
                    >
                      {STATE_LABEL[s.state] ?? s.state}
                    </span>
                    {s.state === "failed" && s.failure_reason && (
                      <div className="mt-1 max-w-xs text-xs text-neutral-500">{FAILURE_TEXT[s.failure_reason] ?? s.failure_reason}</div>
                    )}
                  </div>
                </Card>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
