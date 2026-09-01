from models.models import db, AuditLog


# =========================
# AUDIT LOGGING
# =========================
# Creates a record whenever an important application
# event needs to be tracked.
def log_audit_action(user_id, action, details):
    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        details=details
    )

    db.session.add(audit_log)
    db.session.commit()
