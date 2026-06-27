# JobAI — Govt Job Eligibility Matching Platform

## Context

Greenfield project. Users build a profile (Indian govt-job schema: DOB, category, qualification, domicile, physical standards, exams cleared, experience). The platform ingests govt job notifications from multiple sources, extracts eligibility criteria, and surfaces only the jobs each user is eligible for.

**Target scale:** ~50K users, ~5K new jobs/month.
**V1 constraint: $0/month. Every service in v1 is on a permanently free tier — no credit card charges, no trial periods that expire.**

---

## Core Insight: Cost Model

| Approach | Cost scaling | Est. monthly LLM cost |
|---|---|---|
| RAG + LLM per user-job pair | O(U × J) = 250M ops | $5,000–25,000 |
| **Structured extract once, SQL/Python match, LLM only per job** | O(J) only | **$0 in v1 (free Gemini key)** |

Eligibility for Indian govt jobs is ~90% deterministic (age cutoff, qualification equivalence, category, domicile, physical minimums). LLM is needed **once per job** to convert messy PDF/HTML into structured JSON. This is not a RAG problem — it's a **structured extraction + rule engine** problem.

---

## V1 vs V2 Scope

| Feature | V1 (free tier, ship now) | V2 (when monetized) |
|---|---|---|
| API hosting | Koyeb nano (free) | Fly.io / Railway paid |
| LLM extraction | Gemini 2.0 Flash (free key) | Claude Haiku (paid, faster) |
| Background workers | GitHub Actions cron | Redis + Celery (always-on) |
| Eligibility matching | Pull model (compute at feed-load) | Push model (pre-computed, instant) |
| Email notifications | Weekly digest only (Resend free 3K/mo) | Per-match real-time emails |
| DB | Neon free (0.5GB) | Neon Pro or Supabase |
| Scraper types | httpx + feedparser (static + RSS) | + Playwright (JS-rendered portals) |

---

## Architecture Diagram (V1 — Zero Cost)

```
┌────────────────────────┐
│   Next.js 15           │◀──── Users (profile, job feed, apply links)
│   (Vercel Hobby — free)│
└───────────┬────────────┘
            │ REST /api/v1/  (JWT cookie auth)
┌───────────▼────────────┐        ┌──────────────────────────┐
│   FastAPI               │───────▶│  Neon PostgreSQL          │
│   (Koyeb nano — free)   │        │  (free tier, 0.5 GB max) │
│                         │        │                          │
│  Routes:                │◀───────│  Tables:                 │
│   POST /auth/register   │        │   users                  │
│   POST /auth/login      │        │   jobs (+ criteria JSONB)│
│   GET  /profile         │        │   scraper_runs           │
│   PUT  /profile         │        │   (no matches table v1)  │
│   GET  /jobs            │        └──────────────────────────┘
│   POST /admin/upload    │                    ▲
│                         │                    │
│  Matcher runs inline:   │                    │ writes
│  fetch jobs → Python    │                    │
│  rule engine → return   │         ┌──────────┴───────────────────┐
│  eligible subset        │         │  GitHub Actions cron          │
└─────────────────────────┘         │  (every 6 hours — free)      │
                                    │                              │
                                    │  ┌──────────┐ ┌───────────┐ │
                                    │  │ Scrapers │→│ Extractor │ │
                                    │  │ (httpx + │ │ (Gemini   │ │
                                    │  │ selectol.│ │ 2.0 Flash)│ │
                                    │  │ feedpars)│ └───────────┘ │
                                    │  └────┬─────┘               │
                                    │       │                      │
                                    │       ▼                      │
                                    │  Cloudflare R2               │
                                    │  (raw PDFs — free 10 GB)     │
                                    └──────────────────────────────┘
```

**Key V1 simplification — Pull Matching:**
There is no pre-computed `eligibility_matches` table in v1. When a user loads their job feed, FastAPI fetches all active jobs (~500–1500 rows), runs the Python rule engine in-process against the user's profile (~50ms), and returns the eligible subset. This keeps the DB under 300MB for the entire first year, fitting within Neon's 0.5GB free limit.

---

## Components — Detailed

### 1. Frontend — Next.js 15 (Vercel Hobby, free)

**Why Next.js:**
- Govt job listings need SEO — searches like "SSC CGL 2026 eligibility" should land on your pages. SSR/SSG makes pages indexable; a plain React SPA is invisible.
- Server Components filter the job feed server-side before HTML is sent — no flicker of ineligible jobs.
- Vercel Hobby plan: unlimited deployments, 100GB bandwidth/month, always free.
- Auto-deploys on every push to `main`.

**Frontend stack:**
| Package | Purpose |
|---|---|
| `next` 15 (App Router) | Framework + SSR/SSG |
| `tailwindcss` | Styling |
| `shadcn/ui` | Component library (Radix + Tailwind, zero lock-in) |
| `@tanstack/react-query` | Data fetching, caching, background refetch |
| `react-hook-form` + `zod` | Profile wizard forms + validation |

