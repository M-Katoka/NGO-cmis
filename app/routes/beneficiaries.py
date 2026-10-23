from datetime import date, datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from ..extensions import db
from ..models import Beneficiary
from ..security import roles_required, log

bp = Blueprint("beneficiaries", __name__, url_prefix="/beneficiaries")

# Registration is a supervisor/case-worker function (least privilege).
STAFF = ("supervisor", "case_worker")


def _d(value):
    return datetime.strptime(value, "%Y-%m-%d").date() if value else None


@bp.route("/")
@roles_required(*STAFF)
def index():
    q = request.args.get("q", "").strip()
    query = Beneficiary.query
    if q:
        query = query.filter(Beneficiary.full_name.ilike(f"%{q}%") | Beneficiary.ref_no.ilike(f"%{q}%"))
    log("SEARCH_BENEFICIARY", detail=q[:60])
    db.session.commit()
    return render_template("beneficiaries/index.html", beneficiaries=query.order_by(Beneficiary.full_name).limit(100).all(), q=q)


@bp.route("/new", methods=["GET", "POST"])
@roles_required(*STAFF)
def create():
    if request.method == "POST":
        f = request.form
        if not f.get("full_name", "").strip():
            flash("Full name is required.", "error")
            return render_template("beneficiaries/form.html")
        consent = f.get("consent_given") == "on"
        b = Beneficiary(full_name=f["full_name"].strip(), sex=f.get("sex"),
                        date_of_birth=_d(f.get("date_of_birth")), phone=f.get("phone"),
                        address=f.get("address"), guardian_name=f.get("guardian_name"),
                        is_vulnerable=f.get("is_vulnerable") == "on",
                        consent_given=consent, consent_date=date.today() if consent else None,
                        processing_basis_note=f.get("processing_basis_note"),
                        created_by_id=current_user.id)
        db.session.add(b)
        db.session.flush()
        b.ref_no = f"B-{b.id:04d}"
        log("CREATE", "Beneficiary", b.id)
        db.session.commit()
        flash(f"Beneficiary {b.ref_no} registered.", "ok")
        return redirect(url_for("beneficiaries.detail", beneficiary_id=b.id))
    return render_template("beneficiaries/form.html")


@bp.route("/<int:beneficiary_id>")
@roles_required(*STAFF)
def detail(beneficiary_id):
    b = db.get_or_404(Beneficiary, beneficiary_id)
    log("VIEW", "Beneficiary", b.id)
    db.session.commit()
    # Case workers only see the case links they are allowed to open.
    cases = b.cases.all()
    if current_user.role == "case_worker":
        cases = [c for c in cases if c.assigned_to_id == current_user.id]
    return render_template("beneficiaries/detail.html", b=b, cases=cases)
