from flask import Blueprint, jsonify, request

from services.admin_service import (
    get_current_game_state,
    start_game,
    update_game_settings,
    reset_game,
    get_all_stocks,
    create_stock_admin,
    update_stock_admin,
    delete_stock_admin,
    get_all_users,
    update_user_admin,
    get_all_portfolios,
    get_all_orders,
    get_completed_trades,
    get_all_audit_logs
)


admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ============================================================
# GAME STATE MANAGEMENT
# ============================================================

@admin_bp.route("/game", methods=["GET"])
def current_game_state():
    state, error = get_current_game_state(2)

    if error:
        return jsonify({"error": error}), 403

    return jsonify({
        "current_round": state.current_round,
        "time_remaining": state.time_remaining,
        "status": state.status,
        "starting_capital": float(state.starting_capital)
    }), 200


@admin_bp.route("/game/start", methods=["POST"])
def start_game_controller():
    state, error = start_game(2)

    if error:
        return jsonify({"error": error}), 403

    return jsonify({
        "message": "Game started successfully.",
        "current_round": state.current_round,
        "time_remaining": state.time_remaining,
        "status": state.status,
        "starting_capital": float(state.starting_capital)
    }), 200


@admin_bp.route("/game/settings", methods=["PUT"])
def update_game_settings_controller():
    data = request.get_json() or {}

    state, error = update_game_settings(
        2,
        current_round=data.get("current_round"),
        time_remaining=data.get("time_remaining"),
        status=data.get("status"),
        starting_capital=data.get("starting_capital")
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Game settings updated successfully.",
        "current_round": state.current_round,
        "time_remaining": state.time_remaining,
        "status": state.status,
        "starting_capital": float(state.starting_capital)
    }), 200


@admin_bp.route("/game/reset", methods=["POST"])
def reset_game_controller():
    data = request.get_json() or {}

    confirmed = data.get("confirmed", False)

    success, message = reset_game(2, confirmed)

    if not success:
        return jsonify({"error": message}), 400

    return jsonify({
        "message": message
    }), 200


# ============================================================
# STOCK / MARKET MANAGEMENT
# ============================================================

@admin_bp.route("/stocks", methods=["GET"])
def get_stocks():
    stocks, error = get_all_stocks(2)

    if error:
        return jsonify({"error": error}), 403

    return jsonify([
        {
            "id": stock.id,
            "ticker": stock.ticker,
            "company_name": stock.company_name,
            "current_price": float(stock.current_price),
            "total_supply": stock.total_supply,
            "available_supply": stock.available_supply
        }
        for stock in stocks
    ]), 200


@admin_bp.route("/stocks", methods=["POST"])
def create_stock():
    data = request.get_json() or {}

    stock, error = create_stock_admin(
        2,
        ticker=data.get("ticker"),
        company_name=data.get("company_name"),
        current_price=data.get("current_price"),
        total_supply=data.get("total_supply"),
        available_supply=data.get("available_supply")
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Stock created successfully.",
        "stock": {
            "id": stock.id,
            "ticker": stock.ticker,
            "company_name": stock.company_name,
            "current_price": float(stock.current_price),
            "total_supply": stock.total_supply,
            "available_supply": stock.available_supply
        }
    }), 201


@admin_bp.route("/stocks/<int:stock_id>", methods=["PUT"])
def update_stock(stock_id):
    data = request.get_json() or {}

    stock, error = update_stock_admin(
        2,
        stock_id,
        current_price=data.get("current_price"),
        total_supply=data.get("total_supply"),
        available_supply=data.get("available_supply")
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "Stock updated successfully.",
        "stock": {
            "id": stock.id,
            "ticker": stock.ticker,
            "company_name": stock.company_name,
            "current_price": float(stock.current_price),
            "total_supply": stock.total_supply,
            "available_supply": stock.available_supply
        }
    }), 200


@admin_bp.route("/stocks/<int:stock_id>", methods=["DELETE"])
def delete_stock(stock_id):
    success, message = delete_stock_admin(2, stock_id)

    if not success:
        return jsonify({"error": message}), 400

    return jsonify({
        "message": message
    }), 200


# ============================================================
# USER / PLAYER MANAGEMENT
# ============================================================

@admin_bp.route("/users", methods=["GET"])
def get_users():
    users, error = get_all_users(2)

    if error:
        return jsonify({"error": error}), 403

    return jsonify([
        {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "cash_balance": float(user.cash_balance)
        }
        for user in users
    ]), 200


@admin_bp.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    data = request.get_json() or {}

    user, error = update_user_admin(
        2,
        user_id,
        cash_balance=data.get("cash_balance"),
        role=data.get("role")
    )

    if error:
        return jsonify({"error": error}), 400

    return jsonify({
        "message": "User updated successfully.",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "cash_balance": float(user.cash_balance)
        }
    }), 200


# ============================================================
# PORTFOLIO / PLAYER INFORMATION
# ============================================================

@admin_bp.route("/portfolios", methods=["GET"])
def get_portfolios():
    portfolios, error = get_all_portfolios(2)

    if error:
        return jsonify({"error": error}), 403

    return jsonify([
        {
            "user_id": portfolio.user_id,
            "stock_id": portfolio.stock_id,
            "quantity": portfolio.quantity,
            "avg_buy_price": float(portfolio.avg_buy_price)
        }
        for portfolio in portfolios
    ]), 200


# ============================================================
# ORDER / TRADING ACTIVITY
# ============================================================

@admin_bp.route("/orders", methods=["GET"])
def get_orders():
    orders, error = get_all_orders(2)

    if error:
        return jsonify({"error": error}), 403

    return jsonify([
        {
            "id": order.id,
            "user_id": order.user_id,
            "stock_id": order.stock_id,
            "quantity": order.quantity,
            "price": float(order.price),
            "status": order.status,
            "created_at": order.created_at.isoformat()
            if order.created_at else None
        }
        for order in orders
    ]), 200


@admin_bp.route("/trades", methods=["GET"])
def get_completed_trades_controller():
    trades, error = get_completed_trades(2)

    if error:
        return jsonify({"error": error}), 403

    return jsonify([
        {
            "id": trade.id,
            "user_id": trade.user_id,
            "stock_id": trade.stock_id,
            "quantity": trade.quantity,
            "price": float(trade.price),
            "status": trade.status,
            "created_at": trade.created_at.isoformat()
            if trade.created_at else None
        }
        for trade in trades
    ]), 200


# ============================================================
# AUDIT LOGS
# ============================================================

@admin_bp.route("/audit-logs", methods=["GET"])
def get_audit_logs():
    logs, error = get_all_audit_logs(2)

    if error:
        return jsonify({"error": error}), 403

    return jsonify([
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "details": log.details,
            "timestamp": log.timestamp.isoformat()
            if log.timestamp else None
        }
        for log in logs
    ]), 200