---

### 2. API — FastAPI (Koyeb nano, free)

Python across API + scrapers + LLM SDK + rule engine — one language, no context switching.

**Why Koyeb (not Fly.io or Render):**
- Fly.io removed their free tier in 2024 — cheapest is now ~$2/month.
- Render deprecated free web services in November 2024.
- **Koyeb nano**: 0.1 vCPU, 256MB RAM, always-on (no sleep), free permanently. Sufficient for an MVP with low traffic.
- Connects to GitHub → auto-deploys on push to `main`.

**API stack:**
| Package | Purpose |
|---|---|
| `fastapi` | Framework, async, typed |
| `pydantic` v2 | Request/response validation |
| `sqlalchemy` 2.0 (async) | ORM with async sessions |
| `alembic` | DB migrations |
| `asyncpg` | Async Postgres driver |
| `python-jose[cryptography]` | JWT signing + validation |
| `passlib[bcrypt]` | Password hashing |
| `httpx` | Async HTTP client (scrapers + internal calls) |
| `slowapi` | Rate limiting (Redis-free, in-memory for v1) |

**Auth design (v1 — no Auth.js, no third-party):**
FastAPI handles auth end-to-end. Frontend stores JWT in an `httpOnly` cookie.

```
POST /api/v1/auth/register  →  hash password, save user, return JWT
POST /api/v1/auth/login     →  verify password, return JWT
GET  /api/v1/profile        →  validate JWT header, return profile
PUT  /api/v1/profile        →  validate JWT, update profile
GET  /api/v1/jobs           →  validate JWT, run rule engine, return eligible jobs
```

JWT payload: `{ "sub": "user_uuid", "exp": <24h from now> }`
Secret: `JWT_SECRET` env var (random 32+ char string, never committed).

---

### 3. Database — Neon PostgreSQL (free, 0.5 GB)

**Why Neon (not Supabase):**
- Supabase free tier **pauses the project** after 1 week of inactivity — data is inaccessible until manually resumed.
- Neon free tier: no project pause, auto-suspend only the compute (wakes in ~1-2s on first query). Data is always accessible.
- 0.5GB limit is sufficient for v1 (see storage estimate below).

**Local development setup (Windows):**
```powershell
# Download PostgreSQL 16 installer from postgresql.org/download/windows/
# After install, open psql:
psql -U postgres -c "CREATE DATABASE jobai_dev;"
psql -U postgres -c "CREATE USER jobai WITH PASSWORD 'jobai'; GRANT ALL ON DATABASE jobai_dev TO jobai;"
```

```bash
# .env (local)
DATABASE_URL=postgresql+asyncpg://jobai:jobai@localhost:5432/jobai_dev
```

**Neon setup (production):**
1. Sign up at neon.tech (no CC required for free tier)
2. Create project → copy connection string
3. Add `?sslmode=require` to the URL

```bash
# .env (production / GitHub Secret)
DATABASE_URL=postgresql+asyncpg://user:pass@ep-xxx.us-east-2.aws.neon.tech/jobai?ssl=require
```

**V1 storage estimate:**

| Table | Rows after 12 months | Avg row size | Total |
|---|---|---|---|
| `users` | 50K | 1 KB | 50 MB |
| `jobs` (+ criteria JSONB) | 60K (5K/mo × 12) | 3 KB | 180 MB |
| `scraper_runs` | ~1,500 | 0.5 KB | 1 MB |
| **Total** | | | **~231 MB** ✓ |

No `eligibility_matches` table in v1 keeps total well under 0.5 GB.

**Critical indexes (add in migration `003`):**
```sql
-- Job feed query: active jobs sorted by date
CREATE INDEX idx_jobs_status_published
  ON jobs(status, published_at DESC)
  WHERE status = 'active';

-- Deduplication on ingest
CREATE UNIQUE INDEX idx_jobs_source_dedup
  ON jobs(source_name, source_job_id);

-- Content-change detection
CREATE INDEX idx_jobs_content_hash ON jobs(content_hash);
```

Run migrations:
```bash
cd db && alembic upgrade head
```

---

### 4. Background Workers — GitHub Actions Cron (free)

**Why GitHub Actions instead of Celery + Redis:**
- Celery requires an always-on process and a Redis broker — both cost money to host.
- GitHub Actions runners are free virtual machines provided by GitHub. A cron workflow (`0 */6 * * *`) runs your Python scraper scripts in a fresh environment every 6 hours.
- 2,000 free minutes/month for private repos; **unlimited for public repos**.
- V1 usage: 4 runs/day × 30 days × ~10 min/run = **1,200 min/month** (within free limit, even on private).

