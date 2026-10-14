from app.extensions import db

class DiseaseInfo(db.Model):
    __tablename__ = "disease_info"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=True)
    precautions = db.Column(db.JSON, nullable=True)
    source = db.Column(db.String(500), nullable=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)