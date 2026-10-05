"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";

import { Button, Card, ErrorBox, Field, inputClass } from "@/components/ui";
import { api, logout, type Me, type Runner } from "@/lib/api";

function ProfileForm() {
  const router = useRouter();
  const first = useSearchParams().get("first") === "1";
  const [runner, setRunner] = useState<Runner | null>(null);
  const [me, setMe] = useState<Me | null>(null);
  const [confirmEmail, setConfirmEmail] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [form, setForm] = useState({ display_name: "", height_cm: "", weight_kg: "", sex: "", birth_year: "" });
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    api<Me>("/me").then((m) => {
      setMe(m);
      setRunner(m.runner);
      setForm({
        display_name: m.runner.display_name ?? "",
        height_cm: m.runner.height_cm?.toString() ?? "",
        weight_kg: m.runner.weight_kg?.toString() ?? "",
        sex: m.runner.sex ?? "",
        birth_year: m.runner.birth_year?.toString() ?? "",
      });
    });
  }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const body = {
        display_name: form.display_name || null,
        height_cm: form.height_cm ? Number(form.height_cm) : null,
        weight_kg: form.weight_kg ? Number(form.weight_kg) : null,
        sex: form.sex || null,
        birth_year: form.birth_year ? Number(form.birth_year) : null,
      };
      setRunner(await api<Runner>("/me/runner", { method: "PUT", body: JSON.stringify(body) }));
      setSaved(true);
      if (first) router.replace("/sessions/new");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
    }
  }

  if (!runner) return <p className="text-sm text-neutral-500">Loading…</p>;
  const incomplete = !form.weight_kg || !form.sex || !form.birth_year;

  return (
    <div className="mx-auto max-w-md">
      <h1 className="mb-2 text-xl font-semibold">{first ? "Tell us about you" : "Profile"}</h1>
      <p className="mb-6 text-sm text-neutral-600">Height is needed to turn pixels into centimetres. The other fields pick the right reference ranges.</p>
      {incomplete && (
        <p className="mb-4 rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-800">
          Without weight, sex and birth year your analyses will be compared with general ranges and will be less accurate.
        </p>
      )}
      <Card>
        <form onSubmit={submit} className="space-y-4">
          <Field label="Name (optional)">
            <input className={inputClass} value={form.display_name} onChange={(e) => setForm({ ...form, display_name: e.target.value })} />
          </Field>
          <Field label="Height (cm)" hint="Required." info="your-data">
            <input className={inputClass} type="number" min={100} max={250} step="0.5" required value={form.height_cm} onChange={(e) => setForm({ ...form, height_cm: e.target.value })} />
          </Field>
          <Field label="Weight (kg)">
            <input className={inputClass} type="number" min={25} max={250} step="0.5" value={form.weight_kg} onChange={(e) => setForm({ ...form, weight_kg: e.target.value })} />
          </Field>
          <Field label="Sex">
            <select className={inputClass} value={form.sex} onChange={(e) => setForm({ ...form, sex: e.target.value })}>
              <option value="">Prefer not to say</option>
              <option value="female">Female</option>
              <option value="male">Male</option>
              <option value="other">Other</option>
            </select>
          </Field>
          <Field label="Birth year">
            <input className={inputClass} type="number" min={1900} max={2030} value={form.birth_year} onChange={(e) => setForm({ ...form, birth_year: e.target.value })} />
          </Field>
          <ErrorBox message={error} />
          <div className="flex items-center gap-3">
            <Button type="submit">{first ? "Save and continue" : "Save"}</Button>
            {saved && !first && <span className="text-sm text-green-700">Saved.</span>}
          </div>
        </form>
      </Card>

      {me && !first && (
        <>
          <Card className="mt-6 space-y-2">
            <h2 className="font-medium">Emails</h2>
            <label className="flex items-start gap-2 text-sm">
              <input
                type="checkbox"
                className="mt-1"
                checked={me.notify_analysis_ready}
                onChange={async (e) => setMe(await api<Me>("/me/settings", { method: "PUT", body: JSON.stringify({ notify_analysis_ready: e.target.checked }) }))}
              />
              <span>Email me when an analysis is ready.</span>
            </label>
            <p className="text-xs text-neutral-500">We always email you if an analysis fails and when your account is deleted.</p>
          </Card>

          <Card className="mt-6 space-y-3 border-red-200">
            <h2 className="font-medium text-red-800">Delete my account</h2>
            <p className="text-sm text-neutral-700">
              This deletes your account, your profile and every session, video and analysis, at once. It cannot be undone. Type your email to confirm.
            </p>
            <input className={inputClass} type="email" placeholder={me.email} value={confirmEmail} onChange={(e) => setConfirmEmail(e.target.value)} />
            <ErrorBox message={deleteError} />
            <button
              type="button"
              className="rounded-md bg-red-700 px-4 py-2 text-sm font-medium text-white hover:bg-red-800 disabled:cursor-not-allowed disabled:opacity-50"
              disabled={confirmEmail.trim().toLowerCase() !== me.email.toLowerCase()}
              onClick={async () => {
                try {
                  await api("/me", { method: "DELETE", body: JSON.stringify({ email: confirmEmail }) });
                  logout();
                  router.replace("/login?deleted=1");
                } catch (err) {
                  setDeleteError(err instanceof Error ? err.message : "Could not delete the account");
                }
              }}
            >
              Delete my account
            </button>
          </Card>
        </>
      )}
    </div>
  );
}

export default function ProfilePage() {
  return (
    <Suspense fallback={<p className="text-sm text-neutral-500">Loading…</p>}>
      <ProfileForm />
    </Suspense>
  );
}
