import random
import time
from datetime import datetime
from decimal import Decimal

from models.models import (
    db,
    GameState,
    Stock,
    StockPriceHistory,
    User,
    Portfolio
)

from services.market_order_service import (
    get_open_market_orders,
    execute_market_buy,
    execute_market_sell
)


# =========================
# GAME CONFIGURATION
# =========================

ROUND_DURATION = 60
TIMER_INTERVAL = 1


# =========================
# GAME STATE
# =========================

def get_game_state():
    game_state = GameState.query.first()

    if not game_state:
        game_state = GameState(
            current_round=1,
            time_remaining=ROUND_DURATION,
            status="PAUSED"
        )

        db.session.add(game_state)
        db.session.commit()

    return game_state


# =========================
# START GAME
# =========================

def start_game():
    game_state = get_game_state()

    if game_state.status == "ACTIVE":
        return False, "The game is already active."

    if game_state.status == "ENDED":
        return False, "The game has ended. Reset the game before starting again."

    if game_state.time_remaining <= 0:
        game_state.time_remaining = ROUND_DURATION

    game_state.status = "ACTIVE"

    db.session.commit()

    return True, "Game started."


# =========================
# PAUSE GAME
# =========================

def pause_game():
    game_state = get_game_state()

    if game_state.status != "ACTIVE":
        return False, "The game is not currently active."

    game_state.status = "PAUSED"

    db.session.commit()

    return True, "Game paused."


# =========================
# RESUME GAME
# =========================

def resume_game():
    game_state = get_game_state()

    if game_state.status != "PAUSED":
        return False, "The game is not paused."

    game_state.status = "ACTIVE"

    db.session.commit()

    return True, "Game resumed."


# =========================
# END GAME
# =========================

def end_game():
    game_state = get_game_state()

    if game_state.status == "ENDED":
        return False, "The game has already ended."

    game_state.status = "ENDED"

    db.session.commit()

    return True, "Game ended."


# =========================
# END ROUND
# =========================

def end_round():
    game_state = get_game_state()

    if game_state.status == "ENDED":
        return False, "The game has ended."

    # Market orders execute before prices change.
    executed_orders, cancelled_orders = process_market_orders()

    # Apply stock price movement after market orders execute.
    update_stock_prices()

    # Record the new prices.
    record_price_history()

    # Advance to the next round.
    game_state.current_round += 1
    game_state.time_remaining = ROUND_DURATION
    game_state.status = "ACTIVE"

    db.session.commit()

    return (
        True,
        (
            f"Round completed. "
            f"{executed_orders} market orders executed, "
            f"{cancelled_orders} cancelled. "
            f"Round {game_state.current_round} started."
        )
    )


# =========================
# PROCESS MARKET ORDERS
# =========================

def process_market_orders():
    orders = get_open_market_orders()

    executed_count = 0
    cancelled_count = 0

    for order in orders:

        if order.order_type == "BUY":
            success, message = execute_market_buy(order)

        elif order.order_type == "SELL":
            success, message = execute_market_sell(order)

        else:
            success = False
            message = "Invalid market order type."

        if success:
            executed_count += 1
        else:
            cancel_market_order(order)
            cancelled_count += 1

    db.session.commit()

    return executed_count, cancelled_count


# =========================
# CANCEL MARKET ORDER
# =========================

def cancel_market_order(order):
    user = db.session.get(User, order.user_id)

    if order.order_type == "BUY":

        if user:
            trade_value = (
                Decimal(str(order.price))
                * order.quantity
            )

            market_fee = Decimal(str(order.market_fee))

            reserved_amount = trade_value + market_fee

            user.reserved_cash -= reserved_amount

            if user.reserved_cash < Decimal("0.00"):
                user.reserved_cash = Decimal("0.00")

    elif order.order_type == "SELL":

        portfolio = Portfolio.query.filter_by(
            user_id=order.user_id,
            stock_id=order.stock_id
        ).first()

        if portfolio:
            portfolio.reserved_quantity -= order.quantity

            if portfolio.reserved_quantity < 0:
                portfolio.reserved_quantity = 0

    order.status = "CANCELLED"


# =========================
# UPDATE STOCK PRICES
# =========================

def update_stock_prices():
    stocks = Stock.query.all()

    for stock in stocks:
        current_price = Decimal(str(stock.current_price))
        volatility = Decimal(str(stock.volatility))

        # Random movement between
        # -volatility% and +volatility%.
        percentage_change = Decimal(
            str(
                random.uniform(
                    float(-volatility),
                    float(volatility)
                )
            )
        )

        price_change = (
            current_price
            * percentage_change
            / Decimal("100")
        )

        new_price = current_price + price_change

        # Stock price cannot fall below one cent.
        if new_price < Decimal("0.01"):
            new_price = Decimal("0.01")

        stock.current_price = new_price.quantize(
            Decimal("0.01")
        )


# =========================
# RECORD PRICE HISTORY
# =========================

def record_price_history():
    stocks = Stock.query.all()

    for stock in stocks:
        history = StockPriceHistory(
            stock_id=stock.id,
            price=stock.current_price,
            recorded_at=datetime.utcnow()
        )

        db.session.add(history)

    db.session.commit()


# =========================
# TIMER
# =========================

def run_game_timer(app):
    """
    Background game timer.

    Uses elapsed real time rather than assuming each loop
    iteration takes exactly one second.
    """

    last_check = time.monotonic()

    while True:

        time.sleep(TIMER_INTERVAL)

        current_time = time.monotonic()
        elapsed_seconds = current_time - last_check
        last_check = current_time

        try:
            with app.app_context():

                game_state = GameState.query.first()

                if not game_state:
                    continue

                if game_state.status != "ACTIVE":
                    continue

                seconds_elapsed = int(elapsed_seconds)

                if seconds_elapsed < 1:
                    seconds_elapsed = 1

                game_state.time_remaining -= seconds_elapsed

                if game_state.time_remaining <= 0:
                    game_state.time_remaining = 0
                    db.session.commit()

                    end_round()

                else:
                    db.session.commit()

        except Exception as error:
            print(f"Game timer error: {error}")

            try:
                db.session.rollback()
            except Exception:
                pass