import hashlib
import json
import threading
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import User

GENESIS_HASH = "0" * 64
_audit_chain_lock = threading.Lock()


def _normalize_timestamp_iso(ts: Optional[datetime]) -> str:
    if ts is None:
        ts = datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    else:
        ts = ts.astimezone(timezone.utc)
    # Truncate to microseconds consistently across SQLite and PostgreSQL
    return ts.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def compute_audit_hash(
    sequence_no: int,
    timestamp: datetime,
    user_id: Optional[int],
    user_name: str,
    user_role: str,
    action: str,
    entity_type: str,
    entity_id: Optional[str],
    old_value: Optional[str],
    new_value: Optional[str],
    reason: Optional[str],
    outcome: str,
    prev_hash: str,
) -> str:
    """
    Computes deterministic SHA-256 hash over canonical JSON representation
    of an audit record linked to the previous record's hash.
    """
    payload = {
        "sequence_no": sequence_no,
        "timestamp": _normalize_timestamp_iso(timestamp),
        "user_id": user_id,
        "user_name": user_name,
        "user_role": user_role,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "old_value": old_value,
        "new_value": new_value,
        "reason": reason,
        "outcome": outcome,
        "prev_hash": prev_hash,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def append_audit_event(
    db: Session,
    user: Optional[User],
    action: str,
    entity_type: str,
    entity_id: Optional[str] = None,
    old_value: Optional[Any] = None,
    new_value: Optional[Any] = None,
    reason: Optional[str] = None,
    ip_address: Optional[str] = None,
    request_id: Optional[str] = None,
    outcome: str = "SUCCESS",
    commit: bool = False,
) -> AuditLog:
    """
    Appends a hash-chained audit event.
    By default flushes within the caller's transaction so business + audit writes commit atomically.
    Set commit=True for standalone events (e.g., failed login attempts).
    """
    user_id = user.id if user else None
    user_name = user.full_name if user else "System/Anonymous"
    user_role = user.role if user else "system"

    old_str = json.dumps(old_value, sort_keys=True, default=str) if old_value is not None else None
    new_str = json.dumps(new_value, sort_keys=True, default=str) if new_value is not None else None
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    with _audit_chain_lock:
        last_entry = (
            db.query(AuditLog)
            .filter(AuditLog.sequence_no.isnot(None))
            .order_by(AuditLog.sequence_no.desc(), AuditLog.id.desc())
            .first()
        )
        next_seq = (last_entry.sequence_no + 1) if (last_entry and last_entry.sequence_no) else 1
        prev_hash = last_entry.record_hash if (last_entry and last_entry.record_hash) else GENESIS_HASH

        rec_hash = compute_audit_hash(
            sequence_no=next_seq,
            timestamp=now,
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            action=action.upper(),
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            old_value=old_str,
            new_value=new_str,
            reason=reason,
            outcome=outcome.upper(),
            prev_hash=prev_hash,
        )

        audit = AuditLog(
            sequence_no=next_seq,
            timestamp=now,
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            action=action.upper(),
            entity_type=entity_type,
            entity_id=str(entity_id) if entity_id is not None else None,
            old_value=old_str,
            new_value=new_str,
            reason=reason,
            ip_address=ip_address,
            request_id=request_id,
            outcome=outcome.upper(),
            prev_hash=prev_hash,
            record_hash=rec_hash,
        )
        db.add(audit)
        if commit:
            db.commit()
            db.refresh(audit)
        else:
            db.flush()
        return audit


def backfill_audit_chain(db: Session) -> int:
    """
    Safely assigns sequence_no, prev_hash, and record_hash to legacy audit rows
    created prior to hash-chain migration, preserving all original fields.
    """
    with _audit_chain_lock:
        unhashed = (
            db.query(AuditLog)
            .filter(AuditLog.record_hash.is_(None))
            .order_by(AuditLog.id.asc())
            .all()
        )
        if not unhashed:
            return 0

        last_hashed = (
            db.query(AuditLog)
            .filter(AuditLog.record_hash.isnot(None), AuditLog.sequence_no.isnot(None))
            .order_by(AuditLog.sequence_no.desc(), AuditLog.id.desc())
            .first()
        )
        seq = (last_hashed.sequence_no + 1) if (last_hashed and last_hashed.sequence_no) else 1
        prev_hash = last_hashed.record_hash if last_hashed else GENESIS_HASH

        for row in unhashed:
            if not row.outcome:
                row.outcome = "SUCCESS"
            if row.timestamp is None:
                row.timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
            row.sequence_no = seq
            row.prev_hash = prev_hash
            row.record_hash = compute_audit_hash(
                sequence_no=seq,
                timestamp=row.timestamp,
                user_id=row.user_id,
                user_name=row.user_name,
                user_role=row.user_role,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                old_value=row.old_value,
                new_value=row.new_value,
                reason=row.reason,
                outcome=row.outcome,
                prev_hash=prev_hash,
            )
            prev_hash = row.record_hash
            seq += 1

        db.commit()
        return len(unhashed)


def verify_audit_chain(db: Session) -> dict[str, Any]:
    """
    Recomputes the entire hash chain over audit_logs ordered by sequence_no.
    Detects modified fields, broken links, missing hashes, or sequence gaps.
    """
    rows = db.query(AuditLog).order_by(AuditLog.sequence_no.asc(), AuditLog.id.asc()).all()
    total = len(rows)
    if total == 0:
        return {
            "valid": True,
            "total_records": 0,
            "verified_records": 0,
            "broken_links": [],
            "head_hash": None,
            "threat_model_note": (
                "Application-level SHA-256 hash chain detects row edits or deletions after the fact, "
                "but does not defend against an attacker with direct DB superuser write access rewriting the entire chain."
            ),
        }

    broken_links = []
    expected_prev = GENESIS_HASH
    expected_seq = 1
    verified = 0

    for row in rows:
        issues = []
        if row.sequence_no != expected_seq:
            issues.append(f"Expected sequence_no {expected_seq}, got {row.sequence_no}")
        if row.prev_hash != expected_prev:
            issues.append("prev_hash mismatch against predecessor record_hash")
        if not row.record_hash:
            issues.append("Missing record_hash")
        else:
            recomputed = compute_audit_hash(
                sequence_no=row.sequence_no or 0,
                timestamp=row.timestamp,
                user_id=row.user_id,
                user_name=row.user_name,
                user_role=row.user_role,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                old_value=row.old_value,
                new_value=row.new_value,
                reason=row.reason,
                outcome=row.outcome or "SUCCESS",
                prev_hash=row.prev_hash or "",
            )
            if recomputed != row.record_hash:
                issues.append("record_hash mismatch (content modified)")

        if issues:
            broken_links.append({
                "audit_id": row.id,
                "sequence_no": row.sequence_no,
                "issues": issues,
            })
        else:
            verified += 1

        expected_prev = row.record_hash or expected_prev
        expected_seq = (row.sequence_no + 1) if row.sequence_no is not None else (expected_seq + 1)

    return {
        "valid": len(broken_links) == 0,
        "total_records": total,
        "verified_records": verified,
        "broken_links": broken_links,
        "head_hash": rows[-1].record_hash,
        "threat_model_note": (
            "Application-level SHA-256 hash chain detects row modification, deletion, or reordering. "
            "For full defense against privileged DB admins, pair with PostgreSQL REVOKE UPDATE/DELETE on audit_logs and off-host WORM log shipping."
        ),
    }
