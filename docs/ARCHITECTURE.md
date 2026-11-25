# PS-010 System Architecture

## 1. Overview & System Philosophy

**TerraSense (PS-010)** is an industrial **Quality 4.0** digital foundry management platform designed for green sand molding lines (**D1**, **D2**, **D3**, and **D4**).

```
                      +-----------------------------------------+
                      |       Shop Floor Tablets & Desktops     |
                      |   (React 19 + TypeScript + Vite + TW4)  |
                      +--------------------+--------------------+
                                           |
                       REST API / JSON / Bearer JWT (30m + Refresh)
                                           |
                      +--------------------+--------------------+
                      |       FastAPI Application Gateway       |
                      |  Security Headers | Rate Limit | RBAC   |
                      +----+-------------------------------+----+
                           |                               |
         +-----------------+-------------+   +-------------+-----------------+
         |   SPC & Analytics Engines     |   |  Quality & Compliance Services  |
         |  - I-MR / X-bar & R Engine   |   |  - Spec Revision & Versioning   |
         |  - Nelson 8 Rules Evaluator   |   |  - Automated Alert Engine       |
         |  - Stability-Gated Capability |   |  - 8D CAPA & 5-Why Dossiers     |
         |  - Lagged Correlation + FDR   |   |  - SHA-256 Hash-Chained Audit   |
         +-----------------+-------------+   +-------------+-----------------+
                           |                               |
                           +---------------+---------------+
                                           |
                              SQLAlchemy 2.0 + Migrations
                                           |
                      +--------------------+--------------------+
                      |         Normalized Database             |
                      |    PostgreSQL 16 (Prod) / SQLite (Dev)  |
                      +-----------------------------------------+
```

---

## 2. Module Breakdown

### 2.1 Authentication, Session Lifecycle & RBAC
- **Password Hashing**: Memory-hard `hashlib.scrypt` (`N=16384, r=8, p=1`) with 16-byte random salt; verifies legacy PBKDF2-HMAC-SHA256 hashes and upgrades transparently on login.
- **Tokens**: Short-lived JWT access tokens (default 30 min) + rotating refresh tokens (7 days) with `jti` tracking in `revoked_tokens` and `token_version` invalidation on password/role/status changes.
- **Brute-Force Defense**: Sliding-window rate limiting per `(client_ip, username)` plus 5-failure temporary account lockout.
- **Demo Mode Isolation**: `POST /api/auth/demo-switch` and `POST /api/system/seed` are strictly disabled unless `DEMO_MODE=true` and `ENVIRONMENT != production`.

### 2.2 Parameter & Specification Management
- Engineering specifications (**LSL**, **Target**, **USL**) are validated (`LSL < USL`, `LSL <= Target <= USL`) and isolated from statistical control limits (**LCL**, **UCL**).
- Specification revisions increment `current_revision` and enforce optimistic concurrency via `version`.

### 2.3 Statistical Process Control (SPC) Engine
- **I-MR**: $\hat{\sigma}_{\text{within}} = \overline{MR} / d_2$ ($d_2 = 1.12837917$), $UCL_{MR} = 3.26653 \cdot \overline{MR}$, finite filtering, chronological ordering, zero-variance handling.
- **X-bar & R**: Supports constant ($n=2..15$) and variable subgroup sizes with exact per-subgroup limits.
- **Nelson 8 Rules**: Rules 1 through 8 evaluated on chronological series.
- **Process Capability**: Stability assessed prior to capability (`STABLE` vs `UNSTABLE` exploratory mode), Shapiro-Wilk normality check ($3 \le N \le 5000$), and explicit normal-theory PPM/yield assumptions.

### 2.4 Sand Quality & Rejection Correlation Engine
- Time-lag pairing enforces `sand_time <= rejection_time` to prevent future data leakage.
- Computes Pearson $r$ (with Fisher 95% CI), Spearman $\rho$, OOS vs In-Spec scrap ratio, and Benjamini-Hochberg FDR adjusted p-values for multi-factor scans.

### 2.5 Hash-Chained Digital Audit Trail
- Every audit entry computes a canonical SHA-256 `record_hash` linking `sequence_no`, UTC timestamp, actor, action, entity, old/new JSON, reason, outcome, and `prev_hash`.
- `GET /api/audit-logs/verify` recomputes the entire chain to detect post-hoc modification, deletion, or reordering.
- **Threat Model Limitation**: Application-level hash chaining detects tampering in application/database rows, but does not prevent a privileged DB superuser from rewriting the entire chain unless paired with PostgreSQL `REVOKE UPDATE, DELETE ON audit_logs` and off-host WORM shipping.
