import pytest
from app import create_app
from app.extensions import db
from app.models import School, User
from app.models.user import Role


@pytest.fixture()
def app():
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def school(app):
    s = School(name="Test Madrassa", code="TST001")
    db.session.add(s)
    db.session.commit()
    return s


@pytest.fixture()
def super_admin(app):
    u = User(username="admin", email="admin@test.com", first_name="Super", last_name="Admin", role=Role.SUPER_ADMIN)
    u.set_password("admin123")
    db.session.add(u)
    db.session.commit()
    return u


@pytest.fixture()
def school_admin(app, school):
    u = User(username="schooladmin", email="schooladmin@test.com", first_name="School", last_name="Admin",
             role=Role.SCHOOL_ADMIN, school_id=school.id)
    u.set_password("Admin@123")
    db.session.add(u)
    db.session.commit()
    return u


def login(client, username, password):
    return client.post("/auth/login", data={"username": username, "password": password}, follow_redirects=True)
