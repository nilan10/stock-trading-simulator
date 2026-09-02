from flask import session

from models.models import db, User, Stock, Portfolio


def buy_stock(ticker, quantity):
    user_id = session.get("user_id")

    if not user_id:
        return False, "You must be logged in."

    user = db.session.get(User, user_id)

    if not user:
        return False, "User not found."

    if not isinstance(quantity, int) or quantity <= 0:
        return False, "Quantity must be a positive whole number."

    stock = Stock.query.filter_by(ticker=ticker.upper()).first()

    if not stock:
        return False, "Stock not found."

    if quantity > stock.available_supply:
        return False, "Not enough shares available."

    total_cost = stock.current_price * quantity

    if user.cash_balance < total_cost:
        return False, "Insufficient funds."

    portfolio = Portfolio.query.filter_by(
        user_id=user.id,
        stock_id=stock.id
    ).first()

    if portfolio:
        old_quantity = portfolio.quantity
        old_value = portfolio.avg_buy_price * old_quantity

        portfolio.quantity += quantity
        portfolio.avg_buy_price = (
            old_value + total_cost
        ) / portfolio.quantity

    else:
        portfolio = Portfolio(
            user_id=user.id,
            stock_id=stock.id,
            quantity=quantity,
            avg_buy_price=stock.current_price
        )
        db.session.add(portfolio)

    user.cash_balance -= total_cost
    stock.available_supply -= quantity

    db.session.commit()

    return True, f"Bought {quantity} shares of {stock.ticker}."


def sell_stock(ticker, quantity):
    user_id = session.get("user_id")

    if not user_id:
        return False, "You must be logged in."

    user = db.session.get(User, user_id)

    if not user:
        return False, "User not found."

    if not isinstance(quantity, int) or quantity <= 0:
        return False, "Quantity must be a positive whole number."

    stock = Stock.query.filter_by(ticker=ticker.upper()).first()

    if not stock:
        return False, "Stock not found."

    portfolio = Portfolio.query.filter_by(
        user_id=user.id,
        stock_id=stock.id
    ).first()

    if not portfolio or portfolio.quantity < quantity:
        return False, "You do not own enough shares."

    total_value = stock.current_price * quantity

    user.cash_balance += total_value
    stock.available_supply += quantity
    portfolio.quantity -= quantity

    if portfolio.quantity == 0:
        db.session.delete(portfolio)

    db.session.commit()

    return True, f"Sold {quantity} shares of {stock.ticker}."
