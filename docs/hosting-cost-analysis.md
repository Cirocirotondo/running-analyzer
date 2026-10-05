# Hosting cost analysis (October 2026)

Goal: the cheapest way to run the running-analyzer platform (Next.js 16 SSR frontend, FastAPI + Redis + small PostgreSQL + self-hosted GoTrue, a video pose-estimation worker, object storage for 100–500 MB videos kept indefinitely, a few hundred transactional emails per month) for EU users whose videos are personal data.

Date of research: 2026-10-03. Prices are **excl. VAT** unless noted. Legend for confidence:

- **[V]** verified on the provider's own page or in two independent 2026 sources
- **[S]** single 2026 third-party source (plausible, re-check before signing up)
- **[E]** estimate / derived calculation

Context that changes everything in 2026: DRAM/NAND shortages caused two rounds of VPS price increases (Hetzner on 2026-04-01 and 2026-06-15, OVH 2026-04-01, Netcup 2026-04-01, Scaleway 2026-06-01). Many 2025 blog prices are stale. Oracle halved its free ARM tier on 2026-06-15. Amazon SES removed its free tier for new accounts on 2026-07-21.

---

## 1. Single VPS "all-in-one" candidates (EU)

| Provider / plan | vCPU / RAM / disk | Price per month | Location | Billing / term | CPU worker viable? |
|---|---|---|---|---|---|
| Hetzner **CX23** (replaces CX22) | 2 shared x86 / 4 GB / 40 GB NVMe, 20 TB traffic | **€5.49** + €0.50 primary IPv4 [V] (was €3.99 before June) | Falkenstein, Nuremberg, Helsinki | hourly, no term | Tight: fine for web stack; worker 10–45 min/analysis [E] |
| Hetzner **CX33** (replaces CX32) | 4 shared x86 / 8 GB / 80 GB | **€8.49** + €0.50 IPv4 [V] | same | hourly | Yes for beta; ~5–25 min/analysis [E] |
| Hetzner **CX43** | 8 / 16 GB / 160 GB | €15.99 + €0.50 [V] | same | hourly | Yes, 2 analyses in parallel |
| Hetzner **CAX11 / CAX21** (Ampere ARM) | 2 / 4 GB or 4 / 8 GB | €5.99 / €10.49 + IPv4 [V] | same | hourly | ONNX Runtime has aarch64 wheels; ARM vCPU are less oversubscribed than CX, but expect similar wall-time [E] |
| Netcup **VPS 500 G12.5** | 2 / 4 GB / 64 GB | €8.26 (12-month term; −26 % on 24 months) [V] | Nuremberg, Vienna, Amsterdam | 12-month minimum on this price; G12 hourly plans exist [S] | Yes (beta) |
| Netcup **VPS 1000 G12.5** | 4 / 8 GB / 128 GB | €14.50 [V] | same | 12 months | Yes |
| OVHcloud **VPS-1 (VPS 2027 range)** | 2 vCore / 4 GB / 40 GB NVMe, unlimited traffic | €3.81 with commitment [V]; ~€6.49 month-to-month on the 2026 range [S] | Gravelines, Strasbourg, Frankfurt, Warsaw | monthly or 12/24-month | Yes (beta) |
| OVHcloud **VPS-2** | 4 / 8 GB / 75 GB | €7.21 (commitment) [V] | same | | Yes |
| Kimsufi (OVH budget dedicated) | old dedicated hardware | from ~€5–8 [E], stock-dependent | France | monthly | Yes but old CPUs, no SLA |
| Contabo **Cloud VPS 4** | 4 / 8 GB / 100 GB SSD | €5.50 **incl. VAT** on 24-month term [V]; shorter terms cost more + setup fee [S] | Nuremberg (DE) or Lauterbourg (FR, "EU" region) | 1–24 months, prepaid | Yes, but heavily oversubscribed CPUs: worker wall-time unpredictable [S] |
| Contabo **Cloud VPS 6** | 6 / 12 GB / 200 GB | €7.50 incl. VAT (24-month) [V] | same | | Yes |
| Scaleway **STARDUST1-S** | 1 / 1 GB / 10 GB | €0.0006/h ≈ €0.43 IPv6-only; ≈ $3.3 with IPv4 [S]; frequently out of stock [E] | Paris, Amsterdam | hourly | No (1 GB RAM) |
| Scaleway **DEV1-S** | 2 / 2 GB / 20 GB | €0.00898/h ≈ €6.55 + IPv4 (~€0.004/h) + block storage [V] | Paris, Amsterdam, Warsaw | hourly | No for everything (2 GB RAM); PLAY2-NANO 2 / 4 GB is €20.10 |
| IONOS **VPS M+** | 2 / 4 GB / 120 GB | €4 for 3 months, then **€12** + €10 setup [V, ionos.de, consumer prices] | Germany (choice EU/UK/US) | 3 months, then monthly | Yes (beta) |
| IONOS **VPS S+** | 1 / 2 GB / 60 GB | €2 → €5 [V] | same | | No |

