from models.models import (
    db,
    User,
    Stock,
    GameState,
    Portfolio,
    Order,
    AuditLog
)

from services.audit_service import log_audit_action
from database.seed import reset_database


# ============================================================
# ADMIN AUTHORIZATION
# ============================================================

def _get_admin(admin_user_id):
    """Return the user if they are an Admin, otherwise None."""
    admin = db.session.get(User, admin_user_id)

    if not admin or admin.role != "Admin":
        return None

    return admin


# ============================================================
# GAME STATE MANAGEMENT
# ============================================================

def get_current_game_state(admin_user_id):
    admin = _get_admin(admin_user_id)

    if not admin:
        return None, "Unauthorized. Only Admins can view game state."

    state = GameState.query.first()

    if not state:
        return None, "Game state not initialized."

    return state, None


def start_game(admin_user_id):
    admin = _get_admin(admin_user_id)

    if not admin:
        return None, "Unauthorized. Only Admins can start the game."

    state = GameState.query.first()

    if not state:
        state = GameState(
            current_round=1,
            time_remaining=60,
            status="ACTIVE"
        )

        db.session.add(state)

    else:
        state.status = "ACTIVE"

    db.session.commit()

    log_audit_action(
        admin.id,
        "GAME_START",
        "Admin started or resumed the game."
    )

    return state, None


def update_game_settings(
    admin_user_id,
    current_round=None,
    time_remaining=None,
    status=None,
    starting_capital=None
):
    admin = _get_admin(admin_user_id)

    if not admin:
        return None, "Unauthorized. Only Admins can change game settings."

    state = GameState.query.first()

    if not state:
        return None, "Game state not found."

    if current_round is not None:
        if current_round < 1:
            return None, "Current round must be at least 1."

        state.current_round = current_round

    if time_remaining is not None:
        if time_remaining < 0:
            return None, "Time remaining cannot be negative."

        state.time_remaining = time_remaining

    if status is not None:
        if status not in ["ACTIVE", "PAUSED", "ENDED"]:
            return None, "Invalid game status."

        state.status = status

    if starting_capital is not None:
        if starting_capital < 0:
            return None, "Starting capital cannot be negative."

        state.starting_capital = starting_capital

    db.session.commit()

    log_audit_action(
        admin.id,
        "GAME_SETTINGS_UPDATE",
        f"Updated round: {state.current_round}, "
        f"time: {state.time_remaining}, "
        f"status: {state.status}, "
        f"starting capital: {state.starting_capital}"
    )

    return state, None


# ============================================================
# SOFT RESET
# ============================================================

def reset_game(admin_user_id, confirmed=False):
    """
    Soft reset.

    Resets gameplay state while preserving the current
    stock market and its configuration.
    """

    admin = _get_admin(admin_user_id)

    if not admin:
        return False, "Unauthorized. Only Admins can reset the game."

    if not confirmed:
        return False, (
            "Confirmation required. "
            "Set confirmed to True to reset the game."
        )

    state = GameState.query.first()

    if not state:
        state = GameState(
            current_round=1,
            time_remaining=60,
            status="PAUSED",
            starting_capital=150000.00
        )

        db.session.add(state)

    # --------------------------------------------------------
    # CLEAR ORDERS AND PORTFOLIOS
    # --------------------------------------------------------

    Order.query.delete()
    Portfolio.query.delete()

    # --------------------------------------------------------
    # RESET USER BALANCES
    # --------------------------------------------------------

    users = User.query.all()

    for user in users:
        user.cash_balance = state.starting_capital
        user.reserved_cash = 0.00

    # --------------------------------------------------------
    # RESET GAME STATE
    # --------------------------------------------------------

    state.current_round = 1
    state.time_remaining = 60
    state.status = "PAUSED"

    db.session.commit()

    log_audit_action(
        admin.id,
        "GAME_RESET",
        f"Admin performed a soft game reset. "
        f"Starting capital: {state.starting_capital}. "
        f"Current market configuration was preserved."
    )

    return True, "Game successfully reset."


# ============================================================
# HARD RESET
# ============================================================

def hard_reset_game(admin_user_id, confirmed=False):
    """
    Hard reset.

    Completely restores the simulator to the canonical
    state defined in seed.py.
    """

    admin = _get_admin(admin_user_id)

    if not admin:
        return False, (
            "Unauthorized. Only Admins can perform a hard reset."
        )

    if not confirmed:
        return False, (
            "Confirmation required. "
            "Set confirmed to True to perform a hard reset."
        )

    try:
        reset_database()

        return True, (
            "Hard reset successful. "
            "The canonical users, stocks, game settings, "
            "and market state have been restored."
        )

    except Exception as error:
        db.session.rollback()

        return False, f"Hard reset failed: {error}"


# ============================================================
# STOCK / MARKET MANAGEMENT
# ============================================================

def get_all_stocks(admin_user_id):
    admin = _get_admin(admin_user_id)

    if not admin:
        return None, "Unauthorized. Only Admins can view market data."

    stocks = Stock.query.order_by(Stock.ticker).all()

    return stocks, None


