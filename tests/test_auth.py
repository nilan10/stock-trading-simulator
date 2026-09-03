import unittest
from werkzeug.security import generate_password_hash
from app import app
from models.models import db, User


class TestAuthModule(unittest.TestCase):

    def setUp(self):
        """Set up an isolated test database before each test run."""
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
        self.client = app.test_client()

        with app.app_context():
            db.create_all()

            # Seed existing users for auth testing
            admin = User(
                username="admin_user",
                password_hash=generate_password_hash("admin123"),
                role="Admin"
            )
            trader = User(
                username="test_trader",
                password_hash=generate_password_hash("password123"),
                role="Trader"
            )
            db.session.add_all([admin, trader])
            db.session.commit()

            self.admin_id = admin.id
            self.trader_id = trader.id

    def tearDown(self):
        """Clean up the database session after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    # ============================================================
    # SERVICE / HELPER TESTS
    # ============================================================

    def test_register_user_success(self):
        from services.auth_helpers import register_user
        with app.app_context():
            user, msg = register_user("new_trader", "securepass")
            self.assertIsNotNone(user)
            self.assertEqual(user.role, "Trader")
            self.assertEqual(msg, "Account created successfully.")

    def test_register_user_duplicate_username(self):
        from services.auth_helpers import register_user
        with app.app_context():
            user, msg = register_user("test_trader", "password123")
            self.assertIsNone(user)
            self.assertEqual(msg, "Username already exists.")

    def test_login_user_invalid_password(self):
        from services.auth_helpers import login_user
        with app.app_context():
            user, msg = login_user("test_trader", "wrongpassword")
            self.assertIsNone(user)
            self.assertEqual(msg, "Invalid password.")

    def test_assign_user_role_unauthorized(self):
        from services.auth_helpers import assign_user_role
        with app.app_context():
            success, msg = assign_user_role(self.trader_id, self.admin_id, "Admin")
            self.assertFalse(success)
            self.assertIn("Unauthorized", msg)

    def test_assign_user_role_success(self):
        from services.auth_helpers import assign_user_role
        with app.app_context():
            success, msg = assign_user_role(self.admin_id, self.trader_id, "Regulator")
            self.assertTrue(success)
            
            target = db.session.get(User, self.trader_id)
            self.assertEqual(target.role, "Regulator")

    # ============================================================
    # CONTROLLER / ENDPOINT TESTS
    # ============================================================

    def test_register_endpoint_success(self):
        payload = {"username": "registered_via_api", "password": "pass123"}
        response = self.client.post("/register", json=payload)
        
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.get_json()["username"], "registered_via_api")

    def test_login_endpoint_success(self):
        payload = {"username": "test_trader", "password": "password123"}
        response = self.client.post("/login", json=payload)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["username"], "test_trader")

    def test_login_endpoint_missing_fields(self):
        payload = {"username": "test_trader"}
        response = self.client.post("/login", json=payload)
        
        self.assertEqual(response.status_code, 400)
        self.assertIn("error", response.get_json())


if __name__ == "__main__":
    unittest.main()