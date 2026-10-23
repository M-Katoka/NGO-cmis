# NGO Case Management Information System (BIT326 – Group 5)

Web-based case management for an NGO, implementing the workflow defined in Chapters One and Two:
**registration → assignment → assessment → intervention / referral → follow-up → authorised closure.**

Team: Mwamba Z Mwila (Chief Developer), Mwisa Katoka (System Designer), Mutuna Chama (System Analyst)

## Stack
Python 3.11+, Flask, SQLAlchemy, Flask-Login, Flask-WTF (CSRF), SQLite (dev) / PostgreSQL (prod), pytest.

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                    # Windows: copy .env.example .env
flask --app run init-db
flask --app run seed-demo          # DEV ONLY: fake users/data, password Password123!
flask --app run run --debug
```
Demo logins: `admin`, `sup1`, `cw1`, `cw2`, `mgmt1`. For real use: `flask --app run create-admin`.

Run tests: `pytest`

## Structure
```
app/
  models.py        Relational schema (Beneficiary, Case, Assessment, Intervention, Referral, FollowUp, AuditLog, User)
  security.py      Role checks, case-assignment access, scoped queries, audit helper
  routes/          auth, main (dashboard), beneficiaries, cases, reports, admin
  templates/       Jinja pages
  cli.py           init-db, create-admin, seed-demo
tests/             Access-control tests (search + export scoping, closed-case rules)
docs/              Architecture notes and roadmap
```

## Access model (Chapter 2: RBAC + case assignment)
| Role | Can do | Cannot do |
|---|---|---|
| case_worker | Register beneficiaries, work **assigned** cases | See other workers' cases (list, search, export) |
| supervisor | All cases, assign, authorise closure, reports | Manage users |
| management | Aggregate reports | See any individual case |
| admin | Manage users, audit log | See case content |

## Data protection notes (Data Protection Act No. 3 of 2021)
Consent and processing basis are recorded on each beneficiary; all views/changes/exports are written to `AuditLog`;
passwords are hashed; CSRF protection and secure session cookies are enabled. Organisational procedures
(retention, disclosure, hosting, disposal) must still be defined with the NGO.

## Out of scope (per Chapter One)
Payments, clinical diagnosis, national-system integration, advanced AI, offline mode.
