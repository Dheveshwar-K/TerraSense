# PS-010 System Architecture

## 1. Overview & System Philosophy

**PS-010** is an industrial-grade **Quality 4.0** digital foundry management platform designed for foundries running modern high-pressure vertical and horizontal flaskless green sand molding lines (Disamatic lines **D1**, **D2**, **D3**, and **D4**).

The system replaces error-prone, paper-based sand testing and fragmented Excel logs with an integrated digital workflow connecting shop-floor tablet sand testing, automated Statistical Process Control (SPC), casting rejection monitoring, and time-lagged defect correlation.

```
                      +-----------------------------------------+
                      |       Shop Floor Tablets & Desktops     |
                      |   (React 19 + TypeScript + Vite + CSS)  |
                      +--------------------+--------------------+
                                           |
                              REST API / JSON / Tokens
                                           |
                      +--------------------+--------------------+
                      |       FastAPI Application Gateway       |
                      |    (Python 3.12+ ASGI High-Throughput)  |
                      +----+-------------------------------+----+
                           |                               |
         +-----------------+-------------+   +-------------+-----------------+
         |   SPC & Analytics Engines     |   |  Quality & Compliance Services  |
         |  - I-MR / X-bar & R Engine   |   |  - Specification Revisioning    |
         |  - Nelson 8 Rules Evaluator   |   |  - Automated Alert Engine       |
         |  - Capability (Cp, Cpk, Pp)   |   |  - Customer Complaints & 8D     |
         |  - Lagged Correlation Engine  |   |  - IATF 16949 Audit Trail       |
         +-----------------+-------------+   +-------------+-----------------+
                           |                               |
                           +---------------+---------------+
                                           |
                                   SQLAlchemy 2.0 ORM
                                           |
                      +--------------------+--------------------+
                      |         Normalized Database             |
                      |    PostgreSQL (Prod) / SQLite (Dev)     |
                      +-----------------------------------------+
```

---

## 2. Module Breakdown

### 2.1 Authentication & Role-Based Access Control (RBAC)
- Token-based JWT authentication (`HS256`, 7-day expiration).
- Secure password hashing using PBKDF2-HMAC-SHA256 (100,000 rounds) with cryptographically secure random salt.
- Granular permissions enforced at backend endpoints and frontend route guards:
  - `operator`: Enter hourly/shift sand tests, view specifications, request data corrections, view alerts.
  - `quality_engineer`: Full access to SPC charts, parameter specification revisions, rejection tracking, 8D CAPA, approve corrections.
  - `supervisor`: Production shift monitoring, quality deviation tracking, scrap analytics.
  - `quality_manager` / `admin`: Full administrative governance, system configuration, audit logs, specification approvals.

### 2.2 Parameter & Specification Management
- Engineering specifications (**LSL**, **USL**, **Target**) are strictly separated from statistical control limits (**LCL**, **UCL**).
- Historical revision history: when specifications are revised, past sand tests preserve the revision number active at test time.
- Physical parameters: Moisture (%), Compactability (%), Green Compression Strength (N/cm²), Permeability (Perm No.), Shear Strength (N/cm²), Mold Hardness (B-scale), Active Clay (%), Total Clay (%), Loss on Ignition (%), Grain Fineness Number (AFS GFN), Wet Tensile Strength (N/cm²), Return Sand Temp (°C).
- Chemical parameters: Volatile Matter (%), Dead Clay (%), Bentonite Addition Rate (%).

### 2.3 Statistical Process Control (SPC) Engine
- **Individuals & Moving Range (I-MR)**:
  - Within-process standard deviation: $\hat{\sigma}_{within} = \frac{\overline{MR}}{d_2}$ ($d_2 = 1.128379$ for $n=2$).
  - Individuals chart: $CL = \overline{X}$, $UCL = \overline{X} + 3\hat{\sigma}_{within}$, $LCL = \overline{X} - 3\hat{\sigma}_{within}$.
  - Moving Range chart: $CL = \overline{MR}$, $UCL = 3.267 \times \overline{MR}$, $LCL = 0$.
- **X-bar & R Charts**: Subgrouped by production shift or calendar date with standard ASTM/ISO factors ($A_2, D_3, D_4, d_2$).
- **Nelson 8 Rules Out-of-Control Detection**: Evaluates 3-sigma excursions, 9-point runs, 6-point trends, 14 alternating points, and zone stratifications.
- **Process Capability**: Computes $C_p, C_{pk}, P_p, P_{pk}$ with stability checks, sample size checks ($N \ge 20$), normality tests, and PPM defect projections.

### 2.4 Rejection & Defect Pareto Module
- Direct tracking of casting defect categories: Porosity, Blowholes, Sand Inclusion, Scab, Mismatch, Cold Shut, Shrinkage, Surface Roughness.
- Formula: $\text{Rejection Rate \%} = \frac{\text{Rejected Qty}}{\text{Inspected Qty}} \times 100$.
- Interactive 80/20 Pareto chart isolating the "vital few" defect contributors from the "trivial many".

### 2.5 Sand Quality & Rejection Correlation Engine
- Time-lag windowing ($\Delta t \in \{0, 6, 12, 24, 48, 72\}$ hours) pairing upstream sand preparation with downstream inspection.
- Pearson correlation coefficient ($r$) and Spearman rank correlation ($\rho$) with statistical significance testing ($p < 0.05$).
- Group comparisons: Calculates the scrap risk ratio between Out-of-Spec and In-Spec sand runs.
- Non-causal phrasing standards: explicitly frames findings as candidate contributing factors for 8D investigation, adhering to the fundamental rule that *correlation does not establish causation*.

### 2.6 Digital Audit Trail & IATF 16949 Compliance
- Immutable ledger recording actor, timestamp, action (`CREATE`, `UPDATE`, `CORRECTION`, `APPROVE`, `EXPORT`), entity, old value, new value, reason, and IP address.
- Built-in JSON diff viewer in the UI.
