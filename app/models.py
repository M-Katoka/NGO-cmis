"""Relational schema (Chapter 2.1): beneficiary is separate from case; assessments,
interventions, referrals and follow-ups are separate linked tables."""
from datetime import datetime, date
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db

ROLES = ("admin", "supervisor", "case_worker", "management")
CASE_STATUSES = ("open", "in_progress", "closed")
REFERRAL_STATUSES = ("pending", "accepted", "completed", "declined")
RISK_LEVELS = ("low", "medium", "high")


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_active(self):  # Flask-Login
        return self.active


class Beneficiary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ref_no = db.Column(db.String(20), unique=True)
    full_name = db.Column(db.String(120), nullable=False)
    sex = db.Column(db.String(10))
    date_of_birth = db.Column(db.Date)
    phone = db.Column(db.String(30))
    address = db.Column(db.String(255))
    guardian_name = db.Column(db.String(120))
    is_vulnerable = db.Column(db.Boolean, default=False)
    # Data Protection Act No. 3 of 2021: record consent / basis for processing
    consent_given = db.Column(db.Boolean, default=False, nullable=False)
    consent_date = db.Column(db.Date)
    processing_basis_note = db.Column(db.String(255))
    created_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    cases = db.relationship("Case", backref="beneficiary", lazy="dynamic")


class Case(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_no = db.Column(db.String(20), unique=True)
    beneficiary_id = db.Column(db.Integer, db.ForeignKey("beneficiary.id"), nullable=False)
    category = db.Column(db.String(60), nullable=False)
    priority = db.Column(db.String(10), default="medium")
    status = db.Column(db.String(20), default="open", nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    opened_at = db.Column(db.DateTime, default=datetime.utcnow)
    closed_at = db.Column(db.DateTime)
    closed_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    closure_reason = db.Column(db.Text)

    assigned_to = db.relationship("User", foreign_keys=[assigned_to_id])
    closed_by = db.relationship("User", foreign_keys=[closed_by_id])
    assessments = db.relationship("Assessment", backref="case", order_by="Assessment.assessed_on")
    interventions = db.relationship("Intervention", backref="case", order_by="Intervention.delivered_on")
    referrals = db.relationship("Referral", backref="case", order_by="Referral.referred_on")
    follow_ups = db.relationship("FollowUp", backref="case", order_by="FollowUp.due_date")

    @property
    def is_closed(self):
        return self.status == "closed"

    def timeline(self):
        """Merged chronological history across all linked record types."""
        ev = []
        for a in self.assessments:
            ev.append((a.assessed_on, "Assessment", f"Risk: {a.risk_level}. {a.needs}", a.assessor))
        for i in self.interventions:
            ev.append((i.delivered_on, "Intervention", f"{i.intervention_type}: {i.description}", i.delivered_by))
        for r in self.referrals:
            ev.append((r.referred_on, "Referral", f"To {r.provider} ({r.service}) - {r.status}", r.referred_by))
        for f in self.follow_ups:
            ev.append((f.due_date, "Follow-up", f"{f.description} - {f.status}", f.assigned_to))
        return sorted(ev, key=lambda e: e[0])


class Assessment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("case.id"), nullable=False)
    assessed_on = db.Column(db.Date, default=date.today, nullable=False)
    needs = db.Column(db.Text, nullable=False)
    risk_level = db.Column(db.String(10), default="low")
    notes = db.Column(db.Text)  # restricted narrative
    assessor_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    assessor = db.relationship("User")


class Intervention(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("case.id"), nullable=False)
    delivered_on = db.Column(db.Date, default=date.today, nullable=False)
    intervention_type = db.Column(db.String(60), nullable=False)
    description = db.Column(db.Text, nullable=False)
    delivered_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    delivered_by = db.relationship("User")


class Referral(db.Model):
    """A referral is a REQUEST to another provider; it needs status + verification."""
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("case.id"), nullable=False)
    referred_on = db.Column(db.Date, default=date.today, nullable=False)
    provider = db.Column(db.String(120), nullable=False)
    service = db.Column(db.String(120), nullable=False)
    status = db.Column(db.String(20), default="pending", nullable=False)
    verified_on = db.Column(db.Date)
    notes = db.Column(db.Text)
    referred_by_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    referred_by = db.relationship("User")


class FollowUp(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    case_id = db.Column(db.Integer, db.ForeignKey("case.id"), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(255), nullable=False)
    status = db.Column(db.String(10), default="pending", nullable=False)
    completed_on = db.Column(db.Date)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    assigned_to = db.relationship("User")

    @property
    def is_overdue(self):
        return self.status == "pending" and self.due_date < date.today()


class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    action = db.Column(db.String(40), nullable=False)
    entity = db.Column(db.String(40))
    entity_id = db.Column(db.Integer)
    detail = db.Column(db.String(255))
    ip_address = db.Column(db.String(45))
    user = db.relationship("User")
