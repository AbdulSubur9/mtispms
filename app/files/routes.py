from flask import abort, Response
from app.files import files_bp
from app.models import UploadedFile


@files_bp.route("/files/<reference_key>")
def serve_file(reference_key):
    """Serves a file stored by the database storage backend (see
    app/services/storage_service.py:DatabaseStorageBackend). Deliberately
    unauthenticated, matching the existing behavior of the local backend's
    files (served straight from /static/uploads/... with no auth check
    today) - access relies on the reference key being an unguessable
    random UUID, the same trust model already in place. If a future
    requirement needs per-file access control (e.g. private documents),
    add an explicit check here rather than assuming this endpoint is safe
    for anything more sensitive than the branding/photo assets it serves
    today.
    """
    record = UploadedFile.query.filter_by(reference_key=reference_key).first()
    if not record:
        abort(404)

    response = Response(record.data, mimetype=record.content_type or "application/octet-stream")
    # Long-lived caching is safe: each upload gets a brand-new random key
    # (see save()), so a given URL's content never changes.
    response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
    return response