def create_stock_admin(
    admin_user_id,
    ticker,
    company_name,
    current_price,
    total_supply,
    available_supply=None
):
    admin = _get_admin(admin_user_id)

    if not admin:
        return None, "Unauthorized. Only Admins can create stocks."

    if not ticker:
        return None, "Ticker is required."

    if not company_name:
        return None, "Company name is required."

    if current_price < 0:
        return None, "Stock price cannot be negative."

    if total_supply < 0:
        return None, "Total supply cannot be negative."

    ticker = ticker.upper().strip()

    existing_stock = Stock.query.filter_by(ticker=ticker).first()

    if existing_stock:
        return None, "A stock with this ticker already exists."

    if available_supply is None:
        available_supply = total_supply

    if available_supply < 0:
        return None, "Available supply cannot be negative."

    if available_supply > total_supply:
        return None, "Available supply cannot exceed total supply."

    stock = Stock(
        ticker=ticker,
        company_name=company_name,
        current_price=current_price,
        total_supply=total_supply,
        available_supply=available_supply
    )

    db.session.add(stock)
    db.session.commit()

    log_audit_action(
        admin.id,
        "STOCK_CREATE",
        f"Admin created stock {stock.ticker} "
        f"(ID: {stock.id}), "
        f"Price: {stock.current_price}, "
        f"Supply: {stock.total_supply}, "
        f"Available: {stock.available_supply}"
    )

    return stock, None


def update_stock_admin(
    admin_user_id,
    stock_id,
    current_price=None,
    total_supply=None,
    available_supply=None
):
    admin = _get_admin(admin_user_id)

    if not admin:
        return None, "Unauthorized. Only Admins can modify stocks."

    stock = db.session.get(Stock, stock_id)

    if not stock:
        return None, "Stock not found."

    if current_price is not None:
        if current_price < 0:
            return None, "Stock price cannot be negative."

        stock.current_price = current_price

    if total_supply is not None:
        if total_supply < 0:
            return None, "Total supply cannot be negative."

        stock.total_supply = total_supply

        if stock.available_supply > total_supply:
            return None, (
                "Total supply cannot be lower than "
                "the current available supply."
            )

    if available_supply is not None:
        if available_supply < 0:
            return None, "Available supply cannot be negative."

        if available_supply > stock.total_supply:
            return None, "Available supply cannot exceed total supply."

        stock.available_supply = available_supply

    db.session.commit()

    log_audit_action(
        admin.id,
        "STOCK_UPDATE",
        f"Admin updated stock {stock.ticker} (ID: {stock_id})."
    )

    return stock, None


def delete_stock_admin(admin_user_id, stock_id):
    admin = _get_admin(admin_user_id)

    if not admin:
        return False, "Unauthorized. Only Admins can delete stocks."

    stock = db.session.get(Stock, stock_id)

    if not stock:
        return False, "Stock not found."

    ticker = stock.ticker

    Portfolio.query.filter_by(stock_id=stock_id).delete()
    Order.query.filter_by(stock_id=stock_id).delete()

    db.session.delete(stock)
    db.session.commit()

    log_audit_action(
        admin.id,
        "STOCK_DELETE",
        f"Admin removed stock {ticker} (ID: {stock_id})."
    )

    return True, f"Stock {ticker} successfully removed."


# ============================================================
# USER / PLAYER MANAGEMENT
# ============================================================

def get_all_users(admin_user_id):
    admin = _get_admin(admin_user_id)

    if not admin:
        return None, "Unauthorized. Only Admins can view users."

    users = User.query.order_by(User.id).all()

    return users, None


def update_user_admin(
    admin_user_id,
    target_user_id,
    cash_balance=None,
    role=None
):
    admin = _get_admin(admin_user_id)

    if not admin:
        return None, "Unauthorized. Only Admins can modify users."

    user = db.session.get(User, target_user_id)

    if not user:
        return None, "User not found."

    if cash_balance is not None:
        if cash_balance < 0:
            return None, "Cash balance cannot be negative."

        user.cash_balance = cash_balance

    if role is not None:
        if role not in ["Trader", "Regulator", "Admin"]:
            return None, "Invalid role."

        user.role = role

    db.session.commit()

    log_audit_action(
        admin.id,
        "USER_UPDATE",
        f"Admin updated User #{target_user_id} "
        f"({user.username}). "
        f"Cash: {user.cash_balance}, "
        f"Role: {user.role}"
    )

    return user, None


# ============================================================
# PORTFOLIO / PLAYER INFORMATION
# ============================================================

def get_all_portfolios(admin_user_id):
    admin = _get_admin(admin_user_id)

    if not admin:
        return None, "Unauthorized. Only Admins can view portfolios."

    portfolios = (
        Portfolio.query
        .join(User, Portfolio.user_id == User.id)
        .join(Stock, Portfolio.stock_id == Stock.id)
        .order_by(User.id, Stock.ticker)
        .all()
    )

    return portfolios, None


# ============================================================
# ORDER / TRADING ACTIVITY
# ============================================================

def get_all_orders(admin_user_id):
    admin = _get_admin(admin_user_id)

    if not admin:
        return None, "Unauthorized. Only Admins can view orders."

    orders = (
        Order.query
        .order_by(Order.created_at.desc())
        .all()
    )

    return orders, None


def get_completed_trades(admin_user_id):
    admin = _get_admin(admin_user_id)

    if not admin:
        return None, "Unauthorized. Only Admins can view completed trades."

    trades = (
        Order.query
        .filter_by(status="EXECUTED")
        .order_by(Order.created_at.desc())
        .all()
    )

    return trades, None


# ============================================================
# AUDIT LOGS
# ============================================================

def get_all_audit_logs(admin_user_id):
    admin = _get_admin(admin_user_id)

    if not admin:
        return None, "Unauthorized. Only Admins can view audit logs."

    logs = (
        AuditLog.query
        .order_by(AuditLog.timestamp.desc())
        .all()
    )

    return logs, None
