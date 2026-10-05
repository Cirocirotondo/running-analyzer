// Small presentational helpers shared by the pages.

import { useId } from "react";

import InfoButton from "@/components/InfoButton";

export function Button({ className = "", ...props }: React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`rounded-md bg-neutral-900 px-4 py-2 text-sm font-medium text-white hover:bg-neutral-700 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...props}
    />
  );
}

export function Field({ label, children, hint, info }: { label: string; children: React.ReactNode; hint?: string; info?: string }) {
  const id = useId();
  if (info) {
    // A button must not sit inside a <label> (tapping the label would open it), so the fields are
    // grouped under the label text instead.
    return (
      <div className="block text-sm" role="group" aria-labelledby={id}>
        <div className="mb-1 flex items-center gap-1">
          <span id={id} className="font-medium text-neutral-700">
            {label}
          </span>
          <InfoButton slug={info} />
        </div>
        {children}
        {hint && <span className="mt-1 block text-xs text-neutral-500">{hint}</span>}
      </div>
    );
  }
  return (
    <label className="block text-sm">
      <span className="mb-1 block font-medium text-neutral-700">{label}</span>
      {children}
      {hint && <span className="mt-1 block text-xs text-neutral-500">{hint}</span>}
    </label>
  );
}

export const inputClass = "w-full rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm focus:border-neutral-500 focus:outline-none";

export function ErrorBox({ message }: { message: string | null }) {
  if (!message) return null;
  return <p className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">{message}</p>;
}

export function Card({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return <div className={`rounded-lg border border-neutral-200 bg-white p-4 ${className}`}>{children}</div>;
}
