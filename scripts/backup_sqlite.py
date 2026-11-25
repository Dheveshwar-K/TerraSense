"""Safe online SQLite backup and integrity verification utility for local development."""
import argparse
import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def backup_sqlite(source_db: Path, backup_dir: Path) -> Path:
    if not source_db.exists():
        raise FileNotFoundError(f"Source database not found: {source_db}")
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%SZ")
    dest_db = backup_dir / f"{source_db.stem}_{ts}.db"

    src_conn = sqlite3.connect(str(source_db))
    dst_conn = sqlite3.connect(str(dest_db))
    try:
        src_conn.backup(dst_conn)
        check = dst_conn.execute("PRAGMA integrity_check").fetchone()
        if not check or check[0] != "ok":
            raise RuntimeError(f"Backup integrity_check failed: {check}")
    finally:
        dst_conn.close()
        src_conn.close()

    digest = hashlib.sha256(dest_db.read_bytes()).hexdigest()
    (dest_db.with_suffix(".db.sha256")).write_text(f"{digest}  {dest_db.name}\n", encoding="utf-8")
    return dest_db


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create verified SQLite hot backup")
    parser.add_argument("--source", default="backend/foundry_quality.db")
    parser.add_argument("--dest-dir", default="backups")
    args = parser.parse_args()
    out = backup_sqlite(Path(args.source), Path(args.dest_dir))
    print(f"Verified SQLite backup created: {out}")
