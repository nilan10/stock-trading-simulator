import os
from flask import Flask
from werkzeug.security import generate_password_hash

from models.models import db, User, Stock, GameState, AuditLog


app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+mysqlconnector://{os.getenv('DB_USER')}:"
    f"{os.getenv('DB_PASSWORD')}@"
    f"{os.getenv('DB_HOST')}/"
    f"{os.getenv('DB_NAME')}"
)

app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)


def seed_database():
    with app.app_context():

        # =========================
        # SEED DEFAULT USERS
        # =========================

        if User.query.count() == 0:

            admin = User(
                username="admin",
                password_hash=generate_password_hash("admin123"),
                role="Admin",
                cash_balance=1000.00
            )

            regulator = User(
                username="regulator",
                password_hash=generate_password_hash("reg123"),
                role="Regulator",
                cash_balance=1000.00
            )

            trader = User(
                username="trader1",
                password_hash=generate_password_hash("pass123"),
                role="Trader",
                cash_balance=1000.00
            )

            db.session.add_all([admin, regulator, trader])
            db.session.commit()

            audit = AuditLog(
                user_id=admin.id,
                action="SYSTEM_INIT",
                details="Seeded initial default users (Admin, Regulator, Trader)."
            )

            db.session.add(audit)
            db.session.commit()


            print("Successfully seeded users!")
        admin = User.query.filter_by(username="admin").first()	

        # =========================
        # SEED DEFAULT STOCKS
        # =========================

        if Stock.query.count() == 0:

            aapl = Stock(
                ticker="AAPL",
                company_name="Apple Inc.",
                current_price=150.00,
                total_supply=1000,
                available_supply=1000
            )

            tsla = Stock(
                ticker="TSLA",
                company_name="Tesla Inc.",
                current_price=200.00,
                total_supply=1000,
                available_supply=1000
            )

            googl = Stock(
                ticker="GOOGL",
                company_name="Alphabet Inc.",
                current_price=100.00,
                total_supply=1000,
                available_supply=1000
            )

            db.session.add_all([aapl, tsla, googl])
            db.session.commit()

            audit = AuditLog(
                user_id=admin.id,
                action="SYSTEM_INIT",
                details="Seeded initial market stocks (AAPL, TSLA, GOOGL)."
            )

            db.session.add(audit)
            db.session.commit()

            print("Successfully seeded stocks!")

        # =========================
        # SEED GAME STATE
        # =========================

        if GameState.query.count() == 0:

            initial_state = GameState(
                current_round=1,
                time_remaining=0,
                status="ACTIVE"
            )

            db.session.add(initial_state)
            db.session.commit()

            print("Successfully initialized Game State to Round 1!")


if __name__ == "__main__":
    seed_database()
