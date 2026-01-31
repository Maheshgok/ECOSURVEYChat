from datetime import datetime, timedelta
from app.core.database import SessionLocal
from app.models import User, Session as UserSession, Corpus
from app.services.auth_service import AuthService

session = SessionLocal()
try:
    google_id = "test_google_sub"
    user = session.query(User).filter(User.google_id == google_id).first()
    if not user:
        user = User(
            google_id=google_id,
            email="test_user@example.com",
            name=None,
            picture=None,
            email_verified=False,
            first_login=datetime.utcnow(),
            last_login=datetime.utcnow(),
        )
        session.add(user)
        session.commit()
        session.refresh(user)

    corpus = session.query(Corpus).first()
    if not corpus:
        corpus = Corpus(name="Test Corpus", description="Local test corpus")
        session.add(corpus)
        session.commit()
        session.refresh(corpus)

    auth = AuthService()
    token_payload = auth.create_session_token(google_id=user.google_id, email=user.email)

    existing = session.query(UserSession).filter(UserSession.token == token_payload["access_token"]).first()
    if not existing:
        user_session = UserSession(
            user_id=user.id,
            token=token_payload["access_token"],
            ip_address="127.0.0.1",
            user_agent="local-test",
            expires_at=datetime.utcnow() + timedelta(hours=24),
            is_active=True,
        )
        session.add(user_session)
        session.commit()

    print("TOKEN=", token_payload["access_token"])
    print("CORPUS_ID=", corpus.id)
finally:
    session.close()
