import type { Metadata } from "next";
import Link from "next/link";

import { GROUP_TITLE, TOPICS, type Group } from "@/content/learn";

export const metadata: Metadata = {
  title: "Guide · Running Analyzer",
  description: "What each running metric means, how it is measured from video, and what research says about it.",
};

export default function LearnIndex() {
  const groups: Group[] = ["side", "rear", "concepts"];
  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-semibold">Guide</h1>
      <p className="mt-2 text-neutral-600">What each metric means, how we measure it from your video, and what research says about it.</p>
      {groups.map((g) => (
        <section key={g} className="mt-8">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">{GROUP_TITLE[g]}</h2>
          <ul className="divide-y divide-neutral-200 rounded-lg border border-neutral-200 bg-white">
            {TOPICS.filter((t) => t.group === g).map((t) => (
              <li key={t.slug}>
                <Link href={`/learn/${t.slug}`} className="block px-4 py-3 hover:bg-neutral-50">
                  <div className="font-medium">{t.title}</div>
                  <div className="mt-0.5 text-sm text-neutral-600">{t.short}</div>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
