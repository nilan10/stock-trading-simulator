from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# 1. USER MODEL
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), default='Trader')  # Trader, Regulator, Admin
    cash_balance = db.Column(db.Float, default=1000.0) # Everyone starts with $1,000

# 2. STOCK MODEL
class Stock(db.Model):
    __tablename__ = 'stocks'
    id = db.Column(db.Integer, primary_key=True)
    ticker = db.Column(db.String(10), unique=True, nullable=False)
    company_name = db.Column(db.String(100), nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    total_supply = db.Column(db.Integer, default=1000)
    available_supply = db.Column(db.Integer, default=1000)

# 3. PORTFOLIO MODEL
class Portfolio(db.Model):
    __tablename__ = 'portfolios'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    avg_buy_price = db.Column(db.Float, default=0.0)

# 4. ORDER MODEL
class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    stock_id = db.Column(db.Integer, db.ForeignKey('stocks.id'), nullable=False)
    order_type = db.Column(db.String(10), nullable=False)  # BUY, SELL
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    status = db.Column(db.String(20), default='OPEN')      # OPEN, EXECUTED, CANCELLED
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# 5. AUDIT LOG MODEL (Required for Part 1)
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)

# 6. GAME STATE MODEL
class GameState(db.Model):
    __tablename__ = 'game_state'
    id = db.Column(db.Integer, primary_key=True)
    current_round = db.Column(db.Integer, default=1)
    status = db.Column(db.String(20), default='ACTIVE')     # ACTIVE, PAUSED, ENDED


# HELPER FUNCTION FOR AUDIT LOGS
def log_audit_action(user_id, action, details):
    """Helper function to record system and trading events in the audit table."""
    log_entry = AuditLog(user_id=user_id, action=action, details=details)
    db.session.add(log_entry)
    db.session.commit()