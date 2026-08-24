"""Unit and integration tests for carvalue_core.security primitives."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from carvalue_core.persistence import (
    AdminSession,
    AdminUser,
    AuditEvent,
    Base,
    make_engine,
    new_session_factory,
)
from carvalue_core.security import (
    create_admin_session,
    generate_csrf_token,
    generate_session_token,
    hash_password,
    hash_token,
    record_audit_event,
    revoke_admin_session,
    validate_admin_session,
    verify_csrf_token,
    verify_password,
)


def test_password_hashing_and_verification() -> None:
    password = "SuperSecretAdminPassword123!"
    pw_hash = hash_password(password)

    assert pw_hash.startswith("pbkdf2:sha256:100000$")
    assert verify_password(password, pw_hash) is True
    assert verify_password("WrongPassword!", pw_hash) is False
    assert verify_password("", pw_hash) is False
    assert verify_password(password, "corrupted_hash") is False


def test_token_generation_and_hashing() -> None:
    tok1 = generate_session_token()
    tok2 = generate_session_token()
    assert tok1 != tok2
    assert len(tok1) >= 32

    csrf1 = generate_csrf_token()
    csrf2 = generate_csrf_token()
    assert csrf1 != csrf2

    h1 = hash_token(tok1)
    assert len(h1) == 64
    assert h1 == hash_token(tok1)


def test_admin_session_lifecycle(tmp_path) -> None:
    db_path = tmp_path / "test_sec.db"
    engine = make_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    SessionLocal = new_session_factory(engine)

    with SessionLocal() as session:
        user = AdminUser(
            email="admin@carvalue.ca",
            password_hash=hash_password("admin_pass"),
            display_name="Operations Admin",
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        # 1. Create session
        admin_sess, raw_token, raw_csrf = create_admin_session(
            session=session,
            user=user,
            duration_hours=12,
            user_agent_coarse="Chrome-Linux",
        )
        session.commit()

        assert admin_sess.id is not None
        assert admin_sess.admin_user_id == user.id
        assert admin_sess.revoked_at is None
        assert admin_sess.user_agent_coarse == "Chrome-Linux"

        # 2. Validate session
        res = validate_admin_session(session, raw_token)
        assert res is not None
        valid_sess, valid_user = res
        assert valid_sess.id == admin_sess.id
        assert valid_user.email == "admin@carvalue.ca"

        # 3. Validate CSRF
        assert verify_csrf_token(admin_sess, raw_csrf) is True
        assert verify_csrf_token(admin_sess, "invalid_csrf_token") is False

        # 4. Revoke session
        revoked = revoke_admin_session(session, raw_token)
        session.commit()
        assert revoked is True

        # 5. Ensure revoked session cannot be validated
        res_after = validate_admin_session(session, raw_token)
        assert res_after is None

    engine.dispose()


def test_expired_session_fails_validation(tmp_path) -> None:
    db_path = tmp_path / "test_sec_exp.db"
    engine = make_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    SessionLocal = new_session_factory(engine)

    with SessionLocal() as session:
        user = AdminUser(
            email="admin_exp@carvalue.ca",
            password_hash=hash_password("admin_pass"),
            is_active=True,
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        admin_sess, raw_token, _ = create_admin_session(session, user, duration_hours=1)
        # Artificially expire the session
        admin_sess.expires_at = datetime.now(UTC) - timedelta(minutes=5)
        session.commit()

        assert validate_admin_session(session, raw_token) is None

    engine.dispose()


def test_inactive_user_fails_validation(tmp_path) -> None:
    db_path = tmp_path / "test_sec_inact.db"
    engine = make_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    SessionLocal = new_session_factory(engine)

    with SessionLocal() as session:
        user = AdminUser(
            email="admin_deact@carvalue.ca",
            password_hash=hash_password("admin_pass"),
            is_active=False,  # Deactivated
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        admin_sess, raw_token, _ = create_admin_session(session, user, duration_hours=1)
        session.commit()

        assert validate_admin_session(session, raw_token) is None

    engine.dispose()


def test_record_audit_event(tmp_path) -> None:
    db_path = tmp_path / "test_sec_audit.db"
    engine = make_engine(f"sqlite:///{db_path}")
    Base.metadata.create_all(engine)
    SessionLocal = new_session_factory(engine)

    with SessionLocal() as session:
        event = record_audit_event(
            session=session,
            actor_type="admin",
            actor_ref="admin@carvalue.ca",
            action="model.promote",
            target_type="model_version",
            target_ref="12",
            outcome="ok",
            details_json={"algorithm": "catboost_candidate", "mae_cad": 1150.0},
        )
        session.commit()

        events = session.execute(select(AuditEvent)).scalars().all()
        assert len(events) == 1
        assert events[0].actor_type == "admin"
        assert events[0].action == "model.promote"
        assert events[0].target_ref == "12"
        assert events[0].details_json == {"algorithm": "catboost_candidate", "mae_cad": 1150.0}

    engine.dispose()
