"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";

import { TOPIC_BY_SLUG } from "@/content/learn";

const WIDTH = 320;
const MARGIN = 12;

type Position = { left: number; top?: number; bottom?: number; maxHeight: number };

/**
 * A small "i" button that opens a short explanation of a term, with a link to its Learn page.
 * Opens on tap or click (no hover: most runners use a phone), closes on Escape, outside tap or
 * the close button. `children` adds content specific to the current value (e.g. "your value is...").
 */
export default function InfoButton({ slug, children, className = "" }: { slug: string; children?: ReactNode; className?: string }) {
  const topic = TOPIC_BY_SLUG[slug];
  const id = useId();
  const buttonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLDivElement>(null);
  const [pos, setPos] = useState<Position | null>(null);
  const open = pos !== null;

  const place = (): Position | null => {
    const b = buttonRef.current?.getBoundingClientRect();
    if (!b) return null;
    const width = Math.min(WIDTH, window.innerWidth - 2 * MARGIN);
    const left = Math.min(Math.max(b.left + b.width / 2 - width / 2, MARGIN), window.innerWidth - width - MARGIN);
    // On the side of the button with more room, never taller than that room (it scrolls inside).
    const below = window.innerHeight - b.bottom - 8 - MARGIN;
    const above = b.top - 8 - MARGIN;
    return below >= Math.min(above, 360)
      ? { left, top: b.bottom + 8, maxHeight: below }
      : { left, bottom: window.innerHeight - b.top + 8, maxHeight: above };
  };

  useEffect(() => {
    if (!open) return;
    const onPointer = (e: PointerEvent) => {
      const t = e.target as Node;
      if (!panelRef.current?.contains(t) && !buttonRef.current?.contains(t)) setPos(null);
    };
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setPos(null);
        buttonRef.current?.focus();
      }
    };
    const onMove = () => setPos(place());
    document.addEventListener("pointerdown", onPointer);
    document.addEventListener("keydown", onKey);
    window.addEventListener("resize", onMove);
    window.addEventListener("scroll", onMove, true);
    return () => {
      document.removeEventListener("pointerdown", onPointer);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("resize", onMove);
      window.removeEventListener("scroll", onMove, true);
    };
  }, [open]);

  if (!topic) return null;

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        aria-label={`About ${topic.title}`}
        aria-expanded={open}
        aria-controls={open ? id : undefined}
        onClick={(e) => {
          e.stopPropagation();
          setPos(open ? null : place());
        }}
        className={`inline-flex h-5 w-5 shrink-0 items-center justify-center rounded-full align-middle text-neutral-400 hover:text-neutral-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sky-600 ${open ? "text-neutral-800" : ""} ${className}`}
      >
        <svg viewBox="0 0 20 20" className="h-4 w-4" aria-hidden="true">
          <circle cx="10" cy="10" r="8.25" fill="none" stroke="currentColor" strokeWidth="1.5" />
          <circle cx="10" cy="6.3" r="1.1" fill="currentColor" />
          <rect x="9.15" y="8.6" width="1.7" height="6" rx="0.85" fill="currentColor" />
        </svg>
      </button>
      {open &&
        createPortal(
          <div
            ref={panelRef}
            id={id}
            role="dialog"
            aria-label={topic.title}
            style={{ left: pos.left, top: pos.top, bottom: pos.bottom, maxHeight: pos.maxHeight, width: Math.min(WIDTH, window.innerWidth - 2 * MARGIN) }}
            className="fixed z-50 overflow-y-auto overscroll-contain rounded-lg border border-neutral-200 bg-white p-4 text-left text-sm font-normal text-neutral-700 shadow-lg"
          >
            <div className="flex items-start justify-between gap-2">
              <div className="font-semibold text-neutral-900">{topic.title}</div>
              <button type="button" aria-label="Close" onClick={() => setPos(null)} className="-mr-1 -mt-1 rounded px-1 text-lg leading-none text-neutral-400 hover:text-neutral-800">
                ×
              </button>
            </div>
            <p className="mt-1">{topic.short}</p>
            {topic.why && <p className="mt-2 text-neutral-500">{topic.why}</p>}
            {children && <div className="mt-3 rounded-md bg-neutral-50 p-2.5 text-neutral-800">{children}</div>}
            <Link href={`/learn/${topic.slug}`} className="mt-3 inline-block font-medium text-sky-700 hover:underline" onClick={() => setPos(null)}>
              Learn more →
            </Link>
          </div>,
          document.body,
        )}
    </>
  );
}
