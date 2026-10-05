import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import AppShell from "@/components/AppShell";

import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Running Analyzer",
  description: "Running technique analysis from treadmill videos",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}>
      <body className="min-h-full bg-neutral-50 text-neutral-900">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
