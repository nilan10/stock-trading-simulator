from flask import Blueprint, request, jsonify, session, redirect

from services.auth_helpers import (
    login_user,
    register_user
)


auth_controller = Blueprint("auth", __name__)


# ============================================================
# LOGIN
# ============================================================

@auth_controller.route("/login", methods=["POST"])
def login():

    data = request.get_json() or {}

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({
            "error": "Username and password are required."
        }), 400

    user, message = login_user(username, password)

    if not user:
        return jsonify({
            "error": message
        }), 401

    # Remember who is logged in
    session["user_id"] = user.id
    session["username"] = user.username
    session["role"] = user.role

    return jsonify({
        "message": message,
        "user_id": user.id,
        "username": user.username,
        "role": user.role
    }), 200


# ============================================================
# REGISTER
# ============================================================

@auth_controller.route("/register", methods=["POST"])
def register():

    data = request.get_json() or {}

    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return jsonify({
            "error": "Username and password are required."
        }), 400

    user, message = register_user(username, password)

    if not user:
        return jsonify({
            "error": message
        }), 409

    return jsonify({
        "message": message,
        "user_id": user.id,
        "username": user.username,
        "role": user.role
    }), 201


# ============================================================
# LOGOUT
# ============================================================

@auth_controller.route("/logout", methods=["GET"])
def logout():

    # Remove the logged-in user's session
    session.clear()

    # Return to the login page
    return redirect("/app")