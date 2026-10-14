from datetime import datetime, timezone

from app.extensions import db

class PredictionFeedback(db.Model):
    __tablename__ = "prediction_feedback"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    prediction_id = db.Column(
        db.Integer,
        db.ForeignKey("prediction_history.id"),
        nullable=False,
        index=True,
    )
    rating = db.Column(db.Integer, nullable=True)
    comments = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = db.relationship("User", back_populates="feedback_entries")
    prediction = db.relationship(
        "PredictionHistory",
        back_populates="feedback_entries",
    )