from flask import Blueprint, render_template, request, redirect, url_for, flash
from ..extensions import db
from ..models import User, AuditLog, ROLES
from ..security import roles_required, log

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.route("/users", methods=["GET", "POST"])
@roles_required("admin")
def users():
    if request.method == "POST":
        f = request.form
        username, password, role = f["username"].strip(), f["password"], f["role"]
        if role not in ROLES or len(password) < 8:
            flash("Valid role and a password of at least 8 characters are required.", "error")
        elif User.query.filter_by(username=username).first():
            flash("Username already exists.", "error")
        else:
            u = User(username=username, full_name=f["full_name"].strip(), role=role)
            u.set_password(password)
            db.session.add(u)
            db.session.flush()
            log("CREATE", "User", u.id, role)
            db.session.commit()
            flash("User created.", "ok")
        return redirect(url_for("admin.users"))
    return render_template("admin/users.html", users=User.query.order_by(User.username).all(), roles=ROLES)


@bp.route("/users/<int:user_id>/toggle", methods=["POST"])
@roles_required("admin")
def toggle_user(user_id):
    u = db.get_or_404(User, user_id)
    u.active = not u.active
    log("UPDATE", "User", u.id, f"active={u.active}")
    db.session.commit()
    return redirect(url_for("admin.users"))


@bp.route("/audit")
@roles_required("admin")
def audit():
    entries = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(300).all()
    return render_template("admin/audit.html", entries=entries)
