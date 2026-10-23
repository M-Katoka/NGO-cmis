from .conftest import login


def test_assigned_worker_can_open_case(app):
    c = app.test_client(); login(c, "cw1")
    assert c.get("/cases/1").status_code == 200


def test_other_worker_blocked_from_case(app):
    c = app.test_client(); login(c, "cw2")
    assert c.get("/cases/1").status_code == 403


def test_other_worker_blocked_from_search_and_export(app):
    c = app.test_client(); login(c, "cw2")
    assert b"C-1" not in c.get("/cases/?q=Test").data
    assert b"C-1" not in c.get("/cases/export.csv").data


def test_management_cannot_see_case_content(app):
    c = app.test_client(); login(c, "mgmt")
    assert c.get("/cases/1").status_code == 403
    assert c.get("/reports/").status_code == 200


def test_admin_cannot_see_cases_but_sees_audit(app):
    c = app.test_client(); login(c, "adm")
    assert c.get("/cases/1").status_code == 403
    assert c.get("/admin/audit").status_code == 200


def test_closed_case_rejects_new_records(app):
    c = app.test_client(); login(c, "sup")
    c.post("/cases/1/close", data={"closure_reason": "Resolved"})
    r = c.post("/cases/1/interventions", data={"intervention_type": "x", "description": "y"})
    assert r.status_code == 400


def test_unauthenticated_redirected(app):
    assert app.test_client().get("/cases/").status_code in (302, 401)
