from decimal import Decimal
from models.models import db, Stock, Order, Portfolio, User
from services.audit_service import log_audit_action


# =========================
# GET ALL STOCKS
# =========================
def get_all_stocks():
    return Stock.query.all()


# =========================
# GET ONE STOCK
# =========================
def get_stock_by_ticker(ticker):
    return Stock.query.filter_by(ticker=ticker.upper()).first()


# =========================
# STAGE / PLACE ORDER
# =========================
def place_order(user_id, ticker, order_type, quantity):
    """
    Validates user funds/holdings and creates an 'OPEN' order to be 
    executed at the end of the turn.
    """
    if quantity <= 0:
        return False, "Quantity must be greater than zero."

    order_type = order_type.upper()
    if order_type not in ["BUY", "SELL"]:
        return False, "Invalid order type. Must be BUY or SELL."

    stock = get_stock_by_ticker(ticker)
    if not stock:
        return False, "Stock not found."

    user = db.session.get(User, user_id)
    if not user:
        return False, "User not found."

    stock_price = Decimal(str(stock.current_price))
    total_cost = stock_price * Decimal(quantity)

    # --- BUY VALIDATION ---
    if order_type == "BUY":
        # Calculate existing unexecuted BUY order commitments
        open_buy_orders = Order.query.filter_by(user_id=user_id, status="OPEN", order_type="BUY").all()
        committed_cash = sum(Decimal(str(o.price)) * Decimal(o.quantity) for o in open_buy_orders)

        available_cash = Decimal(str(user.cash_balance)) - committed_cash
        if available_cash < total_cost:
            log_audit_action(user_id, "ORDER_REJECTED", f"Insufficient cash to stage BUY {quantity} {ticker}")
            return False, f"Insufficient funds. Required: ${total_cost:.2f}, Available (after open orders): ${available_cash:.2f}"

    # --- SELL VALIDATION ---
    elif order_type == "SELL":
        portfolio_item = Portfolio.query.filter_by(user_id=user_id, stock_id=stock.id).first()
        owned_shares = portfolio_item.quantity if portfolio_item else 0

        # Calculate existing unexecuted SELL order commitments
        open_sell_orders = Order.query.filter_by(user_id=user_id, stock_id=stock.id, status="OPEN", order_type="SELL").all()
        committed_shares = sum(o.quantity for o in open_sell_orders)

        available_shares = owned_shares - committed_shares
        if available_shares < quantity:
            log_audit_action(user_id, "ORDER_REJECTED", f"Insufficient shares to stage SELL {quantity} {ticker}")
            return False, f"Insufficient shares. Owned (uncommitted): {available_shares}, Requested: {quantity}"

    # Stage the order
    new_order = Order(
        user_id=user_id,
        stock_id=stock.id,
        order_type=order_type,
        quantity=quantity,
        price=stock_price,
        status="OPEN"
    )

    db.session.add(new_order)
    db.session.commit()

    log_audit_action(user_id, "PLACE_ORDER", f"Staged {order_type} order #{new_order.id} for {quantity} x {ticker} @ ${stock_price:.2f}")
    return True, f"Order staged successfully. Order ID: {new_order.id}"


# =========================
# CANCEL ORDER
# =========================
def cancel_order(user_id, order_id):
    """
    Cancels an OPEN order before the turn ends.
    """
    order = db.session.get(Order, order_id)

    if not order:
        return False, "Order not found."

    if order.user_id != user_id:
        return False, "Unauthorized to cancel this order."

    if order.status != "OPEN":
        return False, f"Cannot cancel order with status '{order.status}'."

    order.status = "CANCELLED"
    db.session.commit()

    log_audit_action(user_id, "CANCEL_ORDER", f"Cancelled Order #{order_id}")
    return True, f"Order #{order_id} has been cancelled."


