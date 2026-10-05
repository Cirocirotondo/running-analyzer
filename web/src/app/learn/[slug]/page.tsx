import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";

import RichText from "@/components/RichText";
import { GROUP_TITLE, SOURCES, TOPIC_BY_SLUG, TOPICS, figureFile } from "@/content/learn";

export function generateStaticParams() {
  return TOPICS.map((t) => ({ slug: t.slug }));
}

export const dynamicParams = false;

export async function generateMetadata(props: PageProps<"/learn/[slug]">): Promise<Metadata> {
  const { slug } = await props.params;
  const topic = TOPIC_BY_SLUG[slug];
  return topic ? { title: `${topic.title} · Running Analyzer`, description: topic.short } : {};
}

export default async function LearnTopic(props: PageProps<"/learn/[slug]">) {
  const { slug } = await props.params;
  const topic = TOPIC_BY_SLUG[slug];
  if (!topic) notFound();
  const fig = topic.figure ? figureFile(topic.figure.name) : null;
  const portrait = fig ? fig.height > fig.width : false;

  return (
    <article className="mx-auto max-w-3xl">
      <nav className="text-sm text-neutral-500">
        <Link href="/learn" className="hover:underline">
          Guide
        </Link>{" "}
        / {GROUP_TITLE[topic.group]}
      </nav>
      <h1 className="mt-2 text-2xl font-semibold">{topic.title}</h1>
      <p className="mt-2 text-lg text-neutral-700">{topic.short}</p>
      {topic.why && <p className="mt-1 text-neutral-500">{topic.why}</p>}

      {topic.figure && fig && (
        <figure className={`mt-6 ${portrait ? "mx-auto max-w-sm" : ""}`}>
          <Image
            src={fig.src}
            alt={topic.figure.alt}
            width={fig.width}
            height={fig.height}
            sizes={portrait ? "(max-width: 640px) 100vw, 384px" : "(max-width: 768px) 100vw, 768px"}
            className="h-auto w-full rounded-lg bg-neutral-200"
            // Already sized and compressed by prototype/learn_figures.py; served as is, so the
            // content-versioned URL is what browsers cache.
            unoptimized
            priority
          />
          <figcaption className="mt-2 text-sm text-neutral-500">{topic.figure.caption}</figcaption>
        </figure>
      )}

      <div className="mt-6 space-y-8 leading-relaxed text-neutral-800">
        {topic.sections.map((s) => (
          <section key={s.heading}>
            <h2 className="mb-2 text-lg font-semibold">{s.heading}</h2>
            <RichText text={s.body} />
          </section>
        ))}
      </div>

      {topic.related && topic.related.length > 0 && (
        <section className="mt-10">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">Related</h2>
          <div className="flex flex-wrap gap-2">
            {topic.related
              .map((r) => TOPIC_BY_SLUG[r])
              .filter(Boolean)
              .map((r) => (
                <Link key={r.slug} href={`/learn/${r.slug}`} className="rounded-full border border-neutral-300 bg-white px-3 py-1 text-sm hover:bg-neutral-100">
                  {r.title}
                </Link>
              ))}
          </div>
        </section>
      )}

      {topic.sources && topic.sources.length > 0 && (
        <section className="mt-10 border-t border-neutral-200 pt-4">
          <h2 className="mb-2 text-sm font-semibold uppercase tracking-wide text-neutral-500">Sources</h2>
          <ol className="list-decimal space-y-1 pl-5 text-sm text-neutral-600">
            {topic.sources.map((id) => {
              const s = SOURCES[id];
              if (!s) return null;
              return (
                <li key={id}>
                  {s.url ? (
                    <a href={s.url} target="_blank" rel="noreferrer" className="hover:underline">
                      {s.cite}
                    </a>
                  ) : (
                    s.cite
                  )}
                </li>
              );
            })}
          </ol>
        </section>
      )}

      <p className="mt-10 text-xs text-neutral-500">
        Example images come from a volunteer test runner, with the face blurred. Reference values are group averages from published studies, not individual thresholds, and this guide is not medical advice.
      </p>
    </article>
  );
}