Takeaways: the cheapest *honest* month-to-month EU box with 4 GB RAM is Hetzner CX23 at €5.99 all-in; the cheapest 8 GB box is OVH VPS-2 (€7.21, commitment) or Hetzner CX33 (€8.99). Contabo is cheaper per GB but only on 24-month prepay and with noisy CPUs. Hetzner CX stock is sometimes "not available" in a given location; CAX (ARM) is the fallback.

Egress: all of the above include ≥ 20 TB or unlimited traffic, so serving videos straight from the VPS costs nothing extra (but ties disk, backups and bandwidth to one box).

Coolify (self-hosted, Apache-2.0) is free and turns any of these into a Heroku-like deploy target; Coolify Cloud (managed control plane) is $5/month for 2 servers [V].

## 2. Oracle Cloud "Always Free" in 2026

- Since **2026-06-15** the Always Free Ampere A1 allowance is **2 OCPU / 12 GB** (1,500 OCPU-hours + 9,000 GB-hours/month), down from 4 OCPU / 24 GB; instances above the limit were terminated from 2026-08-18 [V, InfoQ / Linuxiac / Oracle docs]. Some support e-mails claimed PAYG-upgraded accounts keep 4/24, documentation says "all tenancies" [S].
- Still included: 2× AMD micro (1/8 OCPU, 1 GB), 200 GB block volume, 10 GB object storage, 10 TB egress/month [V].
- EU home regions available (Frankfurt, Amsterdam, Paris, Marseille, Milan, Stockholm, Zurich, Madrid) [E from Oracle region list]; home region cannot be changed; Frankfurt is chronically "Out of capacity" for A1 on free accounts, sometimes for weeks [V].
- Idle reclaim rule: a free instance can be reclaimed if, over 7 days, 95th-percentile CPU < 20 %, network < 20 % and memory < 20 % [V, Oracle docs]. A bursty worker would not stay under all three, but an idle API would.
- Reliability: frequent reports of silent account/instance termination and the unannounced June cut; no support on free accounts [V].
- Viability: 2 OCPU / 12 GB ARM runs FastAPI + Redis + Postgres + GoTrue comfortably. The CPU worker runs (ONNX Runtime aarch64), but at 2 Ampere cores expect ~20–60 min per analysis [E]; acceptable only in beta.
- GDPR: Oracle is a US provider with EU regions and a DPA; the business risk is the free tier itself (no SLA, can disappear). Do **not** keep the only copy of user videos there.

## 3. Frontend hosting (Next.js 16 SSR)

