from models.models import db, User, Stock, GameState, Portfolio, Order, AuditLog
from services.audit_service import log_audit_action


# GAME STATE MANAGEMENT
def get_current_game_state():
    return GameState.query.first()


def start_game(admin_user_id):
    state = GameState.query.first()
    if not state:
        state = GameState(current_round=1, time_remaining=60, status="ACTIVE")
        db.session.add(state)
    else:
        state.status = "ACTIVE"
    
    db.session.commit()
    log_audit_action(admin_user_id, "GAME_START", "Admin started or resumed the game.")
    return state


def update_game_settings(admin_user_id, current_round=None, time_remaining=None, status=None):
    state = GameState.query.first()
    if not state:
        return None, "Game state not found."

    if current_round is not None:
        state.current_round = current_round
    if time_remaining is not None:
        state.time_remaining = time_remaining
    if status is not None:
        state.status = status

    db.session.commit()
    log_audit_action(
        admin_user_id, 
        "GAME_SETTINGS_UPDATE", 
        f"Updated round: {state.current_round}, time: {state.time_remaining}, status: {state.status}"
    )
    return state, None


def reset_game(admin_user_id, confirmed=False):
    if not confirmed:
        return False, "Confirmation required. Set confirmed to True to reset the game."

    # Clear orders and portfolio records
    Order.query.delete()
    Portfolio.query.delete()

    # Reset user balances to default 1000.00
    traders = User.query.filter_by(role="Trader").all()
    for trader in traders:
        trader.cash_balance = 1000.00

    # Reset Game State
    state = GameState.query.first()
    if state:
        state.current_round = 1
        state.time_remaining = 60
        state.status = "PAUSED"

    db.session.commit()
    log_audit_action(admin_user_id, "GAME_RESET", "Admin performed a full game reset.")
    return True, "Game successfully reset."


# STOCK MANAGEMENT

def update_stock_admin(admin_user_id, stock_id, current_price=None, total_supply=None, available_supply=None):
    stock = db.session.get(Stock, stock_id)
    if not stock:
        return None, "Stock not found."

    if current_price is not None:
        stock.current_price = current_price
    if total_supply is not None:
        stock.total_supply = total_supply
    if available_supply is not None:
        stock.available_supply = available_supply

    db.session.commit()
    log_audit_action(admin_user_id, "STOCK_UPDATE", f"Admin updated stock {stock.ticker} (ID: {stock_id}).")
    return stock, None


def delete_stock_admin(admin_user_id, stock_id):
    stock = db.session.get(Stock, stock_id)
    if not stock:
        return False, "Stock not found."

    ticker = stock.ticker
    # Delete related holdings and orders before removing stock
    Portfolio.query.filter_by(stock_id=stock_id).delete()
    Order.query.filter_by(stock_id=stock_id).delete()
    
    db.session.delete(stock)
    db.session.commit()

    log_audit_action(admin_user_id, "STOCK_DELETE", f"Admin removed stock {ticker} (ID: {stock_id}).")
    return True, f"Stock {ticker} successfully removed."


# USER / PLAYER MANAGEMENT

def update_user_admin(admin_user_id, target_user_id, cash_balance=None, role=None):
    user = db.session.get(User, target_user_id)
    if not user:
        return None, "User not found."

    if cash_balance is not None:
        user.cash_balance = cash_balance
    if role is not None:
        user.role = role

    db.session.commit()
    log_audit_action(
        admin_user_id, 
        "USER_UPDATE", 
        f"Admin updated User #{target_user_id} ({user.username}). Cash: {user.cash_balance}, Role: {user.role}"
    )
    return user, None