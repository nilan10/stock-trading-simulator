from flask import session
from decimal import Decimal

from models.models import (
    db,
    User,
    Stock,
    Portfolio,
    Order,
    GameState,
    AuditLog
)


# =========================
# MARKET FEE
# =========================

def get_market_fee_percent():
    game_state = GameState.query.first()

    if not game_state:
        return Decimal("5.00")

    return Decimal(str(game_state.market_fee_percent))


def calculate_market_fee(trade_value):
    fee_percent = get_market_fee_percent()

    return (
        Decimal(str(trade_value))
        * fee_percent
        / Decimal("100")
    ).quantize(Decimal("0.01"))


# =========================
# BUY MARKET ORDER
# =========================

def buy_stock(ticker, quantity):
    user_id = session.get("user_id")

    if not user_id:
        return False, "You must be logged in."

    user = db.session.get(User, user_id)

    if not user:
        return False, "User not found."

    if not isinstance(quantity, int) or quantity <= 0:
        return False, "Quantity must be a positive whole number."

    stock = Stock.query.filter_by(
        ticker=ticker.upper()
    ).first()

    if not stock:
        return False, "Stock not found."

    if quantity > stock.available_supply:
        return False, "Not enough shares available."

    trade_value = (
        Decimal(str(stock.current_price))
        * quantity
    )

    market_fee = calculate_market_fee(trade_value)

    total_reserved = trade_value + market_fee

    available_cash = (
        Decimal(str(user.cash_balance))
        - Decimal(str(user.reserved_cash))
    )

    if available_cash < total_reserved:
        return False, "Insufficient available funds."

    # Reserve both the purchase and the market fee.
    user.reserved_cash += total_reserved

    order = Order(
        user_id=user.id,
        stock_id=stock.id,
        order_type="BUY",
        order_source="MARKET",
        quantity=quantity,
        price=stock.current_price,
        market_fee=market_fee,
        status="OPEN"
    )

    db.session.add(order)

    db.session.add(
        AuditLog(
            user_id=user.id,
            action="CREATE_MARKET_BUY_ORDER",
            details=(
                f"Market buy order created for "
                f"{quantity} shares of {stock.ticker} "
                f"at ${stock.current_price} "
                f"with ${market_fee} fee reserved."
            )
        )
    )

    db.session.commit()

    return (
        True,
        f"Market buy order placed for {quantity} shares of {stock.ticker}. "
        f"${total_reserved:.2f} reserved until the round ends."
    )


# =========================
# SELL MARKET ORDER
# =========================

def sell_stock(ticker, quantity):
    user_id = session.get("user_id")

    if not user_id:
        return False, "You must be logged in."

    user = db.session.get(User, user_id)

    if not user:
        return False, "User not found."

    if not isinstance(quantity, int) or quantity <= 0:
        return False, "Quantity must be a positive whole number."

    stock = Stock.query.filter_by(
        ticker=ticker.upper()
    ).first()

    if not stock:
        return False, "Stock not found."

    portfolio = Portfolio.query.filter_by(
        user_id=user.id,
        stock_id=stock.id
    ).first()

    if not portfolio:
        return False, "You do not own enough shares."

    available_quantity = (
        portfolio.quantity
        - portfolio.reserved_quantity
    )

    if available_quantity < quantity:
        return False, "You do not have enough unreserved shares."

    trade_value = (
        Decimal(str(stock.current_price))
        * quantity
    )

    market_fee = calculate_market_fee(trade_value)

    # Reserve the shares until the round ends.
    portfolio.reserved_quantity += quantity

    order = Order(
        user_id=user.id,
        stock_id=stock.id,
        order_type="SELL",
        order_source="MARKET",
        quantity=quantity,
        price=stock.current_price,
        market_fee=market_fee,
        status="OPEN"
    )

    db.session.add(order)

    db.session.add(
        AuditLog(
            user_id=user.id,
            action="CREATE_MARKET_SELL_ORDER",
            details=(
                f"Market sell order created for "
                f"{quantity} shares of {stock.ticker} "
                f"at ${stock.current_price} "
                f"with ${market_fee} fee."
            )
        )
    )

    db.session.commit()

    return (
        True,
        f"Market sell order placed for {quantity} shares of {stock.ticker}. "
        f"Shares reserved until the round ends."
    )


