"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Button, Card, ErrorBox, inputClass } from "@/components/ui";
import { api, FAILURE_TEXT } from "@/lib/api";

interface Stats {
  accounts: number;
  active_accounts_30d: number;
  sessions: number;
  failed_analyses: number;
  sessions_per_day: { day: string; sessions: number }[];
  mean_processing_seconds: number | null;
  storage_bytes: number;
  cohorts: { month: string; signups: number; active_30d: number }[];
  recording_checks: { videos: number; outcomes: Record<string, number>; rejections: Record<string, number>; warnings: Record<string, number> };
}
interface Invite { code: string; created_at: string; used_by: string | null; used_at: string | null; revoked_at: string | null }
interface AccountRow { email: string; role: string; created_at: string; last_active_at: string | null; sessions: number }
interface Failed { session_id: string; email: string; recorded_on: string; finished_at: string | null; reason: string | null; log: string | null; improvement_consent: boolean; pipeline_version: string; failure_report: "asked" | "open" | "closed" | null; failure_report_at: string | null }

type Tab = "stats" | "invites" | "accounts" | "failed";

const CHECK_LABEL: Record<string, string> = {
  ok: "OK",
  warning: "Warning",
  rejected: "Rejected",
  pending: "Pending",
  unchecked: "Not checked (before the Recording Check existed)",
  camera_low: "Camera below hip height",
  camera_high: "Camera well above hip height",
  tilted: "Phone tilted",
  runner_small: "Runner small in the frame",
  runner_not_found: "No runner found",
  body_not_fully_visible: "Head or feet out of frame",
  not_side_view: "Running direction not recognizable",
  fps_too_low: "Below 60 fps",
  too_short: "Too short",
  unreadable: "Unreadable file",
};

const date = (s: string | null) => (s ? new Date(s).toLocaleDateString() : "–");

