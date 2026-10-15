from app.extensions import db
from app.models import PredictionHistory, User


def register_and_login(client):
    client.post(
        "/auth/register",
        data={
            "username": "api_test_user",
            "email": "api_test@example.com",
            "password": "StrongPass123",
            "confirm_password": "StrongPass123",
            "submit": "Create Account",
        },
        follow_redirects=True,
    )

    client.post(
        "/auth/login",
        data={
            "email": "api_test@example.com",
            "password": "StrongPass123",
            "submit": "Login",
        },
        follow_redirects=True,
    )


def fake_prediction(symptoms):
    return {
        "disease": "Example Disease",
        "confidence": 0.85,
        "is_confident": True,
        "threshold": 0.60,
        "top_3": [
            {
                "rank": 1,
                "disease": "Example Disease",
                "probability": 0.85,
            },
            {
                "rank": 2,
                "disease": "Second Example",
                "probability": 0.10,
            },
            {
                "rank": 3,
                "disease": "Third Example",
                "probability": 0.05,
            },
        ],
    }


def test_api_status(client):
    response = client.get("/api/status")

    assert response.status_code == 200
    assert response.json["status"] == "ok"


def test_prediction_requires_login(client):
    response = client.post(
        "/api/predict",
        json={"symptoms": {"Symptom_1": "itching"}},
    )

    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_prediction_rejects_missing_symptoms(client):
    register_and_login(client)

    response = client.post("/api/predict", json={})

    assert response.status_code == 400
    assert "error" in response.json


def test_prediction_rejects_empty_symptoms(client):
    register_and_login(client)

    response = client.post(
        "/api/predict",
        json={"symptoms": {"Symptom_1": "  "}},
    )

    assert response.status_code == 400


def test_prediction_rejects_unknown_fields(client):
    register_and_login(client)

    response = client.post(
        "/api/predict",
        json={"symptoms": {"Symptom_18": "itching"}},
    )

    assert response.status_code == 400


def test_prediction_rejects_non_string_symptom(client):
    register_and_login(client)

    response = client.post(
        "/api/predict",
        json={"symptoms": {"Symptom_1": 123}},
    )

    assert response.status_code == 400


def test_successful_prediction_is_saved(
    app, client, monkeypatch
):
    register_and_login(client)

    monkeypatch.setattr(
        "app.api.routes.predict_disease",
        fake_prediction,
    )

    response = client.post(
        "/api/predict",
        json={
            "symptoms": {
                "Symptom_1": "itching",
                "Symptom_2": "skin_rash",
            }
        },
    )

    assert response.status_code == 200
    assert response.json["prediction"]["disease"] == (
        "Example Disease"
    )
    assert len(response.json["prediction"]["top_3"]) == 3
    assert response.json["prediction_id"] is not None

    with app.app_context():
        history = db.session.scalar(
            db.select(PredictionHistory)
        )

        assert history is not None
        assert history.predicted_disease == "Example Disease"
        assert history.confidence == 0.85
        assert history.symptoms["Symptom_1"] == "itching"

        user = db.session.scalar(
            db.select(User).where(
                User.email == "api_test@example.com"
            )
        )

        assert history.user_id == user.id


def test_missing_model_returns_service_unavailable(
    client, monkeypatch
):
    register_and_login(client)

    def raise_missing_model(symptoms):
        raise FileNotFoundError("Test model unavailable")

    monkeypatch.setattr(
        "app.api.routes.predict_disease",
        raise_missing_model,
    )

    response = client.post(
        "/api/predict",
        json={"symptoms": {"Symptom_1": "itching"}},
    )

    assert response.status_code == 503
    assert "unavailable" in response.json["error"].lower()



def test_history_requires_login(client):
    response = client.get("/api/history")

    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_history_returns_own_predictions(app, client):
    register_and_login(client)

    with app.app_context():
        user = db.session.scalar(
            db.select(User).where(
                User.email == "api_test@example.com"
            )
        )

        record = PredictionHistory(
            user_id=user.id,
            predicted_disease="Example Disease",
            confidence=0.85,
            top_3_predictions=fake_prediction({})["top_3"],
            symptoms={"Symptom_1": "itching"},
        )

        db.session.add(record)
        db.session.commit()
        expected_id = record.id

    response = client.get("/api/history")

    assert response.status_code == 200
    assert response.json["pagination"]["total"] == 1
    assert len(response.json["items"]) == 1
    assert response.json["items"][0]["id"] == expected_id
    assert (
        response.json["items"][0]["predicted_disease"]
        == "Example Disease"
    )


def test_history_does_not_expose_other_users_predictions(
    app, client
):
    register_and_login(client)

    with app.app_context():
        other_user = User(
            username="other_user",
            email="other@example.com",
        )
        other_user.set_password("StrongPass456")
        db.session.add(other_user)
        db.session.flush()

        db.session.add(
            PredictionHistory(
                user_id=other_user.id,
                predicted_disease="Private Example Disease",
                confidence=0.75,
                top_3_predictions=[],
                symptoms={"Symptom_1": "itching"},
            )
        )
        db.session.commit()

    response = client.get("/api/history")

    assert response.status_code == 200
    assert response.json["pagination"]["total"] == 0
    assert response.json["items"] == []


def test_history_pagination_parameters(client):
    register_and_login(client)

    response = client.get("/api/history?page=0")

    assert response.status_code == 400

    response = client.get("/api/history?per_page=100")

    assert response.status_code == 400


def test_history_returns_empty_list_for_new_user(client):
    register_and_login(client)

    response = client.get("/api/history")

    assert response.status_code == 200
    assert response.json["items"] == []
    assert response.json["pagination"]["total"] == 0
