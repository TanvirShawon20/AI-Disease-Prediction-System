from flask import jsonify

from app.api import api_bp


@api_bp.get("/status")
def api_status():
    return jsonify({
        "message": "API blueprint is registered.",
        "status": "ok",
    })