| Platform / plan | Price | Limits | Commercial use | EU region | Notes |
|---|---|---|---|---|---|
| Cloudflare **Workers Free** + OpenNext | $0 [V] | 100k req/day, 10 ms CPU/req, **3 MiB** compressed bundle [V] | Allowed [V] | Workers run in every PoP; SSR may execute outside the EU | Next.js apps often exceed 3 MiB → Paid |
| Cloudflare **Workers Paid** | **$5/month** [V] | 10 M req + 30 M CPU-ms included, $0.30/M req extra, no egress fees, 10 MiB bundle [V] | Allowed | same | `@opennextjs/cloudflare` supports Next 15; Next 16 via the Build Adapters API (stable in 16.2, March 2026) — check adapter release notes [S] |
| Netlify **Free** | $0 [V] | 300 credits/month (bandwidth 10 credits/GB, SSR 5 credits/GB-h, deploy 15 credits) since the April 2026 credit model [V] | Allowed [V] | Functions on AWS, region configurable on paid plans [E] | ~30 GB bandwidth-equivalent; Personal $9, Pro $20 |
| Vercel **Hobby** | $0 | | **Not allowed** for commercial projects [V] | fra1 selectable | Rule out |
| Vercel **Pro** | **$20/seat** incl. $20 usage [V] | 1 TB transfer, 10 M edge requests | Allowed | fra1 | Best DX, most expensive |
| Railway **Hobby** | $5 incl. $5 usage; then $20/vCPU-month, $10/GB-month [V] | | Allowed | Amsterdam (europe-west4) | Idle Next.js ≈ $5–10/month [E] |
| Render **Free** web service | $0 | 0.1 CPU/512 MB, **spins down after 15 min**, 30–60 s cold start [V] | Allowed | Frankfurt | Not for users |
| Render **Starter** | **$7/month** [V] | 0.5 CPU / 512 MB, always-on | Allowed | Frankfurt | |
| Fly.io | no free tier since Oct 2024 (new accounts: 2 VM-hours/7-day trial) [V] | shared-cpu-1x 1 GB **$6.70/month** (US price; EU regions carry a multiplier) [V]; egress Europe $0.02/GB [V] | Allowed | ams, fra, cdg | Billed per second only while running |
| Coolify on the VPS | $0 extra | | | wherever the VPS is | Simplest for an all-in-one |

## 4. Worker: serverless GPU and CPU options

Assumption: one analysis = 3 min on a T4/L4/A10-class GPU (RTX 4060 does 2–4 min), plus 30–60 s cold start where the provider bills it. 300 analyses/month in beta, 1,500/month at launch.

| Provider | GPU, price | Cost / analysis (180 s + cold start) | Free credits | EU region | Cold-start / lock-in notes |
|---|---|---|---|---|---|
| **Modal** | T4 $0.000164/s, L4 $0.000222/s, A10 $0.000306/s, CPU $0.0000131/core-s, RAM $0.00000222/GiB-s [V] | T4: $0.030 base → **~$0.05** with `region="eu"` (1.5× multiplier) + container CPU/RAM [V/E]; L4 ~$0.06 | **$30/month** on Starter [V]; Team $250/month + $100 credits | `region="eu"` (1.5×) or specific EU zone (1.75×) [V] | Billing starts at container boot; ~10–30 s cold start with a ~1 GB image [E]. US company, DPA/SCCs. Python-only SDK → medium lock-in |
| **RunPod Serverless** | 16 GB tier (A4000/RTX 4000) $0.58/h; 24 GB tier (L4/A5000/3090) **$0.69/h**; 4090 $1.10/h flex [V] | L4: 240 s × $0.000192 ≈ **$0.046**; A4000 ≈ $0.039 | occasional sign-up credits only [E] | EU data centers (RO, SE, CZ, NL) selectable per endpoint [E] | FlashBoot cold starts 2–10 s on warm images [E]; US company. Docker handler → low lock-in |
| **Replicate** | T4 $0.000225/s, L40S $0.000975/s [V] | T4 ≈ $0.041; custom models bill setup/cold boot too (30 s boot can 3× a short call) [V] | none | **No region control** → treat as US | Cog packaging; deployments bill while idle |
| **Beam** | RTX 4090 $0.000192/s, H100 $0.000972/s; no T4/L4 listed [V] | 4090 ≈ $0.035; cold starts not billed [V] | $30 sign-up [S] | no EU region documented → treat as US | |
| **Koyeb** | L4 **$0.70/h**, RTX 4000 SFF Ada $0.50/h, A100 $1.60/h, per-second, scale-to-zero [V] | L4 ≈ $0.035 + boot | $0 (CPU free tier: 2 nano instances) [V] | French company, Frankfurt + Paris; A100 confirmed in Frankfurt, verify L4 in FRA [S] | Container-based → low lock-in; good EU-sovereign serverless option |
| **Scaleway L4-1-24G** | **€0.75/h**, billed per minute [V]; Serverless Jobs exist but GPU support must be verified [E] | boot 1–2 min + 3–4 min ≈ 5–6 min ≈ **€0.065–0.075**; needs own start/stop orchestration | €0 | Paris (fully EU) | Best for strict EU; dedicated VRAM; L4 stock usually fine |
| **Lambda Labs** | A10 ~$1.29/h (up from $0.86) [S], per-minute | $0.065 per 3 min but not serverless; instance lifecycle overhead | none | mostly US | Not a fit |
| **Vast.ai** | RTX 4090 from ~$0.31/h [V] | ≈ $0.016 | none | marketplace of third-party hosts | **Not acceptable** for personal videos (unknown data controllers) |
| **Fly.io GPU** | L40S / A10 on-demand ~ $1.25–1.50/h [E] | ≈ $0.07 | none | ams/fra | Verify current list |
| **Modal CPU** (2 physical cores + 4 GiB, 20 min) | | 2×0.0000131×1200 + 4×0.00000222×1200 ≈ **$0.042** base, $0.063 in EU [E] | $30/month | eu | Same cost as GPU, 7× the latency |
| **Fly performance-2x 8 GB** on demand (20 min) | $132/month ≈ $0.183/h [V] | ≈ **$0.06** + stopped rootfs $0.15/GB-month [V] | trial only | fra | Start/stop via Machines API |

Monthly GPU bill [E]: beta 300 × $0.05 ≈ **$15** (fully covered by Modal's $30 credit, or ~$14 on RunPod); launch 1,500 × $0.05 ≈ **$75** (RunPod/Koyeb) to **$90** (Modal EU). A dedicated GPU server (Hetzner GEX44 RTX 4000 SFF Ada, ~€190/month incl. June increase [E]) only wins above ~120 analyses/day.

Cold-start caveats: keep the ONNX model (RTMPose-m ≈ 50 MB) baked into the image or on a mounted volume; stream the video from object storage inside the container rather than through the API; expect the first job after idle to take +20–60 s.

## 5. Object storage

Prices as published; monthly cost at 50 GB / 500 GB / 3 TB stored with egress = 2× storage (100 GB / 1 TB / 6 TB). Requests are negligible at this scale.

| Provider | Storage price | Egress policy | EU option | 50 GB | 500 GB | 3 TB |
|---|---|---|---|---|---|---|
| **Cloudflare R2** | $0.015/GB-month, first 10 GB free; Class A $4.50/M, Class B $0.36/M after free ops [V] | **$0** [V] | `eu` jurisdiction at bucket creation (permanent) [V]; US company | **$0.60** | **$7.35** | **$44.85** |
| **Backblaze B2** | **$6.95/TB-month**, first 10 GB free [V] | free up to 3× average storage, then $0.01/GB [V] | EU-Central (Amsterdam), chosen at account creation [V]; US company (CLOUD Act) | **$0.28** | **$3.41** | **$20.78** |
| **Hetzner Object Storage** | **€6.49/month** flat incl. 1 TB storage + 1 TB egress; overage ≈ €0.0087/TB-hour (≈ €6.47/TB-month) and €1/TB egress [V for base, S for overage] | 1 TB included, then €1/TB | Falkenstein, Nuremberg, Helsinki (fully EU) | **€6.49** | **€6.49** | **€24.3** |
| **OVHcloud Object Storage Standard** | **€0.007/GB-month** [V] | **free since January 2026** (all regions, S3 and Swift) [V] | Gravelines/Strasbourg/Frankfurt (fully EU) | **€0.35** | **€3.50** | **€21.00** |
| **Scaleway Object Storage** | Multi-AZ €0.0146/GB-month, One-Zone IA €0.012 [V]; 750 GB free for 90 days for new orgs [V] | 75 GB free/month, then **€0.01/GB** [V] | Paris/Amsterdam/Warsaw (fully EU) | €0.98 | €16.55 | €103 |
| **Wasabi** | **$7.99/TB-month** (raised from $6.99 on 2026-07-01), **1 TB minimum**, 90-day minimum retention [V] | free only while monthly egress ≤ stored volume [V] | Amsterdam, Frankfurt, Paris, Milan [V]; US company | $7.99 | $7.99 | $23.97 but 6 TB egress breaks the fair-use policy |
| **AWS S3 Standard eu-central-1** (reference) | $0.0245/GB-month [V] | 100 GB/month free, then $0.09/GB [V] | Frankfurt; US company | $1.23 | ≈ $93 | ≈ $604 |

Observations: with egress = 2× storage, **OVH Object Storage (free egress) and B2 are the cheapest at every size**, R2 is cheapest on the free tier only, Hetzner is the simplest flat price and is fully EU, Scaleway/S3 are priced out by egress. Hetzner Object Storage had degraded-performance incidents in July 2026 [S] — keep a lifecycle rule or second bucket for backups. All S3-compatible, so lock-in is low; R2 requires a Cloudflare account and its API tokens.

## 6. Managed Postgres / Auth

| Option | Price | Limits / rules | EU |
|---|---|---|---|
| **Supabase Free** | $0 [V] | 2 projects, 500 MB DB, 1 GB file storage, 5 GB egress, 50k MAU; **paused after 7 days without API activity**, manual restore, no data loss [V] | Frankfurt (eu-central-1) selectable [V] |
| **Supabase Pro** | **$25/month** per org + usage [V] | 8 GB DB, 100 GB storage, 250 GB egress, 100k MAU, includes $10 compute credit (Micro: 2-core ARM, 1 GB) [V] | Frankfurt |
| **Neon Free** | $0 [V] | 0.5 GB storage per project, 100 CU-hours/project/month, 5 GB transfer; compute scales to zero after 5 min (first query +0.5–1 s) [V]; Azure Germany region closed, AWS Frankfurt available [V] | Frankfurt (aws-eu-central-1) |
| **Postgres + GoTrue on the VPS** | €0 extra | you own backups (pg_dump to object storage, ~€0) | yes |

Self-hosting GoTrue (Supabase Auth) on the VPS keeps the auth data in the EU and removes the pausing risk; the only reason to pay Supabase Pro would be to avoid running Postgres yourself.

## 7. Transactional email (few hundred/month)

| Provider | Free tier | First paid | EU / data location |
|---|---|---|---|
| **Brevo** | 300 emails/day [V] | Starter $9/month | French company, EU hosting — simplest GDPR fit |
| **Scaleway TEM** | 300 emails/month free, then €0.25/1,000 [S] | pay-as-you-go | Paris |
| **Resend** | 3,000/month, 100/day cap [V] | Pro $20/month (50k) | US company; EU region option exists for data residency [E, verify in dashboard] |
| **Amazon SES** | **no free tier for accounts created after 2026-07-21** (only the $200 general AWS credit) [V]; $0.10/1,000 | ≈ $0.05/month at 500 emails | eu-central-1; US company |
| **Postmark** | 100/month hard cap [V] | Basic $15/month (10k) [V] | servers in the US, no EU plans [V]; ActiveCampaign-owned |

Recommendation: Brevo free or Scaleway TEM; cost €0 at this volume.

## 8. Three concrete architectures

Exchange rate assumption for mixed totals: $1 ≈ €0.87 [E]. Add 19–22 % VAT where you cannot reclaim it. Domain (~€1/month) and backups (pg_dump into the same bucket) are included as €0–1.

### A. "One VPS does everything" (CPU worker)

Stack: Coolify or plain docker-compose on one Hetzner box: Next.js, FastAPI, Redis, Postgres, GoTrue, worker (ONNX Runtime CPU, 1–2 concurrent jobs). Videos on Hetzner Object Storage (same network zone, free internal traffic), served via presigned URLs.

| Item | (a) Beta: 30 users, 10 analyses/day, 100 GB | (b) Launch: 500 users, 50 analyses/day, 1 TB |
|---|---|---|
| VPS | Hetzner CX33 €8.49 + IPv4 €0.50 [V] | Hetzner CX43 €15.99 + €0.50 [V] (or Netcup VPS 1000 G12.5 €14.50 on 12 months) |
| Object storage | Hetzner Object Storage €6.49 (100 GB + 200 GB egress) [V] | Hetzner Object Storage €6.49 + ~€1 egress overage [V/S] |
| Email, domain | Brevo free + ~€1 | same |
| **Total** | **≈ €16.5/month** | **≈ €24/month** |

Caveats: analysis latency 5–25 min on 4 shared vCPU [E] and users wait; at 50/day the queue averages ~12 CPU-hours/day — CX43 copes but a burst of 10 uploads means an hour of waiting. Single point of failure; snapshot backups (Hetzner snapshots ≈ €0.012/GB-month [E]) add ~€1. Fully EU, zero US providers: the **cheapest GDPR-clean option for beta**.

### B. "VPS + serverless GPU + cheap object storage"

Stack: Hetzner CX23/CX33 for web + API + Redis + Postgres + GoTrue (Coolify); jobs pushed to a serverless GPU endpoint that reads/writes the bucket directly; object storage at OVH (free egress) or Hetzner.

| Item | (a) Beta | (b) Launch |
|---|---|---|
| VPS | Hetzner CX23 €5.49 + €0.50 [V] | Hetzner CX33 €8.49 + €0.50 [V] |
| GPU | 300 × ~$0.05 ≈ $15 → **$0 under Modal's $30/month credit** (region `eu`) [V/E]; RunPod EU ≈ $14; Scaleway L4 ≈ €21 [E] | 1,500 × ~$0.05 ≈ **$75** RunPod/Koyeb, ≈ $90 Modal EU, ≈ €105 Scaleway L4 [E] |
| Object storage | OVH €0.70 (100 GB) [V] or Hetzner €6.49 | OVH €7.00 (1 TB, egress free) [V] or Hetzner €7.49 |
| Email, domain | €1 | €1 |
| **Total** | **≈ €8/month** with Modal credits (≈ €20 without, ≈ €28 on Scaleway L4) | **≈ €82/month** (RunPod/Koyeb), ≈ €95 (Modal EU), ≈ €122 (all-EU: Scaleway L4 + OVH) |

Caveats: the GPU provider holds videos in memory/scratch during a job (processor under DPA; choose an EU region explicitly). Modal/RunPod are US companies; Koyeb and Scaleway are French if you need an EU-only chain (+€20–40/month at launch). Analysis time drops to ~3–4 min including cold start. Lock-in is limited to the job-submission adapter.

### C. "Free tiers stitched together"

Stack: Oracle Always Free A1 (2 OCPU / 12 GB, Frankfurt) for FastAPI + Redis + GoTrue (+ CPU worker fallback); Cloudflare Workers Free + OpenNext for Next.js; R2 (`eu` jurisdiction) for videos; Neon Free (Frankfurt) for Postgres; Modal Starter credits for GPU jobs; Brevo free for email.

| Item | (a) Beta | (b) Launch |
|---|---|---|
| Oracle A1 | $0 (if you ever get capacity) [V] | $0, but 500 users on a reclaimable free VM |
| Cloudflare Workers | $0; likely **$5** because of the 3 MiB free bundle limit [V] | $5 |
| R2 | 100 GB → $1.35 [V] | 1 TB → **$14.85** [V] |
| Neon Free | $0 (0.5 GB is enough for metadata) [V] | $0–19 if the DB grows past 0.5 GB [E] |
| Modal | $0 (inside $30 credit) [V/E] | $90 − $30 credit ≈ **$60** |
| **Total** | **≈ $1–7/month** | **≈ $80–100/month** (no longer cheaper than B) |

Risks: Oracle capacity lottery and unannounced tier cuts (June 2026) — the API can vanish; idle-reclaim rule; Neon cold starts and 90-day inactivity deletion on free projects; Cloudflare SSR runs outside the EU unless you accept that only non-personal rendering happens at the edge; five vendors, four of them US (Oracle, Cloudflare, Neon, Modal), each needing a DPA; nothing has an SLA. Suitable for a private beta with friends, not for a public launch holding people's videos.

### Verdict

- **Cheapest that is still GDPR-reasonable, beta:** Architecture **A** on a Hetzner CX33 + Hetzner Object Storage (**≈ €16.5/month**, 100 % EU providers, zero DPAs with US vendors). If analysis latency matters more than €8, Architecture **B-beta** with Modal `eu` credits is ≈ €8/month but adds a US processor; the all-EU variant (Scaleway L4) is ≈ €28/month.
- **Launch (500 users, 50/day, 1 TB):** Architecture **B** at **≈ €82/month** (RunPod EU or Koyeb Frankfurt + Hetzner CX33 + OVH Object Storage); ≈ €122/month if every byte must stay with EU-headquartered providers (Scaleway L4 + OVH). Architecture A at ≈ €24/month remains the floor if 10–25 min analysis times are acceptable.
- Architecture **C** is only worth it for a throw-away private beta; it stops being the cheapest as soon as storage passes ~300 GB.

## 9. Sources

- Hetzner price adjustment 15 June 2026: https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/
- Hetzner post-April 2026 price tables: https://www.bitdoze.com/hetzner-cloud-cost-optimized-plans/ ; https://northflank.com/blog/hetzner-cloud-server-price-increases
- Hetzner Object Storage: https://www.hetzner.com/storage/object-storage/ ; https://docs.hetzner.com/storage/object-storage/overview ; https://bex.co/blog/2026/09/11/hetzner-object-storage-tenant-backup-backend
- Netcup VPS: https://www.netcup.com/en/server/vps ; price notice https://docs.elest.io/books/announcement/page/netcup-price-change-notice-effective-april-1st
- OVHcloud VPS: https://www.ovhcloud.com/en-ie/vps/ ; https://www.vpsbenchmarks.com/hosters/ovhcloud/plans/vps-1 ; https://blog.cdnsun.com/ovhcloud-and-hetzner-2026-hosting-price-increases-explained/
- OVHcloud Object Storage egress removal (Jan 2026): https://pricingsaas.com/companies/ovhcloud ; https://projector.cloud-mercato.com/projects/ovhcloud-standard-object-storage-benchmark/pricing/table
- Contabo: https://contabo.com/en/vps/ ; https://contabo.com/blog/cheapest-eu-vps-high-ram-gdpr/
- Scaleway instances and pricing update: https://www.scaleway.com/en/pricing/virtual-instances/ ; https://www.scaleway.com/en/blog/a-transparent-update-on-scaleway-pricing/ ; GPU https://calculator.holori.com/scaleway/vm/L4-1-24G ; storage https://www.scaleway.com/en/pricing/storage ; TEM https://www.scaleway.com/en/transactional-email-tem/
- IONOS: https://www.ionos.de/server/vps
- Oracle Always Free: https://docs.oracle.com/en-us/iaas/Content/FreeTier/resourceref.htm ; https://www.infoq.com/news/2026/07/oracle-cloud-free-tier-limits/ ; https://linuxiac.com/oracle-quietly-cuts-free-tier-ampere-a1-resources-in-half/
- Cloudflare Workers pricing: https://developers.cloudflare.com/workers/platform/pricing/ ; R2 pricing https://developers.cloudflare.com/r2/pricing/ ; R2 jurisdictions https://developers.cloudflare.com/r2/reference/data-location/ ; OpenNext https://opennext.js.org/cloudflare
- Netlify credits model: https://netli.fyi/blog/netlify-pricing-and-limits ; commercial use https://answers.netlify.com/t/can-we-use-netlify-free-plan-for-commercial-purposes/41545/2
- Vercel: https://dev.to/nayankyada/vercel-pricing-2026-what-you-actually-pay-for-a-real-nextjs-project-33md
- Railway: https://docs.railway.com/pricing/plans ; Render: https://livemy.app/blog/render-pricing ; Fly.io: https://docs.fly.io/about/pricing
- Coolify: https://coolify.io/docs/core/selfhosted-cloud-comparison
- Modal: https://modal.com/pricing ; https://modal.com/docs/guide/region-selection
- RunPod: https://www.runpod.io/pricing ; https://docs.runpod.io/serverless/pricing
- Replicate: https://replicate.com/pricing ; https://www.spheron.network/blog/replicate-pricing-2026-per-second-cost/
- Beam: https://www.beam.cloud/pricing ; Koyeb: https://www.koyeb.com/pricing ; https://www.koyeb.com/docs/reference/regions
- Lambda: https://computeprices.com/providers/lambda/gpus/a10 ; Vast.ai: https://computeprices.com/providers/vast/gpus/rtx4090
- Backblaze B2: https://www.backblaze.com/cloud-storage/pricing ; https://www.backblaze.com/docs/cloud-storage-data-regions
- Wasabi: https://wasabi.com/pricing ; https://wasabi.com/company/storage-regions ; https://leanopstech.com/blog/wasabi-pricing-2026/
- AWS S3 Frankfurt: https://www.impossiblecloud.com/magazine/cheapest-s3-storage-vs-aws-europe-2026 ; https://egresscost.com/aws/s3-egress-pricing
- Supabase: https://www.jetadmin.io/blog/supabase-pricing-2026-guide-to-plans-limits-and-real-world-costs/ ; Neon: https://neon.com/pricing ; https://neon.com/docs/introduction/regions
- Email: https://automationatlas.io/answers/resend-pricing-explained-2026/ ; https://automationatlas.io/answers/postmark-pricing-explained-2026/ ; https://postmarkapp.com/support/article/1168-postmarks-gdpr-compliance ; https://costbench.com/software/marketing-automation/brevo/free-plan ; https://www.costbench.com/software/email-api/amazon-ses/free-plan/
- RTMPose CPU benchmarks: https://github.com/open-mmlab/mmpose/tree/main/projects/rtmpose/benchmark
