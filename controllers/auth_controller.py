from flask import Blueprint, request, jsonify, session
from services.auth_helpers import login_user, register_user

auth_controller = Blueprint("auth", __name__)


@auth_controller.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    user, message = login_user(username, password)

    if not user:
        return jsonify({"error": message}), 401

    session["user_id"] = user.id
    session["username"] = user.username
    session["role"] = user.role

    return jsonify({
        "message": message,
        "user_id": user.id,
        "username": user.username,
        "role": user.role
    }), 200


@auth_controller.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({"error": "Username and password are required."}), 400

    user, message = register_user(username, password)

    if not user:
        return jsonify({"error": message}), 409

    return jsonify({
        "message": message,
        "user_id": user.id,
        "username": user.username,
        "role": user.role
    }), 201
