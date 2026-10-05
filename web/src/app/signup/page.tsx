"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { Button, ErrorBox, Field, inputClass } from "@/components/ui";
import { signup } from "@/lib/api";

export default function SignupPage() {
  const router = useRouter();
  const [form, setForm] = useState({ email: "", password: "", invite_code: "" });
  const [consents, setConsents] = useState({ accept_terms: false, accept_privacy: false, accept_disclaimer: false, is_adult: false });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const allConsents = Object.values(consents).every(Boolean);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signup({ ...form, ...consents });
      router.replace("/profile?first=1");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-up failed");
    } finally {
      setBusy(false);
    }
  }

  const consentRow = (key: keyof typeof consents, text: React.ReactNode) => (
    <label className="flex items-start gap-2 text-sm">
      <input type="checkbox" className="mt-1" checked={consents[key]} onChange={(e) => setConsents({ ...consents, [key]: e.target.checked })} />
      <span>{text}</span>
    </label>
  );

  return (
    <div className="mx-auto mt-12 max-w-sm">
      <h1 className="mb-6 text-xl font-semibold">Create an account</h1>
      <form onSubmit={submit} className="space-y-4">
        <Field label="Invite code" hint="The beta is invite-only.">
          <input className={`${inputClass} uppercase`} value={form.invite_code} onChange={(e) => setForm({ ...form, invite_code: e.target.value })} required />
        </Field>
        <Field label="Email">
          <input className={inputClass} type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} required autoComplete="email" />
        </Field>
        <Field label="Password" hint="At least 8 characters.">
          <input className={inputClass} type="password" minLength={8} value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required autoComplete="new-password" />
        </Field>
        <div className="space-y-2 rounded-md border border-neutral-200 bg-white p-3">
          {consentRow("is_adult", "I am 18 or older.")}
          {consentRow("accept_terms", "I accept the terms of service.")}
          {consentRow("accept_privacy", "I have read the privacy notice: my videos are stored in the EU until I delete them.")}
          {consentRow("accept_disclaimer", "I understand that the analysis is not a medical opinion.")}
        </div>
        <ErrorBox message={error} />
        <Button type="submit" disabled={busy || !allConsents} className="w-full">
          {busy ? "Creating…" : "Create account"}
        </Button>
      </form>
      <p className="mt-6 text-sm text-neutral-600">
        Already registered?{" "}
        <Link href="/login" className="underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
