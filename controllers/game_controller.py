from flask import Blueprint, jsonify, session

from services.game_service import (
    get_game_state,
    start_game,
    pause_game,
    resume_game,
    end_game,
    end_round
)


game_controller = Blueprint("game", __name__)


def require_admin():
    """Return True if the currently logged-in user is an Admin."""
    return session.get("role") == "Admin"


@game_controller.route("/game", methods=["GET"])
def game_status():
    game_state = get_game_state()

    return jsonify({
        "current_round": game_state.current_round,
        "time_remaining": game_state.time_remaining,
        "status": game_state.status,
        "starting_capital": float(game_state.starting_capital),
        "market_fee_percent": float(game_state.market_fee_percent)
    }), 200


@game_controller.route("/game/start", methods=["POST"])
def start():
    if not require_admin():
        return jsonify({
            "error": "Unauthorized. Only Admins can control the game."
        }), 403

    success, message = start_game()

    if not success:
        return jsonify({"error": message}), 400

    return jsonify({"message": message}), 200


@game_controller.route("/game/pause", methods=["POST"])
def pause():
    if not require_admin():
        return jsonify({
            "error": "Unauthorized. Only Admins can control the game."
        }), 403

    success, message = pause_game()

    if not success:
        return jsonify({"error": message}), 400

    return jsonify({"message": message}), 200


@game_controller.route("/game/resume", methods=["POST"])
def resume():
    if not require_admin():
        return jsonify({
            "error": "Unauthorized. Only Admins can control the game."
        }), 403

    success, message = resume_game()

    if not success:
        return jsonify({"error": message}), 400

    return jsonify({"message": message}), 200


@game_controller.route("/game/end", methods=["POST"])
def end():
    if not require_admin():
        return jsonify({
            "error": "Unauthorized. Only Admins can control the game."
        }), 403

    success, message = end_game()

    if not success:
        return jsonify({"error": message}), 400

    return jsonify({"message": message}), 200


@game_controller.route("/game/round/end", methods=["POST"])
def finish_round():
    if not require_admin():
        return jsonify({
            "error": "Unauthorized. Only Admins can control the game."
        }), 403

    success, message = end_round()

    if not success:
        return jsonify({"error": message}), 400

    return jsonify({"message": message}), 200