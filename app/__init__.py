import os
from pathlib import Path
from flask import render_template

from flask import Flask, jsonify

from config import config
from app.extensions import db, migrate, login_manager, csrf



def create_app(config_name=None):
    app = Flask(
        __name__,
        instance_relative_config=True,
        static_folder="statics",
    )

    env_name = config_name or os.getenv(
        "FLASK_CONFIG",
        "development",
    )

    if env_name not in config:
        raise ValueError(
            f"Unknown configuration: {env_name}"
        )

    app.config.from_object(config[env_name])

    Path(app.instance_path).mkdir(
        parents=True,
        exist_ok=True,
    )

    if env_name == "production":
        if (
            not app.config.get("SECRET_KEY")
            or app.config["SECRET_KEY"] == "dev-only-change-me"
        ):
            raise RuntimeError(
                "Set a secure SECRET_KEY in production."
            )

        if not app.config.get("SQLALCHEMY_DATABASE_URI"):
            raise RuntimeError(
                "Set DATABASE_URL in production."
            )

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to continue."
    login_manager.login_message_category = "warning"

    # Import models so SQLAlchemy knows about every table.
    from app.models import (
        User,
        PredictionHistory,
        DiseaseInfo,
        PredictionFeedback,
    )

    # Import and register application blueprints.
    from app.auth import auth_bp
    from app.api import api_bp

    app.register_blueprint(
        auth_bp,
        url_prefix="/auth",
    )

    app.register_blueprint(
        api_bp,
        url_prefix="/api",
    )


    @app.get("/")
    def index():
        return render_template("index.html")
    

    @app.get("/health")
    def health():
        return jsonify({
            "status": "ok",
        })

    return app


@login_manager.user_loader
def load_user(user_id):
    from app.models import User

    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None