# =========================
# PROCESS END-OF-TURN TRADES
# =========================
def process_end_of_turn_orders():
    """
    Batch executes all 'OPEN' market orders atomically at round end.
    """
    open_orders = Order.query.filter_by(status="OPEN").all()
    executed_count = 0
    failed_count = 0

    for order in open_orders:
        user = db.session.get(User, order.user_id)
        stock = db.session.get(Stock, order.stock_id)

        order_cost = Decimal(str(order.price)) * Decimal(order.quantity)

        try:
            if order.order_type == "BUY":
                if Decimal(str(user.cash_balance)) < order_cost:
                    order.status = "CANCELLED"
                    log_audit_action(user.id, "ORDER_FAILED", f"Order #{order.id} failed: Insufficient cash during batch execution.")
                    failed_count += 1
                    continue

                # Deduct cash & update/create portfolio
                user.cash_balance = Decimal(str(user.cash_balance)) - order_cost
                stock.available_supply -= order.quantity

                portfolio = Portfolio.query.filter_by(user_id=user.id, stock_id=stock.id).first()
                if portfolio:
                    # Recalculate average buy price
                    total_old_cost = Decimal(str(portfolio.avg_buy_price)) * Decimal(portfolio.quantity)
                    new_total_quantity = portfolio.quantity + order.quantity
                    portfolio.avg_buy_price = (total_old_cost + order_cost) / Decimal(new_total_quantity)
                    portfolio.quantity = new_total_quantity
                else:
                    portfolio = Portfolio(
                        user_id=user.id,
                        stock_id=stock.id,
                        quantity=order.quantity,
                        avg_buy_price=order.price
                    )
                    db.session.add(portfolio)

            elif order.order_type == "SELL":
                portfolio = Portfolio.query.filter_by(user_id=user.id, stock_id=stock.id).first()

                if not portfolio or portfolio.quantity < order.quantity:
                    order.status = "CANCELLED"
                    log_audit_action(user.id, "ORDER_FAILED", f"Order #{order.id} failed: Insufficient shares during batch execution.")
                    failed_count += 1
                    continue

                # Add cash & adjust portfolio
                user.cash_balance = Decimal(str(user.cash_balance)) + order_cost
                stock.available_supply += order.quantity
                portfolio.quantity -= order.quantity

                if portfolio.quantity == 0:
                    db.session.delete(portfolio)

            order.status = "EXECUTED"
            log_audit_action(user.id, "ORDER_EXECUTED", f"Order #{order.id} executed: {order.order_type} {order.quantity} x {stock.ticker}")
            executed_count += 1

        except Exception as e:
            db.session.rollback()
            order.status = "CANCELLED"
            log_audit_action(user.id, "ORDER_ERROR", f"Order #{order.id} error: {str(e)}")
            failed_count += 1

    db.session.commit()
    return {"executed": executed_count, "failed": failed_count}


# =========================
# GET USER PORTFOLIO
# =========================
def get_user_portfolio(user_id):
    """
    Returns total cash, holding items, average costs, market values, and total profit/loss.
    """
    user = db.session.get(User, user_id)
    if not user:
        return None, "User not found."

    holdings = Portfolio.query.filter_by(user_id=user_id).all()
    portfolio_data = []
    total_stock_value = Decimal("0.00")

    for holding in holdings:
        stock = db.session.get(Stock, holding.stock_id)
        current_price = Decimal(str(stock.current_price))
        avg_price = Decimal(str(holding.avg_buy_price))
        
        current_value = current_price * Decimal(holding.quantity)
        cost_basis = avg_price * Decimal(holding.quantity)
        gain_loss = current_value - cost_basis

        total_stock_value += current_value

        portfolio_data.append({
            "ticker": stock.ticker,
            "company_name": stock.company_name,
            "quantity": holding.quantity,
            "avg_buy_price": float(avg_price),
            "current_price": float(current_price),
            "current_value": float(current_value),
            "gain_loss": float(gain_loss)
        })

    cash = Decimal(str(user.cash_balance))
    total_portfolio_value = cash + total_stock_value

    summary = {
        "cash_balance": float(cash),
        "total_stock_value": float(total_stock_value),
        "total_portfolio_value": float(total_portfolio_value),
        "holdings": portfolio_data
    }

    return summary, "Portfolio retrieved successfully."