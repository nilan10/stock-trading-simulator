from models.models import db, User, GameState
from services.audit_service import log_audit_action
from werkzeug.security import generate_password_hash, check_password_hash


# =========================
# USER LOGIN
# =========================
# Finds an existing user and verifies their password.
def login_user(username, password):
    user = User.query.filter_by(username=username).first()

    if not user:
        return None, "User not found."

    # Compare the entered password with the stored password hash.
    if not check_password_hash(user.password_hash, password):
        log_audit_action(user.id, "LOGIN", "FAILED_BAD_PASSWORD")
        return None, "Invalid password."

    # Record successful login in the audit log.
    log_audit_action(user.id, "LOGIN", "SUCCESS")
    return user, "Login successful."


# =========================
# USER REGISTRATION
# =========================
# Creates a new user account.
# All newly registered users start as Traders.
def register_user(username, password):
    existing_user = User.query.filter_by(username=username).first()

    if existing_user:
        return None, "Username already exists."

    # Get the current game settings.
    game_state = GameState.query.first()

    # Store a hashed password instead of the actual password.
    new_user = User(
        username=username,
        password_hash=generate_password_hash(password),
        role="Trader",
        cash_balance=game_state.starting_capital
    )

    db.session.add(new_user)
    db.session.commit()

    # Record the new account in the audit log.
    log_audit_action(
        new_user.id,
        "USER_REGISTER",
        "Registered as Trader."
    )

    return new_user, "Account created successfully."


# =========================
# USER LOGOUT
# =========================
# Records when a user logs out.
def logout_user(user_id):
    log_audit_action(user_id, "LOGOUT", "SUCCESS")
    return True


# =========================
# ADMIN ROLE MANAGEMENT
# =========================
# Allows an Admin to change another user's role.
def assign_user_role(admin_user_id, target_user_id, new_role):
    # Verify that the person making the request is an Admin.
    admin = db.session.get(User, admin_user_id)

    if not admin or admin.role != "Admin":
        return False, "Unauthorized. Only Admins can change user roles."

    # Find the user whose role is being changed.
    target_user = db.session.get(User, target_user_id)

    if not target_user:
        return False, "Target user not found."

    # Change the user's role and save the change.
    old_role = target_user.role
    target_user.role = new_role
    db.session.commit()

    # Record the role change for auditing.
    log_audit_action(
        admin_user_id,
        "ROLE_CHANGE",
        f"Updated User #{target_user_id} "
        f"({target_user.username}) from {old_role} to {new_role}."
    )

    return True, f"Successfully updated {target_user.username} to {new_role}."