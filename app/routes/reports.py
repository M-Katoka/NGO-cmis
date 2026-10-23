from datetime import date
from flask import Blueprint, render_template
from sqlalchemy import func
from ..extensions import db
from ..models import Case, Referral, FollowUp, User
from ..security import roles_required, log

bp = Blueprint("reports", __name__, url_prefix="/reports")


@bp.route("/")
@roles_required("supervisor", "management")
def summary():
    """Aggregate-only: no names, no narrative. Safe for management role."""
    by_status = dict(db.session.query(Case.status, func.count(Case.id)).group_by(Case.status).all())
    by_category = db.session.query(Case.category, func.count(Case.id)).group_by(Case.category).all()
    referrals = dict(db.session.query(Referral.status, func.count(Referral.id)).group_by(Referral.status).all())
    overdue = FollowUp.query.filter(FollowUp.status == "pending", FollowUp.due_date < date.today()).count()
    workload = (db.session.query(User.full_name, func.count(Case.id))
                .join(Case, Case.assigned_to_id == User.id)
                .filter(Case.status != "closed").group_by(User.full_name).all())
    log("VIEW_REPORT", detail="summary")
    db.session.commit()
    return render_template("reports/summary.html", by_status=by_status, by_category=by_category,
                           referrals=referrals, overdue=overdue, workload=workload)
