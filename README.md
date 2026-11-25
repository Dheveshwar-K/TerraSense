# TerraSense (PS-010): Integrated Digital Sand Quality Management & Rejection Analytics System

[![Quality 4.0](https://img.shields.io/badge/Foundry-Quality%204.0-blue.svg)](#)
[![IATF 16949](https://img.shields.io/badge/Compliance-IATF%2016949-emerald.svg)](#)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.12+-009688.svg)](#)
[![React 19](https://img.shields.io/badge/Frontend-React%2019%20%7C%20TypeScript%20%7C%20Vite-61dafb.svg)](#)
[![Tailwind 4](https://img.shields.io/badge/Styles-Tailwind%20CSS%204-38bdf8.svg)](#)

An industrial **Quality 4.0** platform built for green sand molding lines **D1**, **D2**, **D3**, and **D4**.

Replaces paper-based foundry sand logs with a centralized digital platform featuring shop-floor tablet test entry, real-time Statistical Process Control (SPC), casting rejection Pareto analytics, 8D customer complaint resolution, a time-lagged defect correlation engine, and a SHA-256 hash-chained IATF 16949 audit trail.

---

## Key Capabilities

1. **Centralized Production Lines Management (D1–D4)**:
   - Historical telemetry, shift scheduling, muller batch logs, and health tracking for four green sand molding lines.
2. **Tablet-Optimized Digital Test Entry**:
   - Large numeric inputs with instant physical sensor bounds and tolerance validation (`OK`, `WARNING`, `OUT_OF_SPEC`).
   - Duplicate `(line, date, shift, hour, test_type)` prevention at both API and database constraint levels, plus dual-control measurement correction workflows.
3. **Validated Statistical Process Control (SPC) Engine**:
   - **I-MR Control Charts** with $\hat{\sigma}_{\text{within}} = \overline{MR} / d_2$ ($d_2 = 1.12837917$), $UCL_{MR} = 3.26653 \cdot \overline{MR}$, missing/NaN filtering, constant-data guards, and chronological sorting.
   - **Subgrouped X-bar & R Charts** with ASTM E2587 / ISO 7870 constants ($n=2..15$) and exact subgroup-specific limits for variable subgroup sizes.
   - **All 8 Nelson Rules** independently validated for special-cause variation.
   - **Stability-Gated Process Capability ($C_p, C_{pk}, P_p, P_{pk}$)** with explicit stability assessment (`STABLE` vs `UNSTABLE` exploratory mode), zero-variance protection, Shapiro-Wilk normality testing, and normal-model PPM/yield projections.
4. **Casting Rejection & Defect Pareto**:
   - Shift-wise scrap logging across 8 major foundry defect categories with strict quantity invariants (`inspected_qty > 0`, `0 <= rejected_qty <= inspected_qty`).
   - Interactive 80/20 Pareto chart with date/line filters.
5. **Time-Lagged Sand Quality & Rejection Correlation Engine**:
   - Causal time-window alignment ($\Delta t \in \{0, 6, 12, 24, 48, 72\}$ hours) with strict `sand_time <= rejection_time` enforcement to prevent future data leakage.
   - Pearson ($r$) with Fisher 95% CI, Spearman ($\rho$), OOS vs In-Spec scrap ratio, Benjamini-Hochberg FDR multiple-testing correction, and non-causal engineering phrasing.
6. **Customer Complaints, 8D CAPA & 5-Why/Ishikawa Investigations**:
   - Persistent 8-Discipline (D1–D8) dossiers and 5-Why / 6M Fishbone root-cause records with optimistic locking (`expected_version`).
7. **Quality Alert Engine**:
   - Real-time spec violation and Nelson rule alert triggers with deduplication, acknowledgment, and mandatory resolution notes.
8. **Hash-Chained IATF 16949 Digital Audit Trail**:
   - Append-only SHA-256 hash-chained ledger (`sequence_no`, `prev_hash`, `record_hash`, `outcome`) with `/api/audit-logs/verify` tamper detection and JSON diff inspection.
9. **Authenticated Industrial Reporting**:
   - Token-safe Blob exports (no tokens in URLs) for PDF, Excel (`.xlsx` with formula-injection neutralization), and RFC 4180 CSV.

---

## Security, Demo Mode & RBAC

- **Production Guardrails**: When `ENVIRONMENT=production`, startup refuses placeholder/weak `SECRET_KEY` values, refuses `DEMO_MODE=true`, refuses SQLite, and refuses placeholder database passwords.
- **Authentication**: `scrypt` memory-hard password hashing (with backward-compatible PBKDF2 verification and transparent upgrade), short-lived JWT access tokens (30m default), rotating refresh tokens, logout JTI revocation, account lockout, and sliding-window login rate limiting.
- **Demo Mode Isolation**: Demo persona switching (`POST /api/auth/demo-switch`) and demo seeding (`POST /api/system/seed`) are strictly blocked (`403 Forbidden`) unless `DEMO_MODE=true` in a non-production environment.

| Role | Sand Entry & Corrections | SPC & Correlations | Rejections & 5-Why | Specs, 8D & Resolve Alerts | Audit Logs & Reports | User Admin |
|---|---|---|---|---|---|---|
| `operator` | Create / Request | View | View | View Only | Restricted | Restricted |
| `supervisor` | Create / Request | View | Create / Log | View Only | View / Export | Restricted |
| `quality_engineer` | Full + Approve/Reject | Full | Full | Full | Full + Verify | Restricted |
| `quality_manager` / `admin` | Full | Full | Full | Full | Full + Verify | Full CRUD |

---

## Quickstart Guide

### 1. Environment Configuration
```bash
cp .env.example .env
# Generate a strong secret key:
python -c "import secrets; print(secrets.token_hex(32))"
```
For local demo evaluation, set `ENVIRONMENT=demo` and `DEMO_MODE=true` in `.env` (never in production).

### 2. Backend (FastAPI + Python 3.12+)
```powershell
$env:PYTHONPATH = "d:\Projects\Sakthi Hack\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Frontend (React 19 + TypeScript + Vite)
```powershell
cd frontend
npm install
npm run dev
```
Web Application: `http://localhost:5173` (proxying `/api` to `http://127.0.0.1:8000`).

### 4. Automated Verification
```powershell
# Backend tests (SPC math, correlation, security, RBAC, audit hash chain, API workflows)
$env:PYTHONPATH = "d:\Projects\Sakthi Hack\backend;d:\Projects\Sakthi Hack"
python -m pytest backend/tests -v

# Frontend lint & production build
cd frontend
npm run lint
npm run build
```

### 5. Docker Deployment
- **Production** (requires `.env` with strong `POSTGRES_PASSWORD` and `SECRET_KEY`, `ENVIRONMENT=production`, `DEMO_MODE=false`):
  ```bash
  docker compose up --build -d
  ```
- **Local Demo Evaluation**:
  ```bash
  docker compose -f docker-compose.yml -f docker-compose.demo.yml up --build -d
  ```

---

## Project Structure

```
TerraSense/
├── backend/
│   ├── alembic/                 # Alembic migration environment & revisions
│   ├── app/
│   │   ├── api/                 # REST API routes, RBAC deps, rate limiting
│   │   ├── core/                # Config validation, DB engine, scrypt/JWT, migrations
│   │   ├── models/              # SQLAlchemy 2.0 ORM models with CheckConstraints
│   │   ├── schemas/             # Pydantic v2 strict validation schemas
│   │   ├── services/            # SPC, Correlation, Alert, Audit Hash Chain, Reports
│   │   └── main.py              # FastAPI entrypoint, security headers, health/ready
│   ├── tests/                   # Pytest unit, math, security, RBAC, and integration tests
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/          # Header, Sidebar, LoginScreen, StatCard, StatusBadge
│   │   ├── context/             # AuthContext (session/refresh/demo), ToastContext
│   │   ├── pages/               # 17 Quality 4.0 operational views
│   │   ├── services/            # Typed API client with refresh & authenticated exports
│   │   └── types/               # TypeScript contracts
│   ├── nginx.conf               # Reverse proxy + security headers
│   └── Dockerfile
├── scripts/                     # PostgreSQL & SQLite verified backup/restore scripts
├── docs/                        # Architecture, SPC Methodology, Deployment Guide
├── docker-compose.yml
├── docker-compose.demo.yml
└── .env.example
```

**GitHub Topics**: `foundry-quality`, `statistical-process-control`, `quality-4-0`, `iatf-16949`, `fastapi`, `react`, `typescript`, `postgresql`, `spc-charts`, `manufacturing-analytics`
