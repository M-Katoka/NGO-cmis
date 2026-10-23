import click
from datetime import date, timedelta
from .extensions import db
from .models import User, Beneficiary, Case, FollowUp


def register_cli(app):
    @app.cli.command("init-db")
    def init_db():
        """Create all tables."""
        db.create_all()
        click.echo("Database initialised.")

    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.option("--full-name", prompt=True)
    @click.password_option()
    def create_admin(username, full_name, password):
        u = User(username=username, full_name=full_name, role="admin")
        u.set_password(password)
        db.session.add(u)
        db.session.commit()
        click.echo(f"Admin '{username}' created.")

    @app.cli.command("seed-demo")
    def seed_demo():
        """Demo users + fake sample data for DEVELOPMENT ONLY."""
        db.create_all()
        users = {}
        for username, name, role in [("admin", "System Admin", "admin"),
                                     ("sup1", "Supervisor One", "supervisor"),
                                     ("cw1", "Case Worker One", "case_worker"),
                                     ("cw2", "Case Worker Two", "case_worker"),
                                     ("mgmt1", "Programme Manager", "management")]:
            u = User(username=username, full_name=name, role=role)
            u.set_password("Password123!")
            db.session.add(u)
            users[username] = u
        db.session.flush()
        b = Beneficiary(ref_no="B-0001", full_name="Demo Beneficiary", sex="F",
                        consent_given=True, consent_date=date.today(),
                        created_by_id=users["sup1"].id)
        db.session.add(b)
        db.session.flush()
        c = Case(case_no="CASE-DEMO-0001", beneficiary_id=b.id, category="Child protection",
                 priority="high", assigned_to_id=users["cw1"].id)
        db.session.add(c)
        db.session.flush()
        db.session.add(FollowUp(case_id=c.id, due_date=date.today() - timedelta(days=2),
                                description="Home visit", assigned_to_id=users["cw1"].id))
        db.session.commit()
        click.echo("Seeded. Demo password for all users: Password123!")
