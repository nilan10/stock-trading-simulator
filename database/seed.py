import os

from flask import Flask
from werkzeug.security import generate_password_hash

from models.models import (
    db,
    User,
    Stock,
    GameState,
    Order,
    Portfolio,
    StockPriceHistory,
    AuditLog
)


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+mysqlconnector://{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}/"
    f"{os.getenv('DB_NAME')}"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


# ============================================================
# CANONICAL GAME CONFIGURATION
# ============================================================

STARTING_CAPITAL = 150000.00
MARKET_FEE_PERCENT = 5.00
ROUND_DURATION = 60


# ============================================================
# CANONICAL STOCK MARKET
# ============================================================

INITIAL_STOCKS = [
    {
        "ticker": "AAPL",
        "company_name": "Apple Inc.",
        "current_price": 150.00,
        "total_supply": 5000,
        "available_supply": 5000,
        "volatility": 5.00
    },
    {
        "ticker": "TSLA",
        "company_name": "Tesla Inc.",
        "current_price": 200.00,
        "total_supply": 4000,
        "available_supply": 4000,
        "volatility": 8.00
    },
    {
        "ticker": "GOOGL",
        "company_name": "Alphabet Inc.",
        "current_price": 100.00,
        "total_supply": 5000,
        "available_supply": 5000,
        "volatility": 4.00
    },
    {
        "ticker": "KO",
        "company_name": "Coca-Cola Co.",
        "current_price": 60.00,
        "total_supply": 15000,
        "available_supply": 15000,
        "volatility": 1.00
    },
    {
        "ticker": "BTC",
        "company_name": "Bitcoin",
        "current_price": 10000.00,
        "total_supply": 100,
        "available_supply": 100,
        "volatility": 15.00
    },
    {
        "ticker": "FMB",
        "company_name": "First Metro Bank",
        "current_price": 10.00,
        "total_supply": 20000,
        "available_supply": 20000,
        "volatility": 3.00
    },
    {
        "ticker": "GME",
        "company_name": "GameStop Corp.",
        "current_price": 40.00,
        "total_supply": 2500,
        "available_supply": 2500,
        "volatility": 12.00
    },
    {
        "ticker": "SML",
        "company_name": "Small Market Logistics",
        "current_price": 25.00,
        "total_supply": 1000,
        "available_supply": 1000,
        "volatility": 8.00
    },
    {
        "ticker": "TNY",
        "company_name": "Tiny Industries",
        "current_price": 25.00,
        "total_supply": 300,
        "available_supply": 300,
        "volatility": 10.00
    }
]


# ============================================================
# SEED DATABASE
# ============================================================

def seed_database():
    """
    Initialize the database without destroying existing data.

    Creates the canonical admin, regulator, stocks, and game
    state if they do not already exist.
    """

    with app.app_context():

        # ----------------------------------------------------
        # DEFAULT ADMIN
        # ----------------------------------------------------

        admin = User.query.filter_by(username="admin").first()

        if not admin:
            admin = User(
                username="admin",
                password_hash=generate_password_hash("nimda"),
                role="Admin",
                cash_balance=STARTING_CAPITAL
            )

            db.session.add(admin)
            db.session.commit()

            print("Created default admin account.")

        # ----------------------------------------------------
        # DEFAULT REGULATOR
        # ----------------------------------------------------

        regulator = User.query.filter_by(
            username="regulator"
        ).first()

        if not regulator:
            regulator = User(
                username="regulator",
                password_hash=generate_password_hash("reg123"),
                role="Regulator",
                cash_balance=STARTING_CAPITAL
            )

            db.session.add(regulator)
            db.session.commit()

            print("Created default regulator account.")

        # ----------------------------------------------------
        # DEFAULT STOCKS
        # ----------------------------------------------------

        for stock_data in INITIAL_STOCKS:

            existing_stock = Stock.query.filter_by(
                ticker=stock_data["ticker"]
            ).first()

            if not existing_stock:

                stock = Stock(**stock_data)

                db.session.add(stock)

                print(
                    f"Created stock {stock_data['ticker']}."
                )

        db.session.commit()

        # ----------------------------------------------------
        # GAME STATE
        # ----------------------------------------------------

        game_state = GameState.query.first()

        if not game_state:

            game_state = GameState(
                current_round=1,
                time_remaining=ROUND_DURATION,
                status="PAUSED",
                starting_capital=STARTING_CAPITAL,
                market_fee_percent=MARKET_FEE_PERCENT
            )

            db.session.add(game_state)
            db.session.commit()

            print("Created initial game state.")

        # ----------------------------------------------------
        # INITIAL AUDIT LOG
        # ----------------------------------------------------

        audit = AuditLog(
            user_id=admin.id,
            action="SYSTEM_INIT",
            details="Initialized canonical stock trading simulator state."
        )

        db.session.add(audit)
        db.session.commit()

        print("Database seeding complete.")