# =========================
# GET OPEN MARKET ORDERS
# =========================

def get_open_market_orders():
    return Order.query.filter_by(
        order_source="MARKET",
        status="OPEN"
    ).order_by(
        Order.created_at.asc()
    ).all()


# =========================
# EXECUTE MARKET BUY
# =========================

def execute_market_buy(order):
    user = db.session.get(User, order.user_id)
    stock = db.session.get(Stock, order.stock_id)

    if not user or not stock:
        return False, "User or stock not found."

    trade_value = (
        Decimal(str(order.price))
        * order.quantity
    )

    market_fee = Decimal(str(order.market_fee))

    total_reserved = trade_value + market_fee

    # The shares may no longer be available when the round ends.
    if order.quantity > stock.available_supply:
        return False, "Not enough shares available to execute order."

    portfolio = Portfolio.query.filter_by(
        user_id=user.id,
        stock_id=stock.id
    ).first()

    if portfolio:
        old_quantity = portfolio.quantity
        old_value = (
            Decimal(str(portfolio.avg_buy_price))
            * old_quantity
        )

        new_quantity = old_quantity + order.quantity

        portfolio.quantity = new_quantity
        portfolio.avg_buy_price = (
            old_value + trade_value
        ) / new_quantity

    else:
        portfolio = Portfolio(
            user_id=user.id,
            stock_id=stock.id,
            quantity=order.quantity,
            reserved_quantity=0,
            avg_buy_price=order.price
        )

        db.session.add(portfolio)

    # Consume the money that was reserved when the order was placed.
    user.reserved_cash -= total_reserved
    user.cash_balance -= total_reserved

    stock.available_supply -= order.quantity

    order.status = "EXECUTED"
    order.executed_at = db.func.current_timestamp()

    db.session.add(
        AuditLog(
            user_id=user.id,
            action="EXECUTE_MARKET_BUY",
            details=(
                f"Executed market buy order #{order.id}: "
                f"{order.quantity} shares of {stock.ticker} "
                f"at ${order.price}; "
                f"trade value ${trade_value}; "
                f"market fee ${market_fee}."
            )
        )
    )

    return True, "Market buy executed."


# =========================
# EXECUTE MARKET SELL
# =========================

def execute_market_sell(order):
    user = db.session.get(User, order.user_id)
    stock = db.session.get(Stock, order.stock_id)

    if not user or not stock:
        return False, "User or stock not found."

    portfolio = Portfolio.query.filter_by(
        user_id=user.id,
        stock_id=stock.id
    ).first()

    if not portfolio:
        return False, "Portfolio not found."

    if portfolio.reserved_quantity < order.quantity:
        return False, "Reserved shares are no longer available."

    trade_value = (
        Decimal(str(order.price))
        * order.quantity
    )

    market_fee = Decimal(str(order.market_fee))

    net_proceeds = trade_value - market_fee

    # Consume the reserved shares.
    portfolio.reserved_quantity -= order.quantity
    portfolio.quantity -= order.quantity

    # Seller receives the sale proceeds after the fee.
    user.cash_balance += net_proceeds

    # Shares return to the market supply.
    stock.available_supply += order.quantity

    order.status = "EXECUTED"
    order.executed_at = db.func.current_timestamp()

    if portfolio.quantity == 0:
        db.session.delete(portfolio)

    db.session.add(
        AuditLog(
            user_id=user.id,
            action="EXECUTE_MARKET_SELL",
            details=(
                f"Executed market sell order #{order.id}: "
                f"{order.quantity} shares of {stock.ticker} "
                f"at ${order.price}; "
                f"trade value ${trade_value}; "
                f"market fee ${market_fee}; "
                f"net proceeds ${net_proceeds}."
            )
        )
    )

    return True, "Market sell executed."