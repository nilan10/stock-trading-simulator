from models.models import db, Portfolio, User, Stock, Order, AuditLog

# GET USER PORTFOLIO SUMMARY
# Calculates cash, holdings, total value, and overall gain/loss.
def get_user_portfolio_summary(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return None, "User not found."

    portfolio_entries = Portfolio.query.filter_by(user_id=user_id).all()
    holdings = []
    total_holdings_value = 0.0

    for item in portfolio_entries:
        if item.quantity <= 0:
            continue
        
        stock = db.session.get(Stock, item.stock_id)
        current_price = float(stock.current_price) if stock else 0.0
        avg_price = float(item.avg_buy_price)
        total_value = item.quantity * current_price
        gain_loss = (current_price - avg_price) * item.quantity

        total_holdings_value += total_value
        holdings.append({
            "stock_id": item.stock_id,
            "ticker": stock.ticker if stock else "N/A",
            "company_name": stock.company_name if stock else "N/A",
            "quantity": item.quantity,
            "avg_buy_price": avg_price,
            "current_price": current_price,
            "total_value": round(total_value, 2),
            "unrealized_gain_loss": round(gain_loss, 2)
        })

    cash_balance = float(user.cash_balance)
    total_portfolio_value = cash_balance + total_holdings_value

    summary = {
        "user_id": user.id,
        "username": user.username,
        "cash_balance": cash_balance,
        "total_holdings_value": round(total_holdings_value, 2),
        "total_portfolio_value": round(total_portfolio_value, 2),
        "holdings": holdings
    }

    return summary, None


# GET TRADE & TRANSACTION HISTORY
# Retrieves all buy/sell orders recorded for a specific user.
def get_user_trade_history(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return None, "User not found."

    orders = Order.query.filter_by(user_id=user_id).order_by(Order.created_at.desc()).all()
    history = []

    for order in orders:
        stock = db.session.get(Stock, order.stock_id)
        history.append({
            "order_id": order.id,
            "ticker": stock.ticker if stock else "N/A",
            "order_type": order.order_type,
            "quantity": order.quantity,
            "price": float(order.price),
            "status": order.status,
            "created_at": order.created_at.isoformat()
        })

    return history, None


# GET USER AUDIT LOGS
# Retrieves all logged activity actions for a specific user.
def get_user_audit_logs(user_id):
    user = db.session.get(User, user_id)
    if not user:
        return None, "User not found."

    logs = AuditLog.query.filter_by(user_id=user_id).order_by(AuditLog.timestamp.desc()).all()
    audit_history = []

    for log in logs:
        audit_history.append({
            "id": log.id,
            "action": log.action,
            "details": log.details,
            "timestamp": log.timestamp.isoformat()
        })

    return audit_history, None


# GET LEADERBOARD
# Ranks traders based on total portfolio value (cash + total stock holdings).
def get_leaderboard():
    traders = User.query.filter_by(role="Trader").all()
    leaderboard = []

    for user in traders:
        summary, _ = get_user_portfolio_summary(user.id)
        if summary:
            leaderboard.append({
                "user_id": user.id,
                "username": user.username,
                "cash_balance": summary["cash_balance"],
                "total_portfolio_value": summary["total_portfolio_value"]
            })

    # Sort descending by total portfolio value
    leaderboard.sort(key=lambda x: x["total_portfolio_value"], reverse=True)
    return leaderboard