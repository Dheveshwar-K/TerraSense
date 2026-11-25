# Deployment, Migrations, Backup & Operations Guide

## 1. Environments & Configuration

TerraSense supports four runtime modes via `ENVIRONMENT`:
- `development`: Local engineering with SQLite or local PostgreSQL.
- `demo`: Demonstration mode (`DEMO_MODE=true`) enabling demo persona switcher and sample seeding.
- `testing`: Automated test execution.
- `production`: Enforces strict security invariants at startup:
  - `SECRET_KEY` must be at least 32 characters and not a known placeholder.
  - `DEMO_MODE` must be `false`.
  - `DATABASE_URL` must point to PostgreSQL (`postgresql://...`), never SQLite, and must not use known placeholder passwords.
  - `ALLOWED_ORIGINS` must not include `*`.

Generate a production secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 2. Local Development Quickstart

### Backend
```powershell
$env:PYTHONPATH = "d:\Projects\Sakthi Hack\backend"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Health endpoints:
- Liveness: `GET http://127.0.0.1:8000/api/health`
- Database Readiness: `GET http://127.0.0.1:8000/api/ready`

### Frontend
```powershell
cd frontend
npm install
npm run dev
```
Vite runs on `http://localhost:5173` and proxies `/api` to `http://127.0.0.1:8000` (override with `VITE_API_PROXY_TARGET`).

---

## 3. Database Migrations

TerraSense runs non-destructive, idempotent schema migrations tracked in `schema_migrations` during startup (`backend/app/core/migrations.py`), and ships standard Alembic configuration (`backend/alembic.ini` and `backend/alembic/versions/`):

```bash
cd backend
alembic upgrade head
```

**Data Safety Policy**: Migrations never run `drop_all()` or reset existing tables. Legacy audit rows are backfilled with SHA-256 chain hashes in place without altering historical payloads.

---

## 4. Docker & Production Deployment

### Production Compose
1. Copy `.env.example` to `.env` and populate strong values for `POSTGRES_USER`, `POSTGRES_PASSWORD`, `SECRET_KEY`, and `ALLOWED_ORIGINS`.
2. Ensure `ENVIRONMENT=production` and `DEMO_MODE=false`.
3. Start services:
   ```bash
   docker compose up --build -d
   docker compose ps
   ```
4. Place a TLS-terminating reverse proxy (Nginx/Caddy/Traefik with HTTPS certificates) in front of port `80` and restrict firewall ingress to HTTPS (`443`) only. PostgreSQL (`5432`) is isolated on the internal `terrasense_net` Docker network and not exposed on host interfaces.

### Demo Compose Override
For evaluation demos only:
```bash
docker compose -f docker-compose.yml -f docker-compose.demo.yml up --build -d
```

---

## 5. Backup & Recovery

### PostgreSQL (Production)
- **Automated Backup**:
  ```bash
  ./scripts/backup_postgres.sh ./backups 30
  ```
  Creates compressed custom-format `pg_dump` archives, verifies archive readability via `pg_restore --list`, generates a `.sha256` checksum, and prunes backups older than 30 days. Schedule daily via `cron`:
  ```cron
  0 2 * * * cd /opt/terrasense && ./scripts/backup_postgres.sh /var/backups/terrasense 30 >> /var/log/terrasense-backup.log 2>&1
  ```
- **Safe Restore** (restores into an explicit target DB after verification and interactive confirmation):
  ```bash
  ./scripts/restore_postgres.sh ./backups/terrasense_foundry_quality_20261125_020000Z.dump foundry_quality_restore
  ```

### SQLite (Local Development)
```bash
python scripts/backup_sqlite.py --source backend/foundry_quality.db --dest-dir backups
```
Uses SQLite's online `.backup()` API and verifies `PRAGMA integrity_check == 'ok'`.
