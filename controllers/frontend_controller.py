from flask import Blueprint, render_template, session,jsonify


frontend_controller = Blueprint("frontend", __name__)


# =========================
# FRONTEND HOME
# =========================
@frontend_controller.route("/app")
def frontend():
    return render_template("index.html")

@frontend_controller.route("/market")
def market():
    return render_template("market.html")

@frontend_controller.route("/me")
def me():
    return jsonify({
        "user_id": session.get("user_id"),
        "username": session.get("username"),
        "role": session.get("role")
    })
