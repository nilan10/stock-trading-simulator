from flask import Blueprint, request, jsonify

from services.market_order_service import buy_stock, sell_stock


order_controller = Blueprint("order", __name__)


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
        return jsonify({
            "error": message
        }), 400

    return jsonify({
        "message": message
    }), 200


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
        return jsonify({
            "error": message
        }), 400

    return jsonify({
        "message": message
    }), 200
