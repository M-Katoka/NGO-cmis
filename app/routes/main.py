from datetime import date, timedelta
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from ..models import FollowUp, Case
from ..security import accessible_cases_query

bp = Blueprint("main", __name__)


@bp.route("/")
@login_required
def dashboard():
    if current_user.role in ("admin", "management"):
        return redirect(url_for("admin.users") if current_user.role == "admin"
                        else url_for("reports.summary"))
    cases = accessible_cases_query(current_user)
    ids = [c.id for c in cases.with_entities(Case.id)]
    fq = FollowUp.query.filter(FollowUp.case_id.in_(ids), FollowUp.status == "pending")
    overdue = fq.filter(FollowUp.due_date < date.today()).order_by(FollowUp.due_date).all()
    upcoming = fq.filter(FollowUp.due_date >= date.today(),
                         FollowUp.due_date <= date.today() + timedelta(days=7)).order_by(FollowUp.due_date).all()
    open_cases = cases.filter(Case.status != "closed").count()
    in_progress = cases.filter(Case.status == "in_progress").count()
    unassigned = cases.filter(Case.assigned_to_id.is_(None), Case.status != "closed").count()
    return render_template("dashboard.html", overdue=overdue, upcoming=upcoming,
                           open_cases=open_cases, in_progress=in_progress, unassigned=unassigned)
