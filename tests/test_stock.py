import unittest
from app import app
from models.models import db, Stock


class TestStockModule(unittest.TestCase):

    def setUp(self):
        """Set up an isolated test database before each test run."""
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.client = app.test_client()

        with app.app_context():
            db.create_all()

            # Seed test stocks
            stock1 = Stock(
                ticker="AAPL",
                company_name="Apple Inc.",
                current_price=150.00,
                total_supply=1000,
                available_supply=800
            )
            stock2 = Stock(
                ticker="TSLA",
                company_name="Tesla Inc.",
                current_price=200.00,
                total_supply=500,
                available_supply=500
            )

            db.session.add_all([stock1, stock2])
            db.session.commit()

            self.stock1_id = stock1.id
            self.stock2_id = stock2.id

    def tearDown(self):
        """Clean up database session after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    # ============================================================
    # SERVICE TESTS
    # ============================================================

    def test_get_all_stocks(self):
        from services.stock_service import get_all_stocks
        with app.app_context():
            stocks = get_all_stocks()
            self.assertEqual(len(stocks), 2)
            tickers = [s.ticker for s in stocks]
            self.assertIn("AAPL", tickers)
            self.assertIn("TSLA", tickers)

    def test_get_stock_by_ticker_case_insensitive(self):
        from services.stock_service import get_stock_by_ticker
        with app.app_context():
            # Lowercase input should still find uppercase ticker
            stock = get_stock_by_ticker("aapl")
            self.assertIsNotNone(stock)
            self.assertEqual(stock.company_name, "Apple Inc.")

    def test_get_stock_by_ticker_not_found(self):
        from services.stock_service import get_stock_by_ticker
        with app.app_context():
            stock = get_stock_by_ticker("NVDA")
            self.assertIsNone(stock)

    # ============================================================
    # CONTROLLER ENDPOINT TESTS
    # ============================================================

    def test_get_stocks_endpoint(self):
        response = self.client.get("/stocks")
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["ticker"], "AAPL")
        self.assertEqual(data[0]["current_price"], 150.00)

    def test_get_single_stock_endpoint_success(self):
        response = self.client.get("/stocks/TSLA")
        self.assertEqual(response.status_code, 200)

        data = response.get_json()
        self.assertEqual(data["ticker"], "TSLA")
        self.assertEqual(data["company_name"], "Tesla Inc.")
        self.assertEqual(data["total_supply"], 500)

    def test_get_single_stock_endpoint_not_found(self):
        response = self.client.get("/stocks/GOOGL")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"], "Stock not found.")


if __name__ == "__main__":
    unittest.main()