from flask import jsonify, request
from flask_login import current_user, login_required
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select

from app.api import api_bp
from app.extensions import db
from app.ml.predictor import predict_disease
from app.models import PredictionHistory


@api_bp.get("/status")
def api_status():
    return jsonify({
        "message": "API blueprint is registered.",
        "status": "ok",
    }), 200


@api_bp.post("/predict")
@login_required
def predict():
    if not request.is_json:
        return jsonify({
            "error": "Content-Type must be application/json."
        }), 415

    data = request.get_json(silent=True)

    if not isinstance(data, dict):
        return jsonify({
            "error": "Request body must be a JSON object."
        }), 400

    symptoms = data.get("symptoms")

    if not isinstance(symptoms, dict):
        return jsonify({
            "error": "Provide symptoms as a JSON object."
        }), 400

    allowed_fields = {
        f"Symptom_{i}" for i in range(1, 18)
    }

    unknown_fields = set(symptoms) - allowed_fields

    if unknown_fields:
        return jsonify({
            "error": "Unknown symptom field(s).",
            "fields": sorted(unknown_fields),
        }), 400

    cleaned_symptoms = {}

    for field, value in symptoms.items():
        if value is None:
            continue

        if not isinstance(value, str):
            return jsonify({
                "error": f"{field} must be a string or null."
            }), 400

        value = value.strip()

        if value:
            if len(value) > 100:
                return jsonify({
                    "error": f"{field} is too long."
                }), 400

            cleaned_symptoms[field] = value

    if not cleaned_symptoms:
        return jsonify({
            "error": "Provide at least one non-empty symptom."
        }), 400

    try:
        result = predict_disease(cleaned_symptoms)
    except FileNotFoundError:
        return jsonify({
            "error": "The prediction model is unavailable."
        }), 503
    except Exception:
        return jsonify({
            "error": "Prediction failed. Please try again."
        }), 500

    try:
        history = PredictionHistory(
            user_id=current_user.id,
            predicted_disease=result["disease"],
            confidence=result["confidence"],
            top_3_predictions=result["top_3"],
            symptoms=cleaned_symptoms,
            model_version=None,
        )

        db.session.add(history)
        db.session.commit()

    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({
            "error": "Prediction completed, but saving history failed."
        }), 500

    return jsonify({
        "message": "Prediction completed successfully.",
        "prediction_id": history.id,
        "prediction": result,
        "disclaimer": (
            "Educational decision support only; "
            "this result is not a medical diagnosis."
        ),
    }), 200



@api_bp.get("/history")
@login_required
def prediction_history():
    try:
        page = request.args.get("page", default=1, type=int)
        per_page = request.args.get("per_page", default=10, type=int)

        if page is None or per_page is None or page < 1:
            return jsonify({
                "error": "page must be a positive integer."
            }), 400

        if per_page < 1 or per_page > 50:
            return jsonify({
                "error": "per_page must be between 1 and 50."
            }), 400

        query = select(PredictionHistory).where(
            PredictionHistory.user_id == current_user.id
        )

        total = db.session.scalar(
            select(db.func.count()).select_from(query.subquery())
        )

        records = db.session.scalars(
            query.order_by(
                PredictionHistory.created_at.desc(),
                PredictionHistory.id.desc(),
            )
            .offset((page - 1) * per_page)
            .limit(per_page)
        ).all()

        return jsonify({
            "items": [
                {
                    "id": record.id,
                    "predicted_disease": record.predicted_disease,
                    "confidence": record.confidence,
                    "top_3_predictions": record.top_3_predictions,
                    "symptoms": record.symptoms,
                    "created_at": (
                        record.created_at.isoformat()
                        if record.created_at else None
                    ),
                }
                for record in records
            ],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "pages": (total + per_page - 1) // per_page,
            },
        }), 200

    except SQLAlchemyError:
        db.session.rollback()
        return jsonify({
            "error": "Unable to retrieve prediction history."
        }), 500
