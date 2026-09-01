" User Account Authenitcation File "
from models import db, User, log_audit_action

def login_or_register(username, password):
    """
    Login and instant automatic registration
    - If the user exists: it recognizes password
    - If user does not exist: creates a new user (1st user = Admin, others = Trader)
    """
    user = User.query.filter_by(username=username).first()

    # 1. Existing User: Authenticate Password
    if user:
        if user.password == password:
            log_audit_action(user.id, 'LOGIN', 'SUCCESS')
            return user, "Login successful."
        else:
            log_audit_action(user.id, 'LOGIN', 'FAILED_BAD_PASSWORD')
            return None, "Invalid password for existing account."

    # 2. New User: Automatically Register 
    is_first_user = User.query.count() == 0
    assigned_role = 'Admin' if is_first_user else 'Trader'

    new_user = User(
        username=username,
        password=password,
        role=assigned_role,
        cash_balance=1000.0
    )
    db.session.add(new_user)
    db.session.commit()

    log_audit_action(new_user.id, 'USER_REGISTER', f"Auto-registered as {assigned_role}.")
    log_audit_action(new_user.id, 'LOGIN', 'SUCCESS')
    return new_user, f"Account created! Logged in as {assigned_role}."


def logout_user(user_id):
    """Logs the user logout event."""
    log_audit_action(user_id, 'LOGOUT', 'SUCCESS')
    return True


def assign_user_role(admin_user_id, target_user_id, new_role):
    """Allows an Admin to update another user's role (e.g., to Regulator)."""
    admin = db.session.get(User, admin_user_id)
    if not admin or admin.role != 'Admin':
        return False, "Unauthorized. Only Admins can change user roles."

    target_user = db.session.get(User, target_user_id)
    if not target_user:
        return False, "Target user not found."

    old_role = target_user.role
    target_user.role = new_role
    db.session.commit()

    log_audit_action(
        admin_user_id, 
        'ROLE_CHANGE', 
        f"Updated User #{target_user_id} ({target_user.username}) from {old_role} to {new_role}."
    )
    return True, f"Successfully updated {target_user.username} to {new_role}."