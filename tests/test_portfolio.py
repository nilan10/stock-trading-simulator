import unittest
from app import app
from models.models import db, User, Stock, Portfolio, Order, AuditLog


class TestPortfolioModule(unittest.TestCase):

    def setUp(self):
        """Set up an isolated test database before each test run."""
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.client = app.test_client()

        with app.app_context():
            db.create_all()

            # Seed Traders
            trader1 = User(
                username="trader1",
                password_hash="hash",
                role="Trader",
                cash_balance=10000.00
            )
            trader2 = User(
                username="trader2",
                password_hash="hash",
                role="Trader",
                cash_balance=15000.00
            )

            # Seed Stock
            stock = Stock(
                ticker="AAPL",
                company_name="Apple Inc.",
                current_price=150.00,
                available_supply=1000
            )

            db.session.add_all([trader1, trader2, stock])
            db.session.commit()

            self.user1_id = trader1.id
            self.user2_id = trader2.id
            self.stock_id = stock.id

            # Seed Portfolio Entry
            portfolio = Portfolio(
                user_id=trader1.id,
                stock_id=stock.id,
                quantity=10,
                reserved_quantity=0,
                avg_buy_price=100.00
            )

            # Seed Order
            order = Order(
                user_id=trader1.id,
                stock_id=stock.id,
                order_type="BUY",
                order_source="MARKET",
                quantity=10,
                price=100.00,
                status="EXECUTED"
            )

            # Seed AuditLog
            audit_log = AuditLog(
                user_id=trader1.id,
                action="CREATE_MARKET_BUY_ORDER",
                details="Bought 10 shares of AAPL"
            )

            db.session.add_all([portfolio, order, audit_log])
            db.session.commit()

    def tearDown(self):
        """Clean up database session after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    # ============================================================
    # SERVICE TESTS
    # ============================================================

    def test_get_user_portfolio_summary_success(self):
        from services.portfolio_service import get_user_portfolio_summary
        with app.app_context():
            summary, error = get_user_portfolio_summary(self.user1_id)

            self.assertIsNone(error)
            self.assertEqual(summary["user_id"], self.user1_id)
            self.assertEqual(summary["cash_balance"], 10000.00)
            self.assertEqual(summary["total_holdings_value"], 1500.00)  # 10 shares * $150
            self.assertEqual(summary["total_portfolio_value"], 11500.00)
            self.assertEqual(len(summary["holdings"]), 1)

            # Gain calculation: (150 - 100) * 10 = 500
            self.assertEqual(summary["holdings"][0]["unrealized_gain_loss"], 500.00)

    def test_get_user_portfolio_summary_user_not_found(self):
        from services.portfolio_service import get_user_portfolio_summary
        with app.app_context():
            summary, error = get_user_portfolio_summary(9999)
            self.assertIsNone(summary)
            self.assertEqual(error, "User not found.")

    def test_get_user_trade_history(self):
        from services.portfolio_service import get_user_trade_history
        with app.app_context():
            history, error = get_user_trade_history(self.user1_id)

            self.assertIsNone(error)
            self.assertEqual(len(history), 1)
            self.assertEqual(history[0]["ticker"], "AAPL")
            self.assertEqual(history[0]["price"], 100.00)

    def test_get_user_audit_logs(self):
        from services.portfolio_service import get_user_audit_logs
        with app.app_context():
            logs, error = get_user_audit_logs(self.user1_id)

            self.assertIsNone(error)
            self.assertEqual(len(logs), 1)
            self.assertEqual(logs[0]["action"], "CREATE_MARKET_BUY_ORDER")

    def test_get_leaderboard_ordering(self):
        from services.portfolio_service import get_leaderboard
        with app.app_context():
            rankings = get_leaderboard()

            self.assertEqual(len(rankings), 2)
            # Trader2 has $15,000 cash; Trader1 has $10,000 cash + $1,500 holdings = $11,500
            self.assertEqual(rankings[0]["user_id"], self.user2_id)
            self.assertEqual(rankings[0]["total_portfolio_value"], 15000.00)
            self.assertEqual(rankings[1]["user_id"], self.user1_id)

    # ============================================================
    # CONTROLLER ENDPOINT TESTS
    # ============================================================

    def test_get_portfolio_unauthorized(self):
        response = self.client.get("/portfolio")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["error"], "You must be logged in.")

    def test_get_portfolio_success(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user1_id

        response = self.client.get("/portfolio")
        self.assertEqual(response.status_code, 200)
        json_data = response.get_json()
        self.assertEqual(json_data["user_id"], self.user1_id)
        self.assertEqual(json_data["total_portfolio_value"], 11500.00)

    def test_get_trade_history_endpoint(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user1_id

        response = self.client.get("/portfolio/history")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()), 1)

    def test_get_audit_logs_endpoint(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.user1_id

        response = self.client.get("/portfolio/audit")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.get_json()), 1)

    def test_fetch_leaderboard_endpoint(self):
        response = self.client.get("/leaderboard")
        self.assertEqual(response.status_code, 200)
        rankings = response.get_json()
        self.assertEqual(len(rankings), 2)


if __name__ == "__main__":
    unittest.main()