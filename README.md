# PS-010: Integrated Digital Sand Quality Management & Rejection Analytics System

[![Quality 4.0](https://img.shields.io/badge/Foundry-Quality%204.0-blue.svg)](#)
[![IATF 16949](https://img.shields.io/badge/Compliance-IATF%2016949-emerald.svg)](#)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python%203.12-009688.svg)](#)
[![React 19](https://img.shields.io/badge/Frontend-React%2019%20%7C%20TypeScript%20%7C%20Vite-61dafb.svg)](#)
[![Tailwind 4](https://img.shields.io/badge/Styles-Tailwind%20CSS%204-38bdf8.svg)](#)

An industrial-grade Quality 4.0 application built for foundry green sand molding lines **D1**, **D2**, **D3**, and **D4**. 

Replaces paper-based log sheets with a centralized digital platform featuring shop-floor tablet test entry, real-time Statistical Process Control (SPC), casting rejection monitoring, 8D customer complaint resolution, and a time-lagged defect correlation engine.

---

## Key Capabilities

1. **Centralized Production Lines Management (D1, D2, D3, D4)**:
   - Separate historical data, shift scheduling, and status tracking for four automated green sand lines.
2. **Tablet-Optimized Digital Test Entry**:
   - High-contrast, large touch-input keypad for operators on the factory floor.
   - Real-time instant tolerance validation: green (In Spec), amber (Warning Margin), red (Out-of-Spec).
   - Accidental duplicate submission prevention.
3. **Automated SPC Engine**:
   - Individuals and Moving Range (**I-MR**) control charts with $\hat{\sigma}_{within} = \frac{\overline{MR}}{d_2}$ within-process estimation.
   - Subgrouped **X-bar & R** charts with standard ASTM/ISO factors.
   - **Nelson 8 Rules** special-cause variation evaluator with exact root-cause descriptions.
   - Process Capability (**$C_p, C_{pk}, P_p, P_{pk}$**) with stability checks, sample size verification ($N \ge 20$), normality tests, and projected PPM defective.
4. **Casting Rejection & Defect Pareto**:
   - Shift-wise scrap logging across 8 major foundry defect categories (Porosity, Blowholes, Sand Inclusion, Scab, Mismatch, Cold Shut, Shrinkage, Surface Roughness).
   - Interactive **80/20 Pareto Chart** with cumulative percentage curve and threshold cutoff.
5. **Sand Quality & Rejection Correlation Engine**:
   - Time-lag analysis ($\Delta t \in \{0, 6, 12, 24, 48, 72\}$ hours) linking upstream sand properties with downstream inspection scrap.
   - Pearson ($r$) and Spearman ($\rho$) correlation coefficients with statistical significance testing ($p < 0.05$).
   - Group comparison (Scrap risk ratio between Out-of-Spec and In-Spec runs).
   - Responsible non-causal phrasing ("Correlation does not prove causation. Potential contributing factor requiring engineering investigation").
6. **Customer Complaints & 8D CAPA**:
   - Full 8-Discipline (D1-D8) investigation dossier linked to sand batches and rejection lots.
7. **Quality Alert System**:
   - Automated real-time triggers for specification limits and Nelson rule violations.
   - Acknowledge and Resolve workflow with mandatory containment notes.
8. **IATF 16949 Digital Audit Trail**:
   - Immutable event ledger with built-in JSON diff viewer.
9. **One-Click Industrial Reporting**:
   - Instant export of publication-grade PDF, Excel (.xlsx), and RFC-compliant CSV reports.

---

## Default User Accounts & RBAC

The system provides a **Quick Role Switcher** dropdown in the header to allow evaluators to instantly test the system under each persona:

| Username | Password | Role | Description |
|---|---|---|---|
| `operator` | `operator123` | **Operator** | Shop-floor sand test entry, physical testing checks. |
| `quality_engineer` | `quality123` | **Quality Engineer** | SPC charts, specification revisions, scrap investigations, 8D CAPA. |
| `supervisor` | `super123` | **Production Supervisor** | Shift performance monitoring, deviation tracking. |
| `admin` | `admin123` | **Quality Manager / Admin** | Administrative governance, audit review, specification approvals. |

---

## Quickstart Guide

### 1. Backend (FastAPI + Python 3.12+)
```powershell
# In PowerShell from project root:
$env:PYTHONPATH = "d:\Projects\Sakthi Hack\backend"
& "C:\Users\DHEVESHWAR K\AppData\Local\Python\bin\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
OpenAPI Documentation: `http://127.0.0.1:8000/docs`

### 2. Frontend (React 19 + TypeScript + Vite)
```powershell
cd frontend
npm run dev
```
Web Application: `http://localhost:5173`

### 3. Automated Tests
```powershell
$env:PYTHONPATH = "d:\Projects\Sakthi Hack\backend"
& "C:\Users\DHEVESHWAR K\AppData\Local\Python\bin\python.exe" -m pytest "backend/tests" -v
```
All 7 unit tests covering password hashing, JWT tokens, I-MR control limits, Nelson rules, Process Capability, and Correlation Analysis pass 100%.

### 4. Docker Deployment
```bash
docker-compose up --build -d
```
Runs PostgreSQL, FastAPI Backend, and Nginx-served React frontend in isolated production containers.

---

## Project Structure

```
PS-010/
├── backend/
│   ├── app/
│   │   ├── api/             # REST API routes and auth dependencies
│   │   ├── core/            # Database engine, JWT security, config
│   │   ├── models/          # Normalized SQLAlchemy 2.0 ORM models
│   │   ├── schemas/         # Pydantic v2 validation models
│   │   ├── services/        # SPC engine, Correlation engine, Alert engine, Reports
│   │   └── main.py          # FastAPI application entrypoint
│   ├── tests/               # Pytest suite with mathematical test cases
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── components/      # Sidebar, Header, StatCards, StatusBadges
│   │   ├── context/         # AuthContext & Demo Role Switcher
│   │   ├── pages/           # 17 interactive Quality 4.0 views
│   │   ├── services/        # Typed API client
│   │   ├── types/           # TypeScript definitions
│   │   └── App.tsx          # Router layout
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── docs/                    # Architecture, SPC formulas, and Deployment guides
├── docker-compose.yml
└── README.md
```
