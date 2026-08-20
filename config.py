import os
from datetime import timedelta

basedir = os.path.abspath(os.path.dirname(__file__))


def _database_url():
    url = os.environ.get("DATABASE_URL")
    if url and url.startswith("postgres://"):
        # SQLAlchemy 2.x requires the postgresql:// scheme
        url = url.replace("postgres://", "postgresql://", 1)
    return url


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    SQLALCHEMY_DATABASE_URI = _database_url() or (
        "sqlite:///" + os.path.join(basedir, "instance", "mtispms.db")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None

    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True") == "True"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

    ITEMS_PER_PAGE = int(os.environ.get("ITEMS_PER_PAGE", 20))

    # UPLOAD_FOLDER must always be an ABSOLUTE path. A relative value here
    # (e.g. the "app/static/uploads" shown in .env.example) used to be
    # passed straight through and resolved against the process's current
    # working directory at runtime - which differs between `flask run`,
    # gunicorn, and Render, and isn't guaranteed to exist or be writable.
    # That mismatch was the root cause of the student-photo-upload 500:
    # os.makedirs()/file.save() would throw in save_upload(), which had no
    # error handling, so the exception reached the user as a raw 500.
    _upload_folder_env = os.environ.get("UPLOAD_FOLDER")
    if _upload_folder_env and os.path.isabs(_upload_folder_env):
        UPLOAD_FOLDER = _upload_folder_env
    elif _upload_folder_env:
        UPLOAD_FOLDER = os.path.join(basedir, _upload_folder_env)
    else:
        UPLOAD_FOLDER = os.path.join(basedir, "app", "static", "uploads")

    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024))
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}
    ALLOWED_UPLOAD_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "pdf"}
    ALLOWED_EXCEL_EXTENSIONS = {"xlsx", "xls"}

    # Storage backend for uploaded files (student photos, user profile
    # photos, school logos, expense receipts):
    #   "local"    - writes to UPLOAD_FOLDER on this server's disk. Fast and
    #                simple, but on Render (and similar platforms) this disk
    #                is EPHEMERAL - uploads are wiped on every
    #                restart/redeploy. Fine for local development only.
    #   "database" - stores file bytes as rows in PostgreSQL (see
    #                app/models/uploaded_file.py). Genuinely persists across
    #                Render restarts/redeploys with zero new credentials or
    #                paid services, since it reuses DATABASE_URL. This is
    #                what actually fixes uploaded assets (e.g. the school
    #                logo) "disappearing" after a restart.
    # Add a real object-storage backend (S3/Cloudinary/etc.) later by
    # implementing the StorageBackend interface in
    # app/services/storage_service.py and adding a branch here - no other
    # code needs to change.
    STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local")


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    # Render's filesystem is ephemeral, so "local" disk storage silently
    # loses every uploaded file (school logos, student photos, ...) on the
    # next restart/redeploy - this was the direct cause of the reported
    # "logo disappears" bug. Default production to the database-backed
    # backend instead, which actually persists; still overridable via the
    # STORAGE_BACKEND env var if a real object-storage backend is wired up
    # later.
    STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "database")


class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}
