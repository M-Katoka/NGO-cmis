from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required
from ..extensions import db
from ..models import User
from ..security import log

bp = Blueprint("auth", __name__)


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = User.query.filter_by(username=request.form.get("username", "").strip()).first()
        if user and user.active and user.check_password(request.form.get("password", "")):
            login_user(user)
            log("LOGIN", "User", user.id)
            db.session.commit()
            return redirect(url_for("main.dashboard"))
        log("LOGIN_FAILED", detail=request.form.get("username", "")[:60])
        db.session.commit()
        flash("Invalid credentials.", "error")  # generic message on purpose
    return render_template("auth/login.html")


@bp.route("/logout")
@login_required
def logout():
    log("LOGOUT")
    db.session.commit()
    logout_user()
    return redirect(url_for("auth.login"))
