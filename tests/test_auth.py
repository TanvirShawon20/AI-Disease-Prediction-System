from app import create_app
from app.extensions import db
from app.models import User

def register(client, username="test_user", email="test@example.com",
             password="StrongPass123"):
    return client.post(
        "/auth/register",
        data={
            "username": username,
            "email": email,
            "password": password,
            "confirm_password": password,
            "submit": "Create Account",
        },
        follow_redirects=True,
    )


def login(client, email="test@example.com",
          password="StrongPass123"):
    return client.post(
        "/auth/login",
        data={
            "email": email,
            "password": password,
            "submit": "Login",
        },
        follow_redirects=True,
    )


def test_registration_creates_hashed_password(app, client):
    response = register(client)

    assert response.status_code == 200

    with app.app_context():
        user = db.session.scalar(
            db.select(User).where(User.email == "test@example.com")
        )

        assert user is not None
        assert user.password_hash != "StrongPass123"
        assert user.check_password("StrongPass123")


def test_duplicate_email_is_rejected(app, client):
    register(client)
    response = register(
        client,
        username="another_user",
        email="test@example.com",
    )

    assert b"already registered" in response.data

    with app.app_context():
        users = db.session.scalars(db.select(User)).all()
        assert len(users) == 1


def test_login_and_dashboard(client):
    register(client)
    response = login(client)

    assert response.status_code == 200
    assert b"Welcome, test_user!" in response.data


def test_invalid_password_is_rejected(client):
    register(client)
    response = login(client, password="WrongPassword123")

    assert b"Invalid email or password." in response.data
    assert b"Welcome, test_user!" not in response.data


def test_dashboard_requires_login(client):
    response = client.get("/auth/dashboard")

    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_logout_ends_session(client):
    register(client)
    login(client)

    response = client.post(
        "/auth/logout",
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"You have been logged out." in response.data

    dashboard_response = client.get("/auth/dashboard")
    assert dashboard_response.status_code == 302
    assert "/auth/login" in dashboard_response.headers["Location"]