# ============================================================
# HARD RESET
# ============================================================

def reset_database():
    """
    Completely restore the database to the canonical game state.

    This is intentionally destructive.

    It removes:
        - Registered traders
        - Existing admin/regulator accounts
        - Orders
        - Portfolios
        - Stock price history
        - Audit history
        - Existing stocks

    It recreates:
        - Canonical admin
        - Canonical regulator
        - Canonical stocks
        - Canonical game configuration

    The game starts PAUSED on Round 1 with 60 seconds remaining.
    """

    with app.app_context():

        print("Starting hard reset...")

        # ----------------------------------------------------
        # DELETE DEPENDENT GAMEPLAY DATA
        # ----------------------------------------------------

        StockPriceHistory.query.delete()
        Order.query.delete()
        Portfolio.query.delete()

        # Audit logs reference users through user_id, so they
        # MUST be deleted before users.
        AuditLog.query.delete()

        db.session.commit()

        print(
            "Cleared orders, portfolios, price history, "
            "and audit logs."
        )

        # ----------------------------------------------------
        # DELETE USERS
        #
        # This removes registered traders as well as the
        # existing admin and regulator.
        #
        # Canonical accounts are recreated below.
        # ----------------------------------------------------

        User.query.delete()

        db.session.commit()

        print("Cleared users.")

        # ----------------------------------------------------
        # DELETE STOCKS
        # ----------------------------------------------------

        Stock.query.delete()

        db.session.commit()

        print("Cleared stocks.")

        # ----------------------------------------------------
        # RESET GAME STATE
        # ----------------------------------------------------

        game_state = GameState.query.first()

        if not game_state:

            game_state = GameState()

            db.session.add(game_state)

        game_state.current_round = 1
        game_state.time_remaining = ROUND_DURATION
        game_state.status = "PAUSED"
        game_state.starting_capital = STARTING_CAPITAL
        game_state.market_fee_percent = MARKET_FEE_PERCENT

        db.session.commit()

        print("Reset game state.")

        # ----------------------------------------------------
        # RECREATE CANONICAL ADMIN
        # ----------------------------------------------------

        admin = User(
            username="admin",
            password_hash=generate_password_hash("nimda"),
            role="Admin",
            cash_balance=STARTING_CAPITAL,
            reserved_cash=0.00
        )

        # ----------------------------------------------------
        # RECREATE CANONICAL REGULATOR
        # ----------------------------------------------------

        regulator = User(
            username="regulator",
            password_hash=generate_password_hash("reg123"),
            role="Regulator",
            cash_balance=STARTING_CAPITAL,
            reserved_cash=0.00
        )

        db.session.add_all([
            admin,
            regulator
        ])

        db.session.commit()

        print("Recreated canonical accounts.")

        # ----------------------------------------------------
        # RECREATE CANONICAL STOCK MARKET
        # ----------------------------------------------------

        for stock_data in INITIAL_STOCKS:

            stock = Stock(**stock_data)

            db.session.add(stock)

        db.session.commit()

        print("Recreated canonical stock market.")

        # ----------------------------------------------------
        # CREATE HARD RESET AUDIT LOG
        # ----------------------------------------------------

        audit = AuditLog(
            user_id=admin.id,
            action="HARD_RESET",
            details="Hard reset restored canonical simulator state."
        )

        db.session.add(audit)

        db.session.commit()

        print("Hard reset complete.")


# ============================================================
# RUN INITIAL SEED
# ============================================================

if __name__ == "__main__":
    seed_database()