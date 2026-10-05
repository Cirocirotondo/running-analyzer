"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api, getToken, logout, type Me } from "@/lib/api";

const PUBLIC = ["/login", "/signup"];
// Readable without an account (shareable explanations); the nav still shows the account when signed in.
const OPEN = (path: string) => path === "/learn" || path.startsWith("/learn/");

export default function AppShell({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [me, setMe] = useState<Me | null>(null);
  const [openReports, setOpenReports] = useState(0); // Failure Reports waiting for an Admin
  const isPublic = PUBLIC.includes(pathname);
  const isOpen = OPEN(pathname);
  const ready = isPublic || isOpen || me !== null;

  useEffect(() => {
    if (isPublic) return;
    if (!getToken()) {
      if (!isOpen) router.replace("/login");
      return;
    }
    api<Me>("/me")
      .then((m) => {
        setMe(m);
        if (m.role === "admin")
          api<{ open: number }>("/admin/failure-reports/count")
            .then((c) => setOpenReports(c.open))
            .catch(() => setOpenReports(0));
        if (!isOpen && !m.runner.profile_complete && pathname !== "/profile") router.replace("/profile?first=1");
      })
      .catch(() => {
        if (isOpen) return;
        logout();
        router.replace("/login");
      });
  }, [pathname, isPublic, isOpen, router]);

  if (!ready) return <div className="p-8 text-sm text-neutral-500">Loading…</div>;

  return (
    <div className="flex min-h-full flex-col">
      <header className="border-b border-neutral-200 bg-white">
        <nav className="mx-auto flex max-w-5xl flex-wrap items-center gap-x-5 gap-y-2 px-4 py-3 text-sm">
          <Link href="/" className="font-semibold tracking-tight">
            Running Analyzer
          </Link>
          {me && (
            <>
              <Link href="/" className="text-neutral-600 hover:text-black">
                Sessions
              </Link>
              <Link href="/sessions/new" className="text-neutral-600 hover:text-black">
                New session
              </Link>
              <Link href="/profile" className="text-neutral-600 hover:text-black">
                Profile
              </Link>
              <Link href="/learn" className="text-neutral-600 hover:text-black">
                Guide
              </Link>
              {me.role === "admin" && (
                <Link href={openReports ? "/admin?tab=failed" : "/admin"} className="text-neutral-600 hover:text-black">
                  Admin
                  {openReports > 0 && (
                    <span className="ml-1 rounded-full bg-red-600 px-1.5 py-0.5 text-xs font-medium text-white" title="Open Failure Reports">
                      {openReports}
                    </span>
                  )}
                </Link>
              )}
              {/* The address does not fit next to the links on a phone. */}
              <span className="ml-auto hidden truncate text-neutral-500 md:inline">{me.email}</span>
              <button
                className="ml-auto text-neutral-600 hover:text-black md:ml-0"
                onClick={() => {
                  logout();
                  router.replace("/login");
                }}
              >
                Sign out
              </button>
            </>
          )}
          {!me && isOpen && (
            <>
              <Link href="/learn" className="text-neutral-600 hover:text-black">
                Guide
              </Link>
              <Link href="/login" className="ml-auto text-neutral-600 hover:text-black">
                Sign in
              </Link>
            </>
          )}
        </nav>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6">{children}</main>
      <footer className="border-t border-neutral-200 px-4 py-3 text-center text-xs text-neutral-500">
        Not a medical opinion. Values are compared with group averages from published studies, not with individual thresholds.
      </footer>
    </div>
  );
}