**Pipeline per cron run:**
```
GitHub Actions runner wakes up
        │
        ▼
scripts/run_pipeline.py
        │
        ├── for each source (SSC, UPSC, Employment News RSS, ...):
        │       scraper.fetch()  →  list of raw job dicts
        │       deduplicate against DB (source_name + source_job_id)
        │       save raw file to Cloudflare R2
        │       insert new job rows (status='pending_extraction')
        │
        └── for each pending job:
                extractor.extract(job)  →  calls Gemini 2.0 Flash
                saves criteria JSONB to job row
                sets status='active'
                logs to scraper_runs table
```

**`.github/workflows/scrape.yml`:**
```yaml
name: Scrape & Extract Jobs
on:
  schedule:
    - cron: '0 */6 * * *'    # every 6 hours: 00:00, 06:00, 12:00, 18:00 UTC
  workflow_dispatch:           # manual trigger from GitHub UI

jobs:
  pipeline:
    runs-on: ubuntu-latest
    timeout-minutes: 30
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r scripts/requirements.txt
      - name: Run scrape + extract pipeline
        run: python scripts/run_pipeline.py
        env:
          DATABASE_URL:                ${{ secrets.DATABASE_URL }}
          GOOGLE_AI_API_KEY:           ${{ secrets.GOOGLE_AI_API_KEY }}
          CLOUDFLARE_ACCOUNT_ID:       ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
          CLOUDFLARE_R2_ACCESS_KEY_ID: ${{ secrets.CLOUDFLARE_R2_ACCESS_KEY_ID }}
          CLOUDFLARE_R2_SECRET_KEY:    ${{ secrets.CLOUDFLARE_R2_SECRET_KEY }}
          R2_BUCKET_NAME:              ${{ secrets.R2_BUCKET_NAME }}
          SENTRY_DSN:                  ${{ secrets.SENTRY_DSN_WORKERS }}
```

---

### 5. Scrapers (static HTML + RSS only in v1)

**V1 scope — skip Playwright:** JS-rendered portals (some state PSCs, banking sites) require headless Chrome. Playwright works in GitHub Actions but adds setup time and complexity. V1 covers static HTML + RSS, which captures SSC, UPSC, Employment News, Railways — the highest-volume sources.

| Source type | Tool | V1? | Examples |
|---|---|---|---|
| Static HTML | `httpx` + `selectolax` | ✓ | SSC, UPSC, Railways, most state PSCs |
| RSS / Atom feeds | `feedparser` | ✓ | Employment News, NCS portal |
| PDF parsing | `pdfplumber` | ✓ | Gazette notifications (triggered post-scrape) |
| JS-rendered | `Playwright` | V2 | IBPS, some state boards |
| Manual upload | FastAPI endpoint | ✓ | Admin uploads PDF directly |

**Adapter pattern:** each scraper implements `BaseScraper`:
```python
class BaseScraper:
    source_name: str
    def fetch_listings(self) -> list[RawJobDict]: ...
```

**Deduplication:** `(source_name, source_job_id)` unique constraint + SHA256 content hash for detecting amendments (corrigenda re-trigger extraction).

Raw files stored locally during development (`./storage/raw/`), in Cloudflare R2 in production.

---

### 6. Extractor — Gemini 2.0 Flash (free API key)

