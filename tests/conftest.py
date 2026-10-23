import pytest
from app import create_app
from app.extensions import db
from app.models import User, Beneficiary, Case
from config import TestConfig


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        for name, role in [("sup", "supervisor"), ("cw1", "case_worker"), ("cw2", "case_worker"),
                           ("mgmt", "management"), ("adm", "admin")]:
            u = User(username=name, full_name=name, role=role)
            u.set_password("Password123!")
            db.session.add(u)
        db.session.flush()
        b = Beneficiary(ref_no="B-1", full_name="Test Person", consent_given=True)
        db.session.add(b)
        db.session.flush()
        cw1 = User.query.filter_by(username="cw1").first()
        db.session.add(Case(case_no="C-1", beneficiary_id=b.id, category="Health", assigned_to_id=cw1.id))
        db.session.commit()
        yield app


def login(client, username):
    return client.post("/login", data={"username": username, "password": "Password123!"}, follow_redirects=True)
