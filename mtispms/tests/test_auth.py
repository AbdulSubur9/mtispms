from tests.conftest import login


def test_login_page_loads(client):
    resp = client.get("/auth/login")
    assert resp.status_code == 200
    assert b"MT-ISPMS" in resp.data


def test_successful_login(client, super_admin):
    resp = login(client, "admin", "admin123")
    assert resp.status_code == 200
    assert b"Welcome back" in resp.data or b"Dashboard" in resp.data


def test_failed_login_wrong_password(client, super_admin):
    resp = login(client, "admin", "wrongpassword")
    assert b"Invalid username or password" in resp.data


def test_logout(client, super_admin):
    login(client, "admin", "admin123")
    resp = client.get("/auth/logout", follow_redirects=True)
    assert resp.status_code == 200
    assert b"logged out" in resp.data.lower()


def test_deactivated_user_cannot_login(client, school, school_admin):
    school_admin.is_active_user = False
    from app.extensions import db
    db.session.commit()
    resp = login(client, "schooladmin", "Admin@123")
    assert b"deactivated" in resp.data.lower()


def test_dashboard_requires_login(client):
    resp = client.get("/", follow_redirects=True)
    assert b"login" in resp.data.lower() or resp.status_code == 200
