import csv, io
from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, abort
from flask_login import current_user
from ..extensions import db
from ..models import (Beneficiary, Case, Assessment, Intervention, Referral, FollowUp, User,
                      RISK_LEVELS, REFERRAL_STATUSES)
from ..security import roles_required, get_case_or_403, accessible_cases_query, log

bp = Blueprint("cases", __name__, url_prefix="/cases")
STAFF = ("supervisor", "case_worker")


def _d(value, default=None):
    return datetime.strptime(value, "%Y-%m-%d").date() if value else default


def _open_case_or_400(case):
    if case.is_closed:
        abort(400, "Case is closed; records cannot be added.")


@bp.route("/")
@roles_required(*STAFF)
def index():
    q = request.args.get("q", "").strip()
    status = request.args.get("status", "")
    query = accessible_cases_query(current_user).join(Beneficiary)
    if q:
        query = query.filter(Case.case_no.ilike(f"%{q}%") | Beneficiary.full_name.ilike(f"%{q}%"))
    if status:
        query = query.filter(Case.status == status)
    return render_template("cases/index.html", cases=query.order_by(Case.opened_at.desc()).limit(200).all(),
                           q=q, status=status)


@bp.route("/export.csv")
@roles_required(*STAFF)
def export_csv():
    """Export uses the SAME scoped query as the list (Chapter 2.1 security testing)."""
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["case_no", "beneficiary_ref", "category", "priority", "status", "assigned_to", "opened_at"])
    for c in accessible_cases_query(current_user).all():
        w.writerow([c.case_no, c.beneficiary.ref_no, c.category, c.priority, c.status,
                    c.assigned_to.username if c.assigned_to else "", c.opened_at.date()])
    log("EXPORT", "Case", detail="cases csv")
    db.session.commit()
    return Response(buf.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=cases.csv"})


@bp.route("/new/<int:beneficiary_id>", methods=["GET", "POST"])
@roles_required(*STAFF)
def create(beneficiary_id):
    b = db.get_or_404(Beneficiary, beneficiary_id)
    workers = User.query.filter(User.role.in_(STAFF), User.active.is_(True)).all()
    if request.method == "POST":
        f = request.form
        category = f.get("category", "").strip()
        priority = f.get("priority", "medium")
        if not category or len(category) > 120:
            flash("Enter a case category up to 120 characters.", "error")
            return render_template("cases/form.html", b=b, workers=workers)
        if priority not in {"low", "medium", "high", "critical"}:
            flash("Choose a valid priority.", "error")
            return render_template("cases/form.html", b=b, workers=workers)
        assignee = int(f["assigned_to_id"]) if f.get("assigned_to_id") else None
        if current_user.role == "case_worker":
            assignee = current_user.id  # workers can only open cases for themselves
        elif assignee and not db.session.get(User, assignee):
            flash("Choose an active case worker.", "error")
            return render_template("cases/form.html", b=b, workers=workers)
        c = Case(beneficiary_id=b.id, category=category, priority=priority,
                 assigned_to_id=assignee)
        db.session.add(c)
        db.session.flush()
        c.case_no = f"CASE-{date.today().year}-{c.id:04d}"
        log("CREATE", "Case", c.id)
        db.session.commit()
        return redirect(url_for("cases.detail", case_id=c.id))
    return render_template("cases/form.html", b=b, workers=workers)


@bp.route("/<int:case_id>")
@roles_required(*STAFF)
def detail(case_id):
    case = get_case_or_403(case_id)
    log("VIEW", "Case", case.id)
    db.session.commit()
    workers = User.query.filter(User.role.in_(STAFF), User.active.is_(True)).all()
    return render_template("cases/detail.html", case=case, workers=workers, risks=RISK_LEVELS,
                           ref_statuses=REFERRAL_STATUSES, today=date.today())


@bp.route("/<int:case_id>/assign", methods=["POST"])
@roles_required("supervisor")
def assign(case_id):
    case = get_case_or_403(case_id)
    assigned_to_id = request.form.get("assigned_to_id", "")
    assignee = db.session.get(User, int(assigned_to_id)) if assigned_to_id.isdigit() else None
    if not assignee or not assignee.active or assignee.role not in STAFF:
        flash("Choose an active case worker or supervisor.", "error")
        return redirect(url_for("cases.detail", case_id=case.id))
    case.assigned_to_id = assignee.id
    case.status = "in_progress" if case.status == "open" else case.status
    log("ASSIGN", "Case", case.id, f"to user {case.assigned_to_id}")
    db.session.commit()
    return redirect(url_for("cases.detail", case_id=case.id))


@bp.route("/<int:case_id>/assessments", methods=["POST"])
@roles_required(*STAFF)
def add_assessment(case_id):
    case = get_case_or_403(case_id); _open_case_or_400(case)
    f = request.form
    db.session.add(Assessment(case_id=case.id, assessed_on=_d(f.get("assessed_on"), date.today()),
                              needs=f["needs"], risk_level=f.get("risk_level", "low"),
                              notes=f.get("notes"), assessor_id=current_user.id))
    log("CREATE", "Assessment", case.id)
    db.session.commit()
    return redirect(url_for("cases.detail", case_id=case.id))


@bp.route("/<int:case_id>/interventions", methods=["POST"])
@roles_required(*STAFF)
def add_intervention(case_id):
    case = get_case_or_403(case_id); _open_case_or_400(case)
    f = request.form
    db.session.add(Intervention(case_id=case.id, delivered_on=_d(f.get("delivered_on"), date.today()),
                                intervention_type=f["intervention_type"], description=f["description"],
                                delivered_by_id=current_user.id))
    log("CREATE", "Intervention", case.id)
    db.session.commit()
    return redirect(url_for("cases.detail", case_id=case.id))


@bp.route("/<int:case_id>/referrals", methods=["POST"])
@roles_required(*STAFF)
def add_referral(case_id):
    case = get_case_or_403(case_id); _open_case_or_400(case)
    f = request.form
    db.session.add(Referral(case_id=case.id, provider=f["provider"], service=f["service"],
                            notes=f.get("notes"), referred_by_id=current_user.id))
    log("CREATE", "Referral", case.id)
    db.session.commit()
    return redirect(url_for("cases.detail", case_id=case.id))


@bp.route("/<int:case_id>/referrals/<int:referral_id>/status", methods=["POST"])
@roles_required(*STAFF)
def update_referral(case_id, referral_id):
    case = get_case_or_403(case_id)
    r = db.get_or_404(Referral, referral_id)
    if r.case_id != case.id:
        abort(404)
    status = request.form.get("status")
    if status not in REFERRAL_STATUSES:
        abort(400)
    r.status = status
    r.verified_on = date.today() if status == "completed" else r.verified_on
    log("UPDATE", "Referral", r.id, status)
    db.session.commit()
    return redirect(url_for("cases.detail", case_id=case.id))


@bp.route("/<int:case_id>/followups", methods=["POST"])
@roles_required(*STAFF)
def add_followup(case_id):
    case = get_case_or_403(case_id); _open_case_or_400(case)
    f = request.form
    db.session.add(FollowUp(case_id=case.id, due_date=_d(f["due_date"]), description=f["description"],
                            assigned_to_id=case.assigned_to_id or current_user.id))
    log("CREATE", "FollowUp", case.id)
    db.session.commit()
    return redirect(url_for("cases.detail", case_id=case.id))


@bp.route("/<int:case_id>/followups/<int:fu_id>/done", methods=["POST"])
@roles_required(*STAFF)
def complete_followup(case_id, fu_id):
    case = get_case_or_403(case_id)
    fu = db.get_or_404(FollowUp, fu_id)
    if fu.case_id != case.id:
        abort(404)
    fu.status, fu.completed_on = "done", date.today()
    log("UPDATE", "FollowUp", fu.id, "done")
    db.session.commit()
    return redirect(url_for("cases.detail", case_id=case.id))


@bp.route("/<int:case_id>/close", methods=["POST"])
@roles_required("supervisor")  # closure is an authorised-staff decision
def close(case_id):
    case = get_case_or_403(case_id)
    reason = request.form.get("closure_reason", "").strip()
    if not reason:
        flash("A closure reason is required.", "error")
        return redirect(url_for("cases.detail", case_id=case.id))
    case.status, case.closed_at, case.closed_by_id, case.closure_reason = "closed", datetime.utcnow(), current_user.id, reason
    log("CLOSE", "Case", case.id)
    db.session.commit()
    return redirect(url_for("cases.detail", case_id=case.id))
