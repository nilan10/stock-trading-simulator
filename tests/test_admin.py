import unittest
from app import app
from models.models import db, User, GameState, Stock


class TestAdminModule(unittest.TestCase):

    def setUp(self):
        """Set up an isolated test database before each test run."""
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.client = app.test_client()

        with app.app_context():
            db.create_all()

            # Seed Admin User
            self.admin = User(
                username="admin_user",
                password_hash="hashed_pw",
                role="Admin",
                cash_balance=100000.00
            )
            # Seed Regular Trader User
            self.trader = User(
                username="trader_user",
                password_hash="hashed_pw",
                role="Trader",
                cash_balance=1000.00
            )

            db.session.add_all([self.admin, self.trader])
            db.session.commit()

            # Save IDs for reference in tests
            self.admin_id = self.admin.id
            self.trader_id = self.trader.id

    def tearDown(self):
        """Clean up the database session after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    # ============================================================
    # SERVICE TESTS
    # ============================================================

    def test_get_current_game_state_unauthorized(self):
        from services.admin_service import get_current_game_state
        with app.app_context():
            state, error = get_current_game_state(self.trader_id)
            self.assertIsNone(state)
            self.assertEqual(error, "Unauthorized. Only Admins can view game state.")

    def test_start_game_service_success(self):
        from services.admin_service import start_game
        with app.app_context():
            state, error = start_game(self.admin_id)
            self.assertIsNone(error)
            self.assertEqual(state.status, "ACTIVE")
            self.assertEqual(state.current_round, 1)

    def test_update_game_settings_validation(self):
        from services.admin_service import start_game, update_game_settings
        with app.app_context():
            start_game(self.admin_id)
            # Negative round should return an error
            state, error = update_game_settings(self.admin_id, current_round=-1)
            self.assertIsNone(state)
            self.assertEqual(error, "Current round must be at least 1.")

    def test_create_stock_service_success(self):
        from services.admin_service import create_stock_admin
        with app.app_context():
            stock, error = create_stock_admin(
                admin_user_id=self.admin_id,
                ticker="AAPL",
                company_name="Apple Inc.",
                current_price=150.00,
                total_supply=1000
            )
            self.assertIsNone(error)
            self.assertEqual(stock.ticker, "AAPL")
            self.assertEqual(stock.available_supply, 1000)

    # ============================================================
    # CONTROLLER / ENDPOINT TESTS
    # ============================================================

    def test_get_game_state_endpoint_forbidden_for_trader(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.trader_id

        response = self.client.get("/admin/game")
        self.assertEqual(response.status_code, 403)
        self.assertIn("Unauthorized", response.get_json()["error"])

    def test_start_game_endpoint_success(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.admin_id

        response = self.client.post("/admin/game/start")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["status"], "ACTIVE")

    def test_create_stock_endpoint_success(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.admin_id

        payload = {
            "ticker": "NVDA",
            "company_name": "NVIDIA Corp",
            "current_price": 120.00,
            "total_supply": 5000
        }
        response = self.client.post("/admin/stocks", json=payload)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["stock"]["ticker"], "NVDA")

    def test_update_user_endpoint_success(self):
        with self.client.session_transaction() as sess:
            sess["user_id"] = self.admin_id

        payload = {"cash_balance": 25000.00, "role": "Regulator"}
        response = self.client.put(f"/admin/users/{self.trader_id}", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["user"]["role"], "Regulator")


if __name__ == "__main__":
    unittest.main()