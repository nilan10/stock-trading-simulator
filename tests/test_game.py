import unittest
from unittest.mock import patch
from app import app
from models.models import db, GameState, Stock, StockPriceHistory


class TestGameModule(unittest.TestCase):

    def setUp(self):
        """Set up an isolated test database before each test run."""
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.client = app.test_client()

        with app.app_context():
            db.create_all()

            # Seed basic game state
            game_state = GameState(
                current_round=1,
                time_remaining=60,
                status="PAUSED",
                starting_capital=100000.00,
                market_fee_percent=5.00
            )
            # Seed a stock to test price updates
            stock = Stock(
                ticker="AAPL",
                company_name="Apple Inc.",
                current_price=100.00,
                volatility=10.00
            )
            db.session.add_all([game_state, stock])
            db.session.commit()

            self.stock_id = stock.id

    def tearDown(self):
        """Clean up database session after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    # ============================================================
    # SERVICE TESTS
    # ============================================================

    def test_start_and_pause_game_service(self):
        from services.game_service import start_game, pause_game
        with app.app_context():
            # Start game
            success, msg = start_game()
            self.assertTrue(success)
            self.assertEqual(GameState.query.first().status, "ACTIVE")

            # Pause game
            success, msg = pause_game()
            self.assertTrue(success)
            self.assertEqual(GameState.query.first().status, "PAUSED")

    def test_update_stock_prices_and_history(self):
        from services.game_service import update_stock_prices, record_price_history
        with app.app_context():
            update_stock_prices()
            record_price_history()

            stock = db.session.get(Stock, self.stock_id)
            history = StockPriceHistory.query.filter_by(stock_id=self.stock_id).first()

            # Price should be updated and price history record saved
            self.assertGreater(stock.current_price, 0)
            self.assertIsNotNone(history)

    @patch("services.game_service.process_market_orders")
    def test_end_round_advances_round(self, mock_process_orders):
        mock_process_orders.return_value = (0, 0)
        from services.game_service import end_round

        with app.app_context():
            success, msg = end_round()
            self.assertTrue(success)

            state = GameState.query.first()
            self.assertEqual(state.current_round, 2)
            self.assertEqual(state.status, "ACTIVE")

    # ============================================================
    # CONTROLLER / ENDPOINT TESTS
    # ============================================================

    def test_get_game_status_endpoint(self):
        response = self.client.get("/game")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["current_round"], 1)

    def test_start_game_endpoint_unauthorized_for_non_admin(self):
        with self.client.session_transaction() as sess:
            sess["role"] = "Trader"

        response = self.client.post("/game/start")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Unauthorized", response.get_json()["error"])

    def test_start_game_endpoint_admin_success(self):
        with self.client.session_transaction() as sess:
            sess["role"] = "Admin"

        response = self.client.post("/game/start")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["message"], "Game started.")


if __name__ == "__main__":
    unittest.main()