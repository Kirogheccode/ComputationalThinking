# routes/history_routes.py
from flask import Blueprint, request, jsonify
from database import add_history, get_history

history_bp = Blueprint("history", __name__)

@history_bp.route("/add", methods=["POST"])
def api_add_history():
    data = request.json
    user_id = data.get("user_id")
    place = data.get("place_name")

    if not user_id or not place:
        return jsonify({"error": "Missing user_id or place_name"}), 400

    add_history(user_id, place)
    return jsonify({"message": "History saved"}), 200


@history_bp.route("/<user_id>", methods=["GET"])
def api_get_history(user_id):
    rows = get_history(user_id)
    formatted = [
        {"place_name": r[0], "timestamp": r[1]}
        for r in rows
    ]
    return jsonify(formatted), 200
