from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(
        db.Enum("Trader", "Regulator", "Admin"),
        nullable=False,
        default="Trader"
    )
    cash_balance = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=1000.00
    )
    reserved_cash = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0.00
    )


class Stock(db.Model):
    __tablename__ = "stocks"

    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), unique=True, nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    current_price = db.Column(db.Numeric(12, 2), nullable=False)
    total_supply = db.Column(db.Integer, nullable=False, default=1000)
    available_supply = db.Column(db.Integer, nullable=False, default=1000)
    volatility = db.Column(
        db.Numeric(5, 2),
        nullable=False,
        default=5.00
    )


class StockPriceHistory(db.Model):
    __tablename__ = "stock_price_history"

    id = db.Column(db.Integer, primary_key=True)
    stock_id = db.Column(
        db.Integer,
        db.ForeignKey("stocks.id"),
        nullable=False
    )
    price = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )
    recorded_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp()
    )


class Portfolio(db.Model):
    __tablename__ = "portfolios"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )
    stock_id = db.Column(
        db.Integer,
        db.ForeignKey("stocks.id"),
        nullable=False
    )
    quantity = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )
    reserved_quantity = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )
    avg_buy_price = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0.00
    )

    __table_args__ = (
        db.UniqueConstraint(
            "user_id",
            "stock_id",
            name="unique_user_stock"
        ),
    )


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    stock_id = db.Column(
        db.Integer,
        db.ForeignKey("stocks.id"),
        nullable=False
    )

    order_type = db.Column(
        db.Enum("BUY", "SELL"),
        nullable=False
    )

    order_source = db.Column(
        db.Enum("MARKET", "PLAYER"),
        nullable=False,
        default="PLAYER"
    )

    quantity = db.Column(
        db.Integer,
        nullable=False
    )

    price = db.Column(
        db.Numeric(12, 2),
        nullable=False
    )

    market_fee = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=0.00
    )

    status = db.Column(
        db.Enum("OPEN", "EXECUTED", "CANCELLED"),
        nullable=False,
        default="OPEN"
    )

    created_at = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp()
    )

    accepted_by_user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    accepted_at = db.Column(
        db.DateTime,
        nullable=True
    )

    executed_at = db.Column(
        db.DateTime,
        nullable=True
    )


class AuditLog(db.Model):
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)

    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        server_default=db.func.current_timestamp()
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=True
    )

    action = db.Column(
        db.String(100),
        nullable=False
    )

    details = db.Column(
        db.Text,
        nullable=True
    )


class GameState(db.Model):
    __tablename__ = "game_state"

    id = db.Column(db.Integer, primary_key=True)

    current_round = db.Column(
        db.Integer,
        nullable=False,
        default=1
    )

    time_remaining = db.Column(
        db.Integer,
        nullable=False,
        default=0
    )

    status = db.Column(
        db.Enum("ACTIVE", "PAUSED", "ENDED"),
        nullable=False,
        default="ACTIVE"
    )

    starting_capital = db.Column(
        db.Numeric(12, 2),
        nullable=False,
        default=100000.00
    )

    market_fee_percent = db.Column(
        db.Numeric(5, 2),
        nullable=False,
        default=5.00
    )