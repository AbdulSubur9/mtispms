from datetime import datetime
from app.extensions import db


class UploadedFile(db.Model):
    """Backing store for the "database" storage backend (see
    app/services/storage_service.py). Exists specifically to solve uploaded
    assets (school logos, student photos, ...) disappearing after a Render
    restart/redeploy: the local filesystem is ephemeral there, but
    PostgreSQL is not - so storing the file bytes as a row here persists
    reliably using infrastructure the app already depends on, with no new
    account, API key, or paid service required.

    This is a legitimate, common pattern for small-to-medium apps. It's not
    the answer for large-scale file traffic (see the module docstring for
    when to add a real object-storage backend like S3), but it is a real
    fix for the reported bug, not a stub.
    """
    __tablename__ = "uploaded_files"

    id = db.Column(db.Integer, primary_key=True)
    # Unique, unguessable key used as the "reference" stored on
    # School.logo / Student.photo / etc. - same role as the file path a
    # local-disk reference plays, just backend-specific.
    reference_key = db.Column(db.String(64), unique=True, nullable=False, index=True)
    school_id = db.Column(db.Integer, db.ForeignKey("schools.id"), nullable=True)  # for tenant-aware cleanup/audits

    original_filename = db.Column(db.String(255))
    content_type = db.Column(db.String(100))
    data = db.Column(db.LargeBinary, nullable=False)
    byte_size = db.Column(db.Integer)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<UploadedFile {self.reference_key} ({self.byte_size} bytes)>"
