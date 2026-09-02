from flask import Blueprint, render_template


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