**Why Gemini instead of Claude Haiku:**
- Claude Haiku requires a paid Anthropic API key — there is no free tier.
- **Google AI Studio** provides a free Gemini API key with: 15 RPM, 1M tokens/minute, 1,500 requests/day.
- V1 usage: 5K jobs/month ÷ 30 days = ~167 jobs/day — well within the 1,500 RPD free limit. ✓
- Gemini 2.0 Flash is highly capable at structured JSON extraction from unstructured PDF/HTML text.
- Get your free key: [aistudio.google.com](https://aistudio.google.com) → Get API key.

**Extraction call:**
```python
import google.generativeai as genai

genai.configure(api_key=settings.GOOGLE_AI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

response = model.generate_content(
    [SYSTEM_PROMPT, raw_text],
    generation_config=genai.GenerationConfig(
        response_mime_type="application/json",
        response_schema=JobCriteria,   # Pydantic model → Gemini enforces schema
    ),
)
criteria = JobCriteria.model_validate_json(response.text)
```

`response_mime_type="application/json"` with `response_schema` gives guaranteed valid JSON — no regex post-processing, equivalent to Anthropic's tool-use structured output.

Each field gets a `confidence` score (0–1). Fields with `confidence < 0.7` are stored in `low_confidence_fields[]` for manual review in the admin panel.

**Cost: $0** (free API key, rate limits not hit at v1 scale).

---

### 7. Matcher — Rule Engine (inline in FastAPI, $0)

Pull model: runs inside the FastAPI `/jobs` route handler when a user requests their feed.

```
GET /api/v1/jobs
    │
    ├── fetch user profile from DB
    ├── fetch all active jobs from DB (status='active', deadline > now)
    │   (~500–1500 rows at any time, ~100KB data)
    ├── run Python rule engine against each job's criteria JSONB
    │   (~50ms for 1500 jobs — fast enough for a web request)
    └── return eligible subset (typically 5–50% of active jobs)
```

**Rules evaluated per job:**
- Age: `profile.age` within `criteria.age.min/max` + category relaxation table
- Qualification: `profile.degree` in `criteria.qualifications` with equivalence map (`B.E ≡ B.Tech`, `B.Sc(IT) ≡ BCA`)
- Category: `profile.category` in `criteria.categories_allowed`
- Gender: `profile.gender` in `criteria.gender` (if not "any")
- Domicile: `profile.state` in `criteria.domicile.states` (if not "any")
- Physical standards: checked only if `criteria.job_type in ['defence', 'police', 'paramilitary']`
- Exams cleared: `criteria.required_exams ⊆ profile.exams_cleared`
- Experience: `profile.experience_years >= criteria.experience.years_min`

Returns `{job, is_eligible, reasons[]}` per job. Frontend shows reasons for ineligibility ("Age: 33 exceeds maximum 32 for General category").

**When to upgrade to push model (V2):** When you have >10K active users and the per-request 50ms latency becomes a bottleneck, or when you need real-time push notifications per match.

---

### 8. Notifications — Resend (free, 3K emails/month)

**V1 scope:** No per-match real-time notifications. Instead, a weekly digest email is sent to users listing new eligible jobs from the past 7 days.

- **Weekly digest:** GitHub Actions cron (`0 8 * * 1` — every Monday 8am UTC) runs the matcher for each user with a profile, collects new eligible jobs, sends one email per user via Resend.
- **Free tier:** 3,000 emails/month. At 3K users × 1 email/week × 4 weeks = 12K emails/month — this **exceeds** the free limit once you have >750 active users.
- **Mitigation for v1:** Send only to users who have a complete profile, and cap to 3K sends/week. Real-time email notifications are a V2 feature.
- **Transactional emails:** Registration welcome email + password reset — these stay well within the 100/day limit on Resend free tier.

---

## Structured Eligibility Schema (`job_criteria`)

This JSONB column lives in the `jobs` table. Extracted once by Gemini, read many times by the matcher.

```json
{
  "age": {
    "min": 18, "max": 32,
    "relaxations": { "SC": 5, "ST": 5, "OBC": 3, "PwD": 10, "ExServicemen": 5 },
    "as_of_date": "2026-08-01"
  },
  "qualifications": [
    { "level": "graduate", "fields": ["any"], "min_percentage": 50 }
  ],
  "gender": ["any"],
  "categories_allowed": ["Gen", "OBC", "SC", "ST", "EWS"],
  "domicile": { "states": ["any"] },
  "physical_standards": {
    "applies_to": ["defence", "police"],
    "height_cm_min": { "male": 170, "female": 157 },
    "chest_cm_min": 80,
    "vision": "6/6"
  },
  "required_exams": [],
  "experience": { "years_min": 0, "domain": null },
  "job_type": "civil",
  "nationality": ["Indian"],
  "free_text_clauses": [],
  "low_confidence_fields": [],
  "extraction_confidence": { "age": 0.98, "qualifications": 0.72 }
}
```

---

## Project Structure

```
JobAI/
│
├── apps/
│   ├── web/                          # Next.js 15 frontend
│   │   ├── app/
│   │   │   ├── (auth)/
│   │   │   │   ├── login/page.tsx
│   │   │   │   └── register/page.tsx
│   │   │   ├── profile/
│   │   │   │   └── page.tsx          # Multi-step profile wizard
│   │   │   ├── jobs/
│   │   │   │   ├── page.tsx          # Eligible jobs feed
│   │   │   │   └── [id]/page.tsx     # Job detail + apply link
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── ui/                   # shadcn/ui components (generated)
│   │   │   ├── JobCard.tsx
│   │   │   ├── ProfileWizard.tsx
│   │   │   └── EligibilityBadge.tsx
│   │   ├── lib/
│   │   │   ├── api.ts                # fetch wrappers for FastAPI
│   │   │   └── auth.ts               # JWT cookie helpers
│   │   ├── .env.local
│   │   ├── next.config.ts
│   │   └── package.json
│   │
│   └── api/                          # FastAPI backend
│       ├── main.py                   # App entrypoint, CORS, router mounting
│       ├── routers/
│       │   ├── auth.py               # POST /auth/register, /auth/login
│       │   ├── profile.py            # GET/PUT /profile
│       │   ├── jobs.py               # GET /jobs (runs matcher inline)
│       │   └── admin.py              # POST /admin/upload-job (manual PDF)
│       ├── services/
│       │   ├── matcher.py            # Rule engine: profile × job_criteria → bool
│       │   └── extractor.py          # Gemini extraction (called by admin upload)
│       ├── models/                   # SQLAlchemy ORM models
│       │   ├── user.py
│       │   └── job.py
│       ├── deps.py                   # DB session, current_user dependency
│       ├── config.py                 # Settings (pydantic-settings from .env)
│       ├── requirements.txt
│       └── .env
│
├── scripts/                          # Run by GitHub Actions (no server needed)
│   ├── run_pipeline.py               # Entry point: scrape → extract → log
│   ├── scrapers/
│   │   ├── base.py                   # BaseScraper interface
│   │   ├── ssc.py                    # ssc.nic.in (static HTML)
│   │   ├── upsc.py                   # upsc.gov.in (static HTML)
│   │   ├── railways.py               # indianrailways.gov.in (static HTML)
│   │   ├── employment_news.py        # RSS feed
│   │   └── state_psc/
│   │       ├── uppsc.py
│   │       └── bpsc.py
│   ├── extractor.py                  # Gemini 2.0 Flash extraction
│   ├── storage.py                    # Cloudflare R2 upload/download
│   └── requirements.txt              # httpx, selectolax, feedparser, pdfplumber,
│                                     # google-generativeai, sqlalchemy, asyncpg, boto3
│
├── packages/
│   └── schema/                       # Shared Pydantic models
│       ├── __init__.py
│       ├── job_criteria.py           # JobCriteria, AgeRule, QualificationRule
│       ├── user_profile.py           # UserProfile, PhysicalStandards
│       └── pyproject.toml
│
├── db/
│   ├── alembic.ini
│   ├── env.py
│   └── migrations/
│       ├── 001_initial_schema.py     # users, jobs tables
│       ├── 002_add_criteria.py       # jobs.criteria JSONB + indexes
│       └── 003_scraper_runs.py       # scraper health tracking
│
├── infra/
│   ├── docker-compose.yml            # Local dev: Postgres only (no Redis needed)
│   ├── Dockerfile.api                # For Koyeb deployment
│   └── koyeb.yaml                    # Koyeb service config
│
├── tests/
│   ├── api/                          # pytest: API route tests
│   ├── scripts/
│   │   ├── test_extractor.py         # Golden-set extraction accuracy (Gemini)
│   │   ├── test_matcher.py           # Rule engine unit tests
│   │   └── test_scrapers/            # Per-scraper fixture tests
│   └── e2e/                          # End-to-end with real DB
│
├── .github/
│   └── workflows/
│       ├── ci-api.yml                # pytest on push to apps/api/**
│       ├── ci-scripts.yml            # pytest on push to scripts/**
│       ├── ci-web.yml                # lint + build + test on push to apps/web/**
│       ├── scrape.yml                # cron every 6h: scrape + extract
│       ├── weekly-digest.yml         # cron every Monday: send digest emails
│       └── deploy.yml                # on merge to main: deploy to Koyeb + Vercel
│
├── .env.example                      # All required keys (see Pre-Implementation Setup)
├── Makefile
└── ARCHITECTURE.md                   # This file
```

---

## Running Each Component Independently

```bash
# ─── Prerequisites (one-time) ───────────────────────────────────────────
cp .env.example .env          # fill in keys (see setup section below)
make install

# ─── Database only ──────────────────────────────────────────────────────
make db-start                 # start local Postgres
make db-migrate               # run alembic migrations
make db-reset                 # wipe and re-migrate (dev only)

# ─── API only ────────────────────────────────────────────────────────────
make api                      # uvicorn on :8000
# → http://localhost:8000/docs  (Swagger UI)

# ─── Frontend only ───────────────────────────────────────────────────────
make web                      # next dev on :3000
# → http://localhost:3000

# ─── Run scraper pipeline manually (no server needed) ────────────────────
cd scripts
python run_pipeline.py --source ssc      # scrape SSC only
python run_pipeline.py --dry-run         # scrape but don't write to DB
python run_pipeline.py                   # all sources

# ─── Run extractor on a local PDF ────────────────────────────────────────
python scripts/extractor.py --file ./tests/fixtures/ssc_cgl_2026.pdf

# ─── Test matcher for a specific user (hit local API) ────────────────────
curl -H "Authorization: Bearer <token>" http://localhost:8000/api/v1/jobs

# ─── Full local stack (Postgres + API + Web) ─────────────────────────────
make dev                      # docker-compose up (Postgres) + uvicorn + next dev
```

**Makefile targets:**
```makefile
install:      pip install -r apps/api/requirements.txt -r scripts/requirements.txt \
              && pip install -e packages/schema \
              && cd apps/web && npm install
db-start:     docker compose -f infra/docker-compose.yml up -d postgres
db-migrate:   cd db && alembic upgrade head
db-reset:     cd db && alembic downgrade base && alembic upgrade head
api:          cd apps/api && uvicorn main:app --reload --port 8000
web:          cd apps/web && npm run dev
dev:          make db-start && make api & make web
test-api:     pytest tests/api -v
test-scripts: pytest tests/scripts -v
test-web:     cd apps/web && npm run test
test-all:     make test-api && make test-scripts && make test-web
```

---

## CI/CD Pipeline

```
Push to feature branch
        │
        ▼
┌─────────────┐  ┌──────────────┐  ┌─────────────┐
│ ci-api.yml  │  │ci-scripts.yml│  │ ci-web.yml  │  ← run in parallel
│  (pytest)   │  │  (pytest)    │  │(build+test) │
└──────┬──────┘  └──────┬───────┘  └──────┬──────┘
       └─────────────────┼─────────────────┘
                         │ all pass
                         ▼
                 Open Pull Request
                         │
                         ▼
                 Merge to main
                         │
                         ▼
                  deploy.yml runs
          ┌──────────────┴──────────────┐
          ▼                             ▼
  Koyeb (API)                   Vercel (Web)
  (auto via koyeb.yaml)         (auto via Vercel GitHub integration)
```

### `.github/workflows/ci-api.yml`
```yaml
name: CI — API
on:
  push:
    paths: ['apps/api/**', 'packages/schema/**', 'db/**']
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_DB: jobai_test, POSTGRES_PASSWORD: test }
        ports: ['5432:5432']
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r apps/api/requirements.txt && pip install -e packages/schema
      - run: cd db && alembic upgrade head
        env: { DATABASE_URL: postgresql+asyncpg://postgres:test@localhost/jobai_test }
      - run: pytest tests/api -v
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:test@localhost/jobai_test
          JWT_SECRET: test-secret-do-not-use-in-production
```

### `.github/workflows/ci-scripts.yml`
```yaml
name: CI — Scripts
on:
  push:
    paths: ['scripts/**', 'packages/schema/**']
jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
        env: { POSTGRES_DB: jobai_test, POSTGRES_PASSWORD: test }
        ports: ['5432:5432']
        options: --health-cmd pg_isready --health-interval 10s --health-timeout 5s --health-retries 5
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.12' }
      - run: pip install -r scripts/requirements.txt && pip install -e packages/schema
      - run: pytest tests/scripts -v
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:test@localhost/jobai_test
          GOOGLE_AI_API_KEY: ${{ secrets.GOOGLE_AI_API_KEY }}
```

### `.github/workflows/ci-web.yml`
```yaml
name: CI — Web
on:
  push:
    paths: ['apps/web/**']
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: cd apps/web && npm ci
      - run: cd apps/web && npm run lint
      - run: cd apps/web && npm run build    # catches TS type errors
      - run: cd apps/web && npm run test
```

### `.github/workflows/deploy.yml`
```yaml
name: Deploy
on:
  push:
    branches: [main]
jobs:
  deploy-api:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to Koyeb
        uses: koyeb/action-git-deploy@v1
        with:
          api-token: ${{ secrets.KOYEB_TOKEN }}
          app-name: jobai-api
          service-name: api
          git-branch: main

  # Vercel deploys automatically via its GitHub integration (no workflow needed).
  # Add this job only if you need to control deploy order.
```

### Branch strategy
```
main          ← production (protected, CI must pass, PR required)
  └─ dev      ← integration (auto-deploys to staging)
       └─ feature/xxx  ← individual features, CI runs on push
```

---

## Cost Estimate — V1 (Zero Cost)

| Service | Plan | Monthly cost | Free limit | V1 usage |
|---|---|---|---|---|
| Vercel (frontend) | Hobby | **$0** | 100 GB bandwidth | << limit |
| Koyeb (API) | Nano | **$0** | 0.1 vCPU / 256 MB | sufficient for MVP |
| Neon (database) | Free | **$0** | 0.5 GB storage | ~230 MB after 12mo |
| GitHub Actions (workers) | Free | **$0** | 2000 min/mo (private) | ~1200 min/mo |
| Gemini 2.0 Flash (LLM) | AI Studio free | **$0** | 1500 req/day | ~167 req/day |
| Cloudflare R2 (storage) | Free | **$0** | 10 GB / 1M writes | << limit |
| Resend (email) | Free | **$0** | 3000 emails/mo | limited to 3K |
| Sentry (error tracking) | Free | **$0** | 5000 events/mo | sufficient |
| **Total** | | **$0/month** | | |

**When to upgrade:** Once revenue covers it, upgrade Koyeb to a paid instance (removes the 256MB RAM constraint) and switch the LLM to Claude Haiku (faster, better structured output). The architecture requires no code changes — only env vars swap.

---

## Pre-Implementation Setup Checklist

Complete this before writing any code. All services are free — no CC charges unless you upgrade.

### Step 1 — Accounts to Create

| # | Service | URL | What to do | Time |
|---|---|---|---|---|
| 1 | **GitHub** | github.com | Create account + new repo (make it **public** for unlimited Actions minutes) | 5 min |
| 2 | **Vercel** | vercel.com | Sign up with GitHub, import the repo, set framework to Next.js | 5 min |
| 3 | **Koyeb** | koyeb.com | Sign up with GitHub, connect repo | 5 min |
| 4 | **Neon** | neon.tech | Create account → New Project → `jobai` → copy connection string | 5 min |
| 5 | **Google AI Studio** | aistudio.google.com | Sign in with Google → "Get API key" → create key → copy it | 2 min |
| 6 | **Cloudflare** | cloudflare.com | Create account → R2 → Create bucket `jobai-raw` → Create API token with R2 edit permissions | 10 min |
| 7 | **Resend** | resend.com | Create account → API Keys → Create key → copy it | 3 min |
| 8 | **Sentry** | sentry.io | Create account → New Project (Python FastAPI) → New Project (Next.js) → copy both DSNs | 5 min |

**Note on Cloudflare R2:** Cloudflare requires a credit card to create an account for fraud prevention, but the R2 free tier (10 GB, 1M writes/month) is genuinely free — you will not be charged.

### Step 2 — Local Software to Install

| Software | Version | Windows install |
|---|---|---|
| **Python** | 3.12+ | python.org → download installer → ✓ "Add to PATH" |
| **Node.js** | 20 LTS | nodejs.org → LTS installer |
| **PostgreSQL** | 16 | postgresql.org/download/windows/ → default install |
| **Git** | latest | git-scm.com |
| **VS Code** | latest | code.visualstudio.com (recommended: install Python + ESLint extensions) |

Verify installs:
```powershell
python --version    # should show 3.12.x
node --version      # should show v20.x.x
psql --version      # should show 16.x
git --version
```

### Step 3 — GitHub Repository Secrets

After creating your GitHub repo, go to **Settings → Secrets and variables → Actions → New repository secret** and add each of these:

| Secret name | Where to get it | Example value |
|---|---|---|
| `DATABASE_URL` | Neon dashboard → Connection string | `postgresql+asyncpg://user:pass@ep-xxx.neon.tech/jobai?ssl=require` |
| `DATABASE_URL_SYNC` | Same as above but `postgresql://` (no `+asyncpg`, for Alembic) | `postgresql://user:pass@ep-xxx.neon.tech/jobai?sslmode=require` |
| `GOOGLE_AI_API_KEY` | Google AI Studio | `AIzaSy...` |
| `CLOUDFLARE_ACCOUNT_ID` | Cloudflare dashboard → right sidebar | `abc123def456...` |
| `CLOUDFLARE_R2_ACCESS_KEY_ID` | R2 → Manage R2 API tokens | `abc...` |
| `CLOUDFLARE_R2_SECRET_KEY` | R2 → Manage R2 API tokens | `xyz...` |
| `R2_BUCKET_NAME` | Name you chose when creating bucket | `jobai-raw` |
| `RESEND_API_KEY` | Resend dashboard → API Keys | `re_...` |
| `SENTRY_DSN_API` | Sentry → jobai-api project → DSN | `https://abc@sentry.io/123` |
| `SENTRY_DSN_WEB` | Sentry → jobai-web project → DSN | `https://xyz@sentry.io/456` |
| `SENTRY_DSN_WORKERS` | Same as SENTRY_DSN_API or separate | `https://abc@sentry.io/123` |
| `JWT_SECRET` | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` | `a3f9c2...` (64-char hex) |
| `KOYEB_TOKEN` | Koyeb dashboard → API Access Tokens | `koy_...` |
| `VERCEL_TOKEN` | Vercel → Settings → Tokens | `abc...` |
| `VERCEL_ORG_ID` | Vercel → Settings → General → Team ID | `team_...` |
| `VERCEL_PROJECT_ID` | Vercel → Project → Settings → General | `prj_...` |

### Step 4 — `.env.example` (commit this, never commit `.env`)

```bash
# Database
DATABASE_URL=postgresql+asyncpg://jobai:jobai@localhost:5432/jobai_dev
DATABASE_URL_SYNC=postgresql://jobai:jobai@localhost:5432/jobai_dev

# LLM (free from aistudio.google.com)
GOOGLE_AI_API_KEY=

# Auth
JWT_SECRET=                    # generate with: python -c "import secrets; print(secrets.token_hex(32))"
JWT_EXPIRE_HOURS=24

# Cloudflare R2 storage
CLOUDFLARE_ACCOUNT_ID=
CLOUDFLARE_R2_ACCESS_KEY_ID=
CLOUDFLARE_R2_SECRET_KEY=
R2_BUCKET_NAME=jobai-raw
R2_PUBLIC_URL=                 # optional: public R2 URL if you enable public access

# Email
RESEND_API_KEY=
FROM_EMAIL=noreply@yourdomain.com

# Error tracking
SENTRY_DSN_API=
SENTRY_DSN_WEB=
SENTRY_DSN_WORKERS=

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000   # change to Koyeb URL in production
```

### Step 5 — First-Run Commands (after all accounts are set up)

```powershell
# 1. Clone repo and install dependencies
git clone https://github.com/yourusername/jobai.git
cd jobai
make install

# 2. Create local database
psql -U postgres -c "CREATE DATABASE jobai_dev;"
psql -U postgres -c "CREATE USER jobai WITH PASSWORD 'jobai'; GRANT ALL ON DATABASE jobai_dev TO jobai;"

# 3. Copy env and fill in your keys
cp .env.example .env
# (open .env in VS Code and fill in the values from Step 3)

# 4. Run migrations
make db-migrate

# 5. Start the API and verify it works
make api
# Open http://localhost:8000/docs — you should see the Swagger UI

# 6. Start the frontend
make web
# Open http://localhost:3000

# 7. Run your first scrape manually
python scripts/run_pipeline.py --dry-run --source ssc
```

---

## Koyeb Deployment Config

```yaml
# infra/koyeb.yaml
name: jobai-api
services:
  - name: api
    type: web
    git:
      repository: github.com/yourusername/jobai
      branch: main
      buildpack: python
      build_command: pip install -r apps/api/requirements.txt && pip install -e packages/schema
      run_command: uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
    instance_type: nano
    regions:
      - sin    # Singapore — lowest latency for Indian users
    ports:
      - port: 8000
        protocol: http
    health_checks:
      - path: /health
        port: 8000
    env:
      - key: DATABASE_URL
        secret: DATABASE_URL
      - key: JWT_SECRET
        secret: JWT_SECRET
      - key: GOOGLE_AI_API_KEY
        secret: GOOGLE_AI_API_KEY
      - key: RESEND_API_KEY
        secret: RESEND_API_KEY
      - key: SENTRY_DSN
        secret: SENTRY_DSN_API
```

---

## Free Tier Limitations to Know Before Launch

| Limitation | Impact | Mitigation |
|---|---|---|
| Neon auto-suspends compute after 5 min idle | First DB query after idle ~1-2s cold start | Add `/health` endpoint on Koyeb that pings DB every 4 min (keep-alive) |
| Koyeb nano: 256 MB RAM | Limits concurrency; 3-5 simultaneous users OK | Upgrade to standard ($5.50/mo) when traffic grows |
| Gemini 1500 req/day | If extraction backlog > 1500 jobs/day, hits limit | Spread extraction over multiple cron runs; only possible at very high job volume |
| Resend 3K emails/mo | ~750 weekly digest users max | Skip digest for inactive users (no profile = no email) |
| GitHub Actions 2000 min/mo | Covers scraping; fails if repo is private and usage spikes | Make repo public (unlimited) or stagger scraper runs |
| Cloudflare R2 needs CC | Signup friction | One-time setup; no charge ever on free tier |

---

## Reference / Prior Art

- **FreeJobAlert, Sarkari Result, Rojgar Result, Employment News** — Indian govt-job aggregators. Content/listing sites; **none do personalized eligibility matching**. That's the differentiation.
- **Jobscan** — resume↔JD matching for private-sector jobs. Same structured-extraction pattern, different problem.
- **LinkedIn / Indeed / Adzuna** — ML ranking over private listings; no hard eligibility-rules layer.
- **Boundless / VisaHQ** — visa eligibility checkers. Closest architecture analogue: structured criteria extraction + rules engine.
- **Govt-side: NCS (National Career Service) portal** — has listings but zero personalized eligibility filter.

The **"structured extraction + rules engine"** pattern is the right one here — borrow from compliance tech, not from job boards.

---

## Verification Plan

1. **Extraction accuracy** — golden set of 20 real notifications (SSC, UPSC, Railways, Employment News). Target: ≥90% field accuracy on deterministic fields using Gemini 2.0 Flash.
2. **Matcher correctness** — unit tests per rule: age relaxation matrix, qualification equivalence, physical standards. Use `pytest` with parametrize for all category combinations.
3. **End-to-end** — seed 5 diverse synthetic profiles + 10 real scraped jobs → manually verify eligible sets match expected output.
4. **Scraper health** — `scraper_runs` table + `/admin/health` endpoint shows per-source last-run status. GH Actions sends failure notification email if any run fails.
5. **Free tier headroom** — monitor monthly: Neon storage (target: <400 MB), GH Actions minutes (target: <1800/mo), Gemini requests (target: <1000/day).

---

## Key Open Questions

1. **Neon keep-alive:** Should the FastAPI `/health` endpoint ping the DB to prevent the 5-min compute suspend? Trade-off: keeps DB warm (better UX) vs uses Neon's free compute hours faster. Recommend: yes, ping every 4 minutes from Koyeb's health check config.
2. **Scraping legal posture** — govt notifications are public-domain but portal ToS varies. Always include attribution + link-out to official source; never host the job form itself.
3. **Amendments / corrigenda** — re-trigger extraction when content hash changes; re-run matcher for affected users (in pull model, this is automatic — fresh on next feed load).
4. **V2 trigger:** When to move from pull matching to push (pre-computed)? When >5K daily active users and feed load >500ms p95. That's when Neon's 0.5GB also gets tight — both signals point to the same upgrade moment.
