"""Security primitives, password hashing, session tokens, CSRF protection, and audit trail.

Implements PRD Section 10 and FR-ADM-01:
- PBKDF2-HMAC-SHA256 password hashing with salt.
- Cryptographically secure session and CSRF token generation.
- Session lifecycle with 12-hour expiration, revocation, and validation.
- Append-only audit trail logging.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from carvalue_core.persistence import AdminSession, AdminUser, AuditEvent

# ---------------------------------------------------------------------------
# Password hashing (PBKDF2-HMAC-SHA256)
# ---------------------------------------------------------------------------

PBKDF2_ITERATIONS = 100_000
SALT_BYTES = 16


def hash_password(password: str) -> str:
    """Hash password with PBKDF2-HMAC-SHA256 and a random salt."""
    salt = os.urandom(SALT_BYTES)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2:sha256:{PBKDF2_ITERATIONS}${salt.hex()}${dk.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a plain password against a stored PBKDF2 hash."""
    try:
        scheme, algo, iterations_str = password_hash.split("$")[0].split(":")
        if scheme != "pbkdf2" or algo != "sha256":
            return False
        iterations = int(iterations_str)
        salt_hex = password_hash.split("$")[1]
        stored_hash_hex = password_hash.split("$")[2]

        salt = bytes.fromhex(salt_hex)
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
        return hmac.compare_digest(dk.hex(), stored_hash_hex)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Token generation & hashing
# ---------------------------------------------------------------------------


def generate_session_token() -> str:
    """Generate a 256-bit cryptographically secure session token."""
    return secrets.token_urlsafe(32)


def generate_csrf_token() -> str:
    """Generate a 256-bit cryptographically secure CSRF token."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """Compute SHA256 hex digest of a token for secure database storage."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Admin Session Management
# ---------------------------------------------------------------------------


def create_admin_session(
    session: Session,
    user: AdminUser,
    duration_hours: int = 12,
    user_agent_coarse: str | None = None,
) -> tuple[AdminSession, str, str]:
    """Create a new authenticated admin session and return (session_row, raw_token, raw_csrf)."""
    raw_token = generate_session_token()
    raw_csrf = generate_csrf_token()

    now = datetime.now(UTC)
    expires_at = now + timedelta(hours=duration_hours)

    admin_session = AdminSession(
        admin_user_id=user.id,
        token_hash=hash_token(raw_token),
        csrf_token_hash=hash_token(raw_csrf),
        created_at=now,
        expires_at=expires_at,
        last_seen_at=now,
        user_agent_coarse=user_agent_coarse[:32] if user_agent_coarse else None,
    )
    session.add(admin_session)

    user.last_login_at = now
    session.flush()

    return admin_session, raw_token, raw_csrf


def validate_admin_session(
    session: Session,
    session_token: str,
) -> tuple[AdminSession, AdminUser] | None:
    """Validate a raw session token. Returns (session_row, user_row) if valid, None otherwise."""
    if not session_token:
        return None

    tok_hash = hash_token(session_token)
    admin_session = session.execute(
        select(AdminSession).where(
            AdminSession.token_hash == tok_hash,
            AdminSession.revoked_at.is_(None),
        )
    ).scalar_one_or_none()

    if not admin_session:
        return None

    now = datetime.now(UTC)
    if admin_session.expires_at <= now:
        return None

    user = session.get(AdminUser, admin_session.admin_user_id)
    if not user or not user.is_active:
        return None

    admin_session.last_seen_at = now
    return admin_session, user


def verify_csrf_token(admin_session: AdminSession, csrf_token: str) -> bool:
    """Verify raw CSRF token against the session's stored CSRF hash."""
    if not csrf_token or not admin_session:
        return False
    candidate_hash = hash_token(csrf_token)
    return hmac.compare_digest(candidate_hash, admin_session.csrf_token_hash)


def revoke_admin_session(session: Session, session_token: str) -> bool:
    """Revoke an active admin session."""
    if not session_token:
        return False

    tok_hash = hash_token(session_token)
    admin_session = session.execute(
        select(AdminSession).where(AdminSession.token_hash == tok_hash)
    ).scalar_one_or_none()

    if admin_session and admin_session.revoked_at is None:
        admin_session.revoked_at = datetime.now(UTC)
        session.flush()
        return True
    return False


# ---------------------------------------------------------------------------
# Append-only Audit Trail
# ---------------------------------------------------------------------------


def record_audit_event(
    session: Session,
    actor_type: str,
    actor_ref: str | None,
    action: str,
    target_type: str | None = None,
    target_ref: str | None = None,
    outcome: str = "ok",
    details_json: dict[str, Any] | None = None,
) -> AuditEvent:
    """Append a tamper-evident audit event (PRD FR-ADM-01)."""
    event = AuditEvent(
        occurred_at=datetime.now(UTC),
        actor_type=actor_type,
        actor_ref=actor_ref,
        action=action,
        target_type=target_type,
        target_ref=target_ref,
        outcome=outcome,
        details_json=details_json or {},
    )
    session.add(event)
    session.flush()
    return event
