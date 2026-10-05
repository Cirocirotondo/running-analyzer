---
status: accepted (provider choice deferred, 2026-10-03)
---

# Self-hosted on an EU VPS, coded against standard interfaces

Production runs on one small EU VPS (Hetzner or OVH class, ~€6–9/month) hosting the Next.js frontend, the
FastAPI API, the Redis queue, PostgreSQL, a self-hosted Supabase Auth and the pose-estimation worker on
CPU; Videos go to an S3-compatible object storage service (Hetzner Object Storage, OVH or Backblaze B2, all
EU). We chose this over Supabase Cloud and Vercel because Videos are kept (ADR 0002) and storage dominates
cost, object storage is far cheaper per TB than any managed bundle, everything stays in the EU, and
Vercel's free plan forbids commercial use. In exchange we own backups, security updates, TLS and
monitoring. Cost analysis: [docs/hosting-cost-analysis.md](../hosting-cost-analysis.md).

The application code talks only to standard interfaces (PostgreSQL, the S3 API, JWTs issued by the auth
service, a Redis queue consumed by the worker), never to provider-specific SDKs, so that the provider is
picked on deployment day and can be changed with configuration. In development the same services run
locally with Docker Compose.

## Planned evolution

The worker is a queue consumer that reads and writes the object storage. On CPU an analysis takes 15–30
minutes (the accurate RTMPose preset does not scale with cores, see prototype/EXPERIMENTS.md); when that
latency matters, the same container moves to a serverless GPU service with an EU region (Modal, RunPod,
Koyeb, Scaleway) at a few cents per analysis, without changing the API or the queue.

## Considered Options

- Supabase Cloud for database and auth, object storage elsewhere.
- Supabase Cloud for everything: the free plan's 1 GB of file storage fills after a few Sessions, and
  free projects pause after a week of inactivity.
- Free tiers stitched together (Oracle Always Free, Cloudflare, R2, Neon): cheapest on paper, but five
  vendors, no SLA, and Oracle cut its free tier in June 2026 — not acceptable for holding people's videos.
- Dedicated GPU servers: hundreds of euros a month; serverless GPU is the only sensible GPU option.
