from flask import Blueprint, request, jsonify
from services.admin_service import (
    get_current_game_state,
    start_game,
    update_game_settings,
    reset_game,
    update_stock_admin,
    delete_stock_admin,
    update_user_admin
)

admin_controller = Blueprint("admin", __name__)

# GAME CONTROLS

@admin_controller.route("/admin/game-state", methods=["GET"])
def get_game_state():
    state = get_current_game_state()
    if not state:
        return jsonify({"error": "Game state not initialized."}), 404
    return jsonify({
        "current_round": state.current_round,
        "time_remaining": state.time_remaining,
        "status": state.status
    }), 200


@admin_controller.route("/admin/game/start", methods=["POST"])
def handle_start_game():
    data = request.get_json() or {}
    admin_id = data.get("admin_id", 1)
    state = start_game(admin_id)
    return jsonify({
        "message": "Game started successfully.",
        "status": state.status
    }), 200


@admin_controller.route("/admin/game/settings", methods=["PUT"])
def handle_update_game_settings():
    data = request.get_json() or {}
    admin_id = data.get("admin_id", 1)
    
    state, error = update_game_settings(
        admin_user_id=admin_id,
        current_round=data.get("current_round"),
        time_remaining=data.get("time_remaining"),
        status=data.get("status")
    )
    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Game settings updated.",
        "current_round": state.current_round,
        "time_remaining": state.time_remaining,
        "status": state.status
    }), 200


@admin_controller.route("/admin/game/reset", methods=["POST"])
def handle_reset_game():
    data = request.get_json() or {}
    admin_id = data.get("admin_id", 1)
    confirmed = data.get("confirmed", False)

    success, message = reset_game(admin_id, confirmed)
    if not success:
        return jsonify({"error": message}), 400

    return jsonify({"message": message}), 200


# MARKET / STOCK ALTERATIONS

@admin_controller.route("/admin/stocks/<int:stock_id>", methods=["PUT"])
def handle_update_stock(stock_id):
    data = request.get_json() or {}
    admin_id = data.get("admin_id", 1)

    stock, error = update_stock_admin(
        admin_user_id=admin_id,
        stock_id=stock_id,
        current_price=data.get("current_price"),
        total_supply=data.get("total_supply"),
        available_supply=data.get("available_supply")
    )
    if error:
        return jsonify({"error": error}), 404

    return jsonify({
        "message": f"Stock {stock.ticker} updated.",
        "current_price": float(stock.current_price),
        "total_supply": stock.total_supply,
        "available_supply": stock.available_supply
    }), 200


@admin_controller.route("/admin/stocks/<int:stock_id>", methods=["DELETE"])
def handle_delete_stock(stock_id):
    data = request.get_json() or {}
    admin_id = data.get("admin_id", 1)

    success, message = delete_stock_admin(admin_id, stock_id)
    if not success:
        return jsonify({"error": message}), 404

    return jsonify({"message": message}), 200


# USER ALTERATIONS

@admin_controller.route("/admin/users/<int:user_id>", methods=["PUT"])
def handle_update_user(user_id):
    data = request.get_json() or {}
    admin_id = data.get("admin_id", 1)

    user, error = update_user_admin(
        admin_user_id=admin_id,
        target_user_id=user_id,
        cash_balance=data.get("cash_balance"),
        role=data.get("role")
    )
    if error:
        return jsonify({"error": error}), 404

    return jsonify({
        "message": f"User {user.username} updated.",
        "cash_balance": float(user.cash_balance),
        "role": user.role
    }), 200