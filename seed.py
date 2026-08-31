from flask import Flask
from models import db, User, Stock, GameState, log_audit_action

app = Flask(__name__)
# Configures SQLite database file named app.db
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)

def seed_database():
    with app.app_context():
        # Creates the database tables defined in models.py
        db.create_all()

        # 1. SEED DEFAULT USERS 
        if User.query.count() == 0:
            admin = User(username='admin', password_hash='admin123', role='Admin', cash_balance=1000.0)
            regulator = User(username='regulator', password_hash='reg123', role='Regulator', cash_balance=1000.0)
            trader = User(username='trader1', password_hash='pass123', role='Trader', cash_balance=1000.0)
            
            db.session.add_all([admin, regulator, trader])
            db.session.commit()
            
            # Log initial setup to Audit Log
            log_audit_action(admin.id, 'SYSTEM_INIT', 'Seeded initial default users (Admin, Regulator, Trader).')
            print("Successfully seeded users!")

        # 2. SEED DEFAULT STOCKS
        if Stock.query.count() == 0:
            aapl = Stock(ticker='AAPL', company_name='Apple Inc.', current_price=150.0, total_supply=1000, available_supply=1000)
            tsla = Stock(ticker='TSLA', company_name='Tesla Inc.', current_price=200.0, total_supply=1000, available_supply=1000)
            googl = Stock(ticker='GOOGL', company_name='Alphabet Inc.', current_price=100.0, total_supply=1000, available_supply=1000)
            
            db.session.add_all([aapl, tsla, googl])
            db.session.commit()
            
            log_audit_action(1, 'SYSTEM_INIT', 'Seeded initial market stocks (AAPL, TSLA, GOOGL).')
            print("Successfully seeded stocks!")

        # 3. SEED GAME STATE
        if GameState.query.count() == 0:
            initial_state = GameState(current_round=1, status='ACTIVE')
            db.session.add(initial_state)
            db.session.commit()
            print("Successfully initialized Game State to Round 1!")

if __name__ == '__main__':
    seed_database()