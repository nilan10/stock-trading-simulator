from flask import Blueprint, request, jsonify
from services.market_order_service import buy_stock, sell_stock
from services.user_order_service import (
    create_user_order,
    get_open_orders,
    update_user_order,
    cancel_user_order,
    accept_user_order
)

order_controller = Blueprint("order", __name__)


# =========================
# MARKET ORDERS
# =========================

@order_controller.route("/buy", methods=["POST"])
def buy():
    data = request.get_json()
    ticker = data.get("ticker")
    quantity = data.get("quantity")

    if not ticker or quantity is None:
        return jsonify({
            "error": "Ticker and quantity are required."
        }), 400

    success, message = buy_stock(ticker, quantity)

    if not success:
        return jsonify({"error": message}), 400

    return jsonify({"message": message}), 200


@order_controller.route("/sell", methods=["POST"])
def sell():
    data = request.get_json()
    ticker = data.get("ticker")
    quantity = data.get("quantity")

    if not ticker or quantity is None:
        return jsonify({
            "error": "Ticker and quantity are required."
        }), 400

    success, message = sell_stock(ticker, quantity)

    if not success:
        return jsonify({"error": message}), 400

    return jsonify({"message": message}), 200


# =========================
# USER-TO-USER ORDERS
# =========================

@order_controller.route("/orders", methods=["POST"])
def create_order():
    data = request.get_json()

    ticker = data.get("ticker")
    order_type = data.get("order_type")
    quantity = data.get("quantity")
    price = data.get("price")

    if not ticker or not order_type or quantity is None or price is None:
        return jsonify({
            "error": "Ticker, order type, quantity, and price are required."
        }), 400

    success, message, order = create_user_order(
        ticker,
        order_type,
        quantity,
        price
    )

    if not success:
        return jsonify({"error": message}), 400

    return jsonify({
        "message": message,
        "order_id": order.id,
        "ticker": ticker.upper(),
        "order_type": order.order_type,
        "quantity": order.quantity,
        "price": float(order.price),
        "status": order.status
    }), 201


@order_controller.route("/orders", methods=["GET"])
def get_orders():
    orders = get_open_orders()

    return jsonify(orders), 200


@order_controller.route("/orders/<int:order_id>", methods=["PUT"])
def update_order(order_id):
    data = request.get_json()

    quantity = data.get("quantity")
    price = data.get("price")

    if quantity is None or price is None:
        return jsonify({
            "error": "Quantity and price are required."
        }), 400

    success, message = update_user_order(
        order_id,
        quantity,
        price
    )

    if not success:
        return jsonify({"error": message}), 400

    return jsonify({
        "message": message
    }), 200


@order_controller.route("/orders/<int:order_id>", methods=["DELETE"])
def cancel_order(order_id):
    success, message = cancel_user_order(order_id)

    if not success:
        return jsonify({"error": message}), 400

    return jsonify({
        "message": message
    }), 200


@order_controller.route("/orders/<int:order_id>/accept", methods=["POST"])
def accept_order(order_id):
    success, message = accept_user_order(order_id)

    if not success:
        return jsonify({"error": message}), 400

    return jsonify({
        "message": message
    }), 200
