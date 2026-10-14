from datetime import datetime, timezone

from app.extensions import db


class PredictionHistory(db.Model):
    __tablename__ = "prediction_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    predicted_disease = db.Column(db.String(120), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    top_3_predictions = db.Column(db.JSON, nullable=True)
    symptoms = db.Column(db.JSON, nullable=False)
    model_version = db.Column(db.String(100), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = db.relationship("User", back_populates="prediction_history")
    feedback_entries = db.relationship(
        "PredictionFeedback",
        back_populates="prediction",
        cascade="all, delete-orphan",
    )