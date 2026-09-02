from flask import Blueprint, jsonify, session

from services.portfolio_service import (
    get_user_portfolio_summary,
    get_user_trade_history,
    get_user_audit_logs,
    get_leaderboard
)


portfolio_controller = Blueprint("portfolio", __name__)


@portfolio_controller.route("/portfolio", methods=["GET"])
def get_portfolio():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"error": "You must be logged in."}), 401

    summary, error = get_user_portfolio_summary(user_id)

    if error:
        return jsonify({"error": error}), 404

    return jsonify(summary), 200


@portfolio_controller.route("/portfolio/history", methods=["GET"])
def get_trade_history():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"error": "You must be logged in."}), 401

    history, error = get_user_trade_history(user_id)

    if error:
        return jsonify({"error": error}), 404

    return jsonify(history), 200


@portfolio_controller.route("/portfolio/audit", methods=["GET"])
def get_audit_logs():
    user_id = session.get("user_id")

    if not user_id:
        return jsonify({"error": "You must be logged in."}), 401

    logs, error = get_user_audit_logs(user_id)

    if error:
        return jsonify({"error": error}), 404

    return jsonify(logs), 200


@portfolio_controller.route("/leaderboard", methods=["GET"])
def fetch_leaderboard():
    rankings = get_leaderboard()

    return jsonify(rankings), 200
