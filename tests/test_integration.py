from tests.conftest import login


def test_super_admin_can_view_schools(client, super_admin):
    login(client, "admin", "admin123")
    resp = client.get("/admin/schools")
    assert resp.status_code == 200
    assert b"Schools" in resp.data


def test_school_admin_cannot_view_schools_list(client, school_admin):
    login(client, "schooladmin", "Admin@123")
    resp = client.get("/admin/schools")
    assert resp.status_code == 403


def test_school_admin_can_view_own_dashboard(client, school_admin):
    login(client, "schooladmin", "Admin@123")
    resp = client.get("/")
    assert resp.status_code == 200


def test_student_list_requires_login(client):
    resp = client.get("/students/", follow_redirects=False)
    assert resp.status_code in (302, 401)


def test_create_student_flow(client, school_admin, school):
    login(client, "schooladmin", "Admin@123")
    resp = client.get("/students/create")
    assert resp.status_code == 200

    resp = client.post("/students/create", data={
        "first_name": "Test", "last_name": "Student", "gender": "male",
        "guardian_name": "Guardian Name", "guardian_contact": "0800000000",
        "class_id": 0, "status": "active",
    }, follow_redirects=True)
    assert resp.status_code == 200
    assert b"created successfully" in resp.data.lower() or b"Test Student" in resp.data
