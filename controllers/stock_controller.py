from flask import Blueprint, jsonify

from services.stock_service import (
    get_all_stocks,
    get_stock_by_ticker
)


stock_controller = Blueprint("stock", __name__)


# =========================
# GET ALL STOCKS
# =========================
# Returns all stocks currently available in the game.
@stock_controller.route("/stocks", methods=["GET"])
def get_stocks():
    stocks = get_all_stocks()

    stock_list = []

    for stock in stocks:
        stock_list.append({
            "id": stock.id,
            "ticker": stock.ticker,
            "company_name": stock.company_name,
            "current_price": float(stock.current_price),
            "total_supply": stock.total_supply,
            "available_supply": stock.available_supply
        })

    return jsonify(stock_list), 200


# =========================
# GET ONE STOCK
# =========================
# Returns information about a specific stock using its ticker.
@stock_controller.route("/stocks/<ticker>", methods=["GET"])
def get_stock(ticker):
    stock = get_stock_by_ticker(ticker)

    if not stock:
        return jsonify({
            "error": "Stock not found."
        }), 404

    return jsonify({
        "id": stock.id,
        "ticker": stock.ticker,
        "company_name": stock.company_name,
        "current_price": float(stock.current_price),
        "total_supply": stock.total_supply,
        "available_supply": stock.available_supply
    }), 200
