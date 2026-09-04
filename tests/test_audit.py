import unittest
from app import app
from models.models import db, User, AuditLog
from services.audit_service import log_audit_action


class TestAuditService(unittest.TestCase):

    def setUp(self):
        """Set up an isolated test database before each test run."""
        app.config["TESTING"] = True
        app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"

        with app.app_context():
            db.create_all()

            # Seed a test user for foreign key attachment
            user = User(
                username="audit_test_user",
                password_hash="hashed_pw",
                role="Trader"
            )
            db.session.add(user)
            db.session.commit()
            self.user_id = user.id

    def tearDown(self):
        """Clean up the database session after each test."""
        with app.app_context():
            db.session.remove()
            db.drop_all()

    # ============================================================
    # AUDIT SERVICE TESTS
    # ============================================================

    def test_log_audit_action_success(self):
        """Ensure audit logs are correctly written to the database."""
        with app.app_context():
            log_audit_action(
                user_id=self.user_id,
                action="TEST_ACTION",
                details="Logged a test action successfully."
            )

            # Query database to confirm record was saved
            log = AuditLog.query.filter_by(action="TEST_ACTION").first()

            self.assertIsNotNone(log)
            self.assertEqual(log.user_id, self.user_id)
            self.assertEqual(log.action, "TEST_ACTION")
            self.assertEqual(log.details, "Logged a test action successfully.")
            self.assertIsNotNone(log.timestamp)

    def test_log_audit_action_null_user(self):
        """Ensure system/anonymous actions can log with user_id as None."""
        with app.app_context():
            log_audit_action(
                user_id=None,
                action="SYSTEM_INIT",
                details="System initialized without user context."
            )

            log = AuditLog.query.filter_by(action="SYSTEM_INIT").first()

            self.assertIsNotNone(log)
            self.assertIsNone(log.user_id)
            self.assertEqual(log.details, "System initialized without user context.")


if __name__ == "__main__":
    unittest.main()