function Counts({ title, counts }: { title: string; counts: Record<string, number> }) {
  const rows = Object.entries(counts).sort((a, b) => b[1] - a[1]);
  const max = Math.max(1, ...rows.map(([, n]) => n));
  return (
    <div>
      <h3 className="mb-2 text-sm font-medium text-neutral-700">{title}</h3>
      {rows.length === 0 && <p className="text-sm text-neutral-500">None.</p>}
      <ul className="space-y-1 text-sm">
        {rows.map(([k, n]) => (
          <li key={k} className="grid grid-cols-[1fr_auto] items-center gap-2">
            <span>
              {CHECK_LABEL[k] ?? k}
              <span className="ml-2 inline-block h-2 rounded bg-neutral-300 align-middle" style={{ width: `${(n / max) * 120}px` }} />
            </span>
            <span className="tabular-nums text-neutral-600">{n}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function StatsTab() {
  const [s, setS] = useState<Stats | null>(null);
  useEffect(() => {
    api<Stats>("/admin/stats").then(setS);
  }, []);
  if (!s) return <p className="text-sm text-neutral-500">Loading…</p>;
  const days = s.sessions_per_day; // the API returns all 30 days, zeros included
  const maxDay = Math.max(1, ...days.map((d) => d.sessions));
  const tiles: [string, string][] = [
    ["Accounts", String(s.accounts)],
    ["Active accounts (30 days)", String(s.active_accounts_30d)],
    ["Sessions", String(s.sessions)],
    ["Failed analyses", String(s.failed_analyses)],
    ["Mean processing time", s.mean_processing_seconds === null ? "–" : `${Math.round(s.mean_processing_seconds / 60)} min`],
    ["Video storage", `${(s.storage_bytes / 1e9).toFixed(1)} GB`],
  ];
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        {tiles.map(([label, value]) => (
          <Card key={label}>
            <div className="text-xs text-neutral-500">{label}</div>
            <div className="mt-1 text-2xl font-semibold tabular-nums">{value}</div>
          </Card>
        ))}
      </div>
      <Card>
        <h2 className="mb-3 font-medium">Sessions per day (last 30 days)</h2>
        <div className="flex h-32 items-end gap-1">
          {days.map((d) => (
            <div key={d.day} className="flex-1" title={`${d.day}: ${d.sessions}`}>
              <div className="rounded-t bg-neutral-800" style={{ height: `${Math.max(d.sessions ? 4 : 1, (d.sessions / maxDay) * 112)}px` }} />
            </div>
          ))}
        </div>
        <div className="mt-1 flex justify-between text-xs text-neutral-500">
          <span>{days[0].day}</span>
          <span>{days[29].day}</span>
        </div>
      </Card>
      <Card>
        <h2 className="mb-1 font-medium">Recording Check (last 90 days, {s.recording_checks.videos} videos)</h2>
        <p className="mb-3 text-xs text-neutral-500">Which recording instructions are not being followed.</p>
        <div className="grid gap-4 sm:grid-cols-3">
          <Counts title="Outcome" counts={s.recording_checks.outcomes} />
          <Counts title="Warnings" counts={s.recording_checks.warnings} />
          <Counts title="Rejections" counts={s.recording_checks.rejections} />
        </div>
      </Card>
      <Card>
        <h2 className="mb-3 font-medium">Monthly sign-up cohorts</h2>
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-neutral-500">
            <tr>
              <th className="py-1">Month</th>
              <th>Sign-ups</th>
              <th>Still active (30 days)</th>
            </tr>
          </thead>
          <tbody>
            {s.cohorts.map((c) => (
              <tr key={c.month} className="border-t border-neutral-100">
                <td className="py-1">{c.month}</td>
                <td className="tabular-nums">{c.signups}</td>
                <td className="tabular-nums">
                  {c.active_30d} ({Math.round((c.active_30d / c.signups) * 100)} %)
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

function InvitesTab() {
  const [rows, setRows] = useState<Invite[] | null>(null);
  const [count, setCount] = useState("5");
  const [fresh, setFresh] = useState<string[]>([]);
  const load = () => api<Invite[]>("/admin/invite-codes").then(setRows);
  useEffect(() => {
    api<Invite[]>("/admin/invite-codes").then(setRows);
  }, []);
  return (
    <div className="space-y-4">
      <Card className="flex flex-wrap items-end gap-3">
        <label className="text-sm">
          <span className="mb-1 block text-neutral-600">New single-use codes</span>
          <input className={`${inputClass} w-24`} type="number" min={1} max={100} value={count} onChange={(e) => setCount(e.target.value)} />
        </label>
        <Button
          onClick={async () => {
            setFresh(await api<string[]>(`/admin/invite-codes?count=${Number(count) || 1}`, { method: "POST" }));
            load();
          }}
        >
          Generate
        </Button>
        {fresh.length > 0 && <p className="w-full font-mono text-sm">{fresh.join("  ")}</p>}
      </Card>
      <Card>
        <table className="w-full text-sm">
          <thead className="text-left text-xs text-neutral-500">
            <tr>
              <th className="py-1">Code</th>
              <th>Created</th>
              <th>State</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {(rows ?? []).map((c) => (
              <tr key={c.code} className="border-t border-neutral-100">
                <td className="py-1 font-mono">{c.code}</td>
                <td>{date(c.created_at)}</td>
                <td>
                  {c.revoked_at ? "revoked" : c.used_at ? `used ${date(c.used_at)} by ${c.used_by ?? "a deleted account"}` : "unused"}
                </td>
                <td className="text-right">
                  {!c.used_at && !c.revoked_at && (
                    <button
                      className="text-red-700 underline"
                      onClick={async () => {
                        await api(`/admin/invite-codes/${c.code}/revoke`, { method: "POST" });
                        load();
                      }}
                    >
                      Revoke
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}

function AccountsTab() {
  const [rows, setRows] = useState<AccountRow[] | null>(null);
  useEffect(() => {
    api<AccountRow[]>("/admin/accounts").then(setRows);
  }, []);
  return (
    <Card>
      <table className="w-full text-sm">
        <thead className="text-left text-xs text-neutral-500">
          <tr>
            <th className="py-1">Email</th>
            <th>Signed up</th>
            <th>Last active</th>
            <th>Sessions</th>
          </tr>
        </thead>
        <tbody>
          {(rows ?? []).map((a) => (
            <tr key={a.email} className="border-t border-neutral-100">
              <td className="py-1">
                {a.email} {a.role === "admin" && <span className="ml-1 rounded bg-neutral-200 px-1 text-xs">admin</span>}
              </td>
              <td>{date(a.created_at)}</td>
              <td>{date(a.last_active_at)}</td>
              <td className="tabular-nums">{a.sessions}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}

const REPORT_LABEL: Record<string, string> = {
  asked: "Runner asked to send the videos",
  open: "Failure Report open",
  closed: "Failure Report closed",
};

function FailedTab() {
  const [rows, setRows] = useState<Failed[] | null>(null);
  const [videos, setVideos] = useState<Record<string, Record<string, string>>>({});
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const load = () => api<Failed[]>("/admin/failed-sessions").then(setRows);
  useEffect(() => {
    load();
  }, []);

  async function act(f: Failed, action: "reanalyze" | "resolve") {
    if (action === "resolve" && !confirm("Close this Failure Report and delete its videos?")) return;
    setError(null);
    try {
      await api(`/admin/sessions/${f.session_id}/${action}`, { method: "POST" });
      setNotice(action === "reanalyze" ? `Session ${f.session_id} queued again; the report closes if it succeeds.` : "Report closed, videos deleted.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    }
  }

  if (rows && rows.length === 0) return <p className="text-sm text-neutral-500">No failed analyses.</p>;
  // Open Failure Reports first: they are the ones waiting for us.
  const sorted = [...(rows ?? [])].sort((a, b) => Number(b.failure_report === "open") - Number(a.failure_report === "open"));
  return (
    <div className="space-y-3">
      <ErrorBox message={error} />
      {notice && <p className="rounded-md border border-green-200 bg-green-50 px-3 py-2 text-sm text-green-800">{notice}</p>}
      {sorted.map((f) => (
        <Card key={f.session_id} className={`space-y-2 text-sm ${f.failure_report === "open" ? "border-red-300 ring-1 ring-red-200" : ""}`}>
          {f.failure_report && (
            <div className="flex flex-wrap items-center gap-3">
              <span className={`rounded px-2 py-0.5 text-xs font-medium ${f.failure_report === "open" ? "bg-red-600 text-white" : "bg-neutral-200 text-neutral-700"}`}>
                {REPORT_LABEL[f.failure_report]}
              </span>
              {f.failure_report_at && <span className="text-xs text-neutral-500">since {date(f.failure_report_at)}</span>}
              {f.failure_report === "open" && (
                <>
                  <Button className="px-3 py-1" onClick={() => act(f, "reanalyze")}>
                    Re-analyze
                  </Button>
                  <button className="text-neutral-600 underline" onClick={() => act(f, "resolve")}>
                    Resolved
                  </button>
                </>
              )}
            </div>
          )}
          <div className="flex flex-wrap justify-between gap-2">
            <span className="font-medium">{f.email}</span>
            <span className="text-neutral-500">
              recorded {f.recorded_on} · failed {date(f.finished_at)} · {f.pipeline_version}
            </span>
          </div>
          <p>
            <span className="font-mono text-xs">{f.reason}</span> — {FAILURE_TEXT[f.reason ?? ""] ?? CHECK_LABEL[f.reason ?? ""] ?? ""}
          </p>
          {f.log && (
            <details>
              <summary className="cursor-pointer text-neutral-600">Pipeline log</summary>
              <pre className="mt-1 max-h-64 overflow-auto whitespace-pre-wrap rounded bg-neutral-100 p-2 text-xs">{f.log}</pre>
            </details>
          )}
          {f.improvement_consent ? (
            videos[f.session_id] ? (
              <p className="flex flex-wrap gap-3">
                {Object.keys(videos[f.session_id]).length === 0 && <span className="text-xs text-neutral-500">The videos have been deleted.</span>}
                {Object.entries(videos[f.session_id]).map(([view, url]) => (
                  <a key={view} href={url} target="_blank" rel="noreferrer" className="text-sky-700 underline">
                    {view} video
                  </a>
                ))}
              </p>
            ) : (
              <button
                className="text-sky-700 underline"
                onClick={async () => {
                  try {
                    const v = await api<Record<string, string>>(`/admin/sessions/${f.session_id}/videos`);
                    setVideos((m) => ({ ...m, [f.session_id]: v }));
                  } catch (err) {
                    setError(err instanceof Error ? err.message : "Could not load the videos");
                  }
                }}
              >
                Show videos (Improvement Consent given)
              </button>
            )
          ) : (
            <p className="text-xs text-neutral-500">No Improvement Consent: the videos cannot be viewed.</p>
          )}
        </Card>
      ))}
    </div>
  );
}

export default function AdminPage() {
  // useSearchParams needs a Suspense boundary in a statically rendered page.
  return (
    <Suspense>
      <Admin />
    </Suspense>
  );
}

function Admin() {
  const initial = useSearchParams().get("tab");
  const [tab, setTab] = useState<Tab>(initial === "invites" || initial === "accounts" || initial === "failed" ? initial : "stats");
  const tabs: [Tab, string][] = [
    ["stats", "Stats"],
    ["invites", "Invite codes"],
    ["accounts", "Accounts"],
    ["failed", "Failed analyses"],
  ];
  return (
    <div>
      <h1 className="mb-4 text-xl font-semibold">Admin</h1>
      <div className="mb-4 flex flex-wrap gap-2">
        {tabs.map(([t, label]) => (
          <button key={t} className={`rounded-md px-3 py-1 text-sm ${tab === t ? "bg-neutral-900 text-white" : "bg-neutral-200"}`} onClick={() => setTab(t)}>
            {label}
          </button>
        ))}
      </div>
      {tab === "stats" && <StatsTab />}
      {tab === "invites" && <InvitesTab />}
      {tab === "accounts" && <AccountsTab />}
      {tab === "failed" && <FailedTab />}
    </div>
  );
}
