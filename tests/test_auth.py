from seed import app
from models import db, User, AuditLog
from auth_helpers import login_or_register, logout_user, assign_user_role

def run_comprehensive_auth_tests():
    with app.app_context():
        print("==========================================")
        print("   RUNNING AUTHENTICATION TEST  ")
        print("==========================================\n")

        # TEST 1: First-Time Login Auto-Registers as Admin
        # Clear database users/logs for a clean test environment
        db.session.query(AuditLog).delete()
        db.session.query(User).delete()
        db.session.commit()

        admin_user, msg = login_or_register("first_admin", "adminpass")
        print(f"[TEST 1] First User Registration: {msg}")
        assert admin_user is not None, "Failed to register first user."
        assert admin_user.role == 'Admin', f"Expected role 'Admin', got '{admin_user.role}'."

        # TEST 2: Second User Auto-Registers as Trader
        trader_user, msg = login_or_register("second_trader", "traderpass")
        print(f"[TEST 2] Second User Registration: {msg}")
        assert trader_user is not None, "Failed to register second user."
        assert trader_user.role == 'Trader', f"Expected role 'Trader', got '{trader_user.role}'."

        # TEST 3: Existing User Correct Password Login
        existing_user, msg = login_or_register("second_trader", "traderpass")
        print(f"[TEST 3] Existing User Login: {msg}")
        assert existing_user.id == trader_user.id, "Login returned wrong user instance."

        # TEST 4: Existing User Wrong Password (Should Fail)
        failed_user, msg = login_or_register("second_trader", "wrongpassword")
        print(f"[TEST 4] Wrong Password Handling: {msg}")
        assert failed_user is None, "User logged in with incorrect password!"

        # TEST 5: Admin Promotes Trader to Regulator
        success, msg = assign_user_role(admin_user.id, trader_user.id, "Regulator")
        print(f"[TEST 5] Admin Role Assignment: {msg}")
        assert success is True, "Admin failed to change role."
        
        # Verify role changed in DB
        updated_trader = User.query.get(trader_user.id)
        assert updated_trader.role == 'Regulator', "Role failed to update in database."

        # TEST 6: Non-Admin Tries to Change Role (Should Fail)
        # Non-admin attempting to promote themselves
        success, msg = assign_user_role(trader_user.id, trader_user.id, "Admin")
        print(f"[TEST 6] Unauthorized Role Change: {msg}")
        assert success is False, "Non-admin successfully changed a role!"

        # TEST 7: Change Role of Non-Existent User
        success, msg = assign_user_role(admin_user.id, 9999, "Trader")
        print(f"[TEST 7] Invalid Target User Role Change: {msg}")
        assert success is False, "Role change succeeded for non-existent user!"

        # TEST 8: Logout Logging
        logout_res = logout_user(trader_user.id)
        print(f"[TEST 8] User Logout: Logged out successfully = {logout_res}")
        assert logout_res is True, "Logout function returned False."

        # TEST 9: Verify Audit Log History Entries
        print("\n------------------------------------------")
        print("          AUDIT LOG CHECK       ")
        print("------------------------------------------")
        audit_entries = AuditLog.query.order_by(AuditLog.id.asc()).all()
        assert len(audit_entries) >= 5, "Audit log missed recording some actions!"

        for entry in audit_entries:
            print(f"Log #{entry.id} | User ID: {entry.user_id} | Action: {entry.action:<15} | Details: {entry.details}")

        print("\nSUCCESS: All 9 authentication tests passed flawlessly!")

if __name__ == '__main__':
    run_comprehensive_auth_tests()