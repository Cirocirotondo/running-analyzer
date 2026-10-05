# Running Analyzer

Analyzes a person's running technique from treadmill videos (side view mandatory, rear view optional):
skeleton overlay, kinematic Metrics with Typical Ranges and sources, and evidence-based Advice.

- Vocabulary: [GLOSSARY.md](GLOSSARY.md). Decisions: [docs/adr/](docs/adr/). What v1 does: [docs/SPEC.md](docs/SPEC.md).
- Reference values and sources: [docs/typical-ranges.md](docs/typical-ranges.md).
- Pipeline experiments and findings: [prototype/EXPERIMENTS.md](prototype/EXPERIMENTS.md).

## Layout

| Path | What |
|---|---|
| `web/` | Next.js frontend (TypeScript, Tailwind) |
| `api/` | FastAPI backend, managed with `uv` |
| `prototype/` | Pose-estimation and metrics pipeline (`analyze.py`, `analyze_rear.py`); becomes the worker |
| `db/init/` | SQL run once when the Postgres volume is created (Supabase Auth schema and roles) |
| `docs/` | Spec, ADRs, reference values, recording protocols |
| `data/`, `videos/` | Local videos and outputs, not in git |

## Run locally

Prerequisites: Docker (Desktop with WSL2 integration on Windows), and for the prototype `uv` and an NVIDIA
GPU (optional; CPU works, slower).

```bash
cp .env.example .env            # first time only
docker compose up -d --build
```

| Service | URL |
|---|---|
| Web | http://localhost:3000 |
| API | http://localhost:8000 (`/health`, `/docs`) |
| Auth (GoTrue) | http://localhost:9999 (`/health`) |
| Storage (S3, RustFS) | http://localhost:9000, console http://localhost:9001 |
| Mailpit (every email lands here) | http://localhost:8025 |
| Postgres | localhost:5432, Redis localhost:6379 |

Workers: `worker` (CPU) or `worker-gpu` run the Analyses (queue `analysis`, picked by `COMPOSE_PROFILES`);
`checker` runs the Recording Check on each uploaded Video (queue `checks`, CPU, seconds per Video).
`janitor` deletes, every hour, Videos nobody will use: drafts untouched for 7 days, unanswered and
expired Failure Reports (`worker/worker/janitor.py`; one pass: `python -m worker.janitor --once`).

`api/src` and `web/` are mounted into the containers, so code changes reload without a rebuild.
Rebuild (`--build`) after changing dependencies. `docker compose down -v` wipes the database and storage.

Database migrations run from the host (the API image has no Alembic config):

```bash
cd api && DATABASE_URL="postgresql+asyncpg://app:app-dev-password@localhost:5432/running_analyzer" uv run alembic upgrade head
```

Maintenance commands, inside the API container (`docker compose exec api uv run python -m running_analyzer_api.cli ...`):
`invites 5` (invite codes), `admin <email>` (Admin role), `rerun <session id>` (analyze again as a new
Session), `adopt ...` (queue videos already in storage, e.g. files above the upload limit).

Development auth confirms emails automatically (`GOTRUE_MAILER_AUTOCONFIRM`); sign up with
`curl -X POST localhost:9999/signup -H 'Content-Type: application/json' -d '{"email":"a@b.c","password":"..."}'`.

## Prototype pipeline

```bash
cd prototype && uv sync
uv run analyze.py ../videos/<clip>.mp4 --speed-kmh 14 --height-cm 179 --device cuda --auto-window 20
uv run analyze_rear.py ../videos/<rear clip>.mp4 --device cuda
```

Outputs in `data/out/<clip>_<model>/`: `overlay.mp4`, `plots.png`, `metrics.json`, `keypoints.parquet`.
Slow-motion clips are handled through the `capture_fps` tag (needs `ffprobe` on the PATH).

## Guide pages and their figures

The explanations behind the info buttons and the `/learn` pages live in `web/src/content/learn.ts`.
The example figures are rendered from one analyzed session (videos plus the keypoints JSON the worker
uploads next to them), with the face blurred:

```bash
cd prototype
uv run learn_figures.py --side-video <side.mp4> --side-keypoints <keypoints_side.json> \
    --rear-video <rear.mp4> --rear-keypoints <keypoints_rear.json> --height-cm 179 \
    --out ../web/public/figures/learn --manifest ../web/src/content/learn-figures.json
```

## Tests

```bash
cd worker && uv run pytest              # pipeline: synthetic phone-like videos, Playback Video, Recording Check decisions
cd web && npm test && npm run lint && npm run typecheck
```

Both run on GitHub Actions on every push (`.github/workflows/tests.yml`). The real-clip regression test
needs `data/fixtures/side_left_hip.mp4` (kept outside git) and the pose model, so it runs locally:

```bash
cd prototype && PIPELINE_DEVICE=cuda uv run --with pytest pytest ../worker/tests -m slow   # RECORD=1 to re-record values
```

The browser test (seeking a Playback Video in Chromium shows the frame of each keypoint row) runs with
the fast tests when Node and Playwright are installed, and is skipped otherwise (CI):
`PLAYWRIGHT_DIR=<folder with node_modules/playwright> uv run pytest -m browser`.
