"""RBAC + case-assignment access (Chapter 2.1: Ferraiolo et al.; OWASP ASVS).

admin       -> manages users, views audit log; NO access to case content
supervisor  -> all cases (add a team scope later), assigns and closes cases
case_worker -> only cases assigned to them
management  -> aggregate reports only; NO individual case content
"""
from functools import wraps
from flask import abort, request
from flask_login import current_user
from .extensions import db
from .models import Case, AuditLog


def roles_required(*roles):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def can_access_case(user, case):
    if user.role == "supervisor":
        return True
    if user.role == "case_worker":
        return case.assigned_to_id == user.id
    return False


def accessible_cases_query(user):
    """Single source of truth for list, search AND export so results never leak."""
    if user.role == "supervisor":
        return Case.query
    if user.role == "case_worker":
        return Case.query.filter(Case.assigned_to_id == user.id)
    return Case.query.filter(db.false())


def get_case_or_403(case_id):
    case = db.get_or_404(Case, case_id)
    if not can_access_case(current_user, case):
        log("ACCESS_DENIED", "Case", case_id)
        db.session.commit()
        abort(403)
    return case


def log(action, entity=None, entity_id=None, detail=None):
    uid = current_user.id if current_user.is_authenticated else None
    db.session.add(AuditLog(user_id=uid, action=action, entity=entity,
                            entity_id=entity_id, detail=detail,
                            ip_address=request.remote_addr))
