"""
Upload storage architecture.

Everything that saves a user-uploaded file (student photos, user profile
photos, school logos, expense receipts, application documents) goes through
`save_image()` / `delete_file()` here instead of touching the filesystem
directly. That gives us three things in one place:

1. Proper error handling and logging - the original bug (student photo
   upload causing a raw 500) happened because file-saving code had no
   try/except at all, so any OSError/PermissionError from a bad path
   reached the user as "Internal Server Error." Every failure here is
   caught, logged with full context, and reported back as a
   `StorageError` with a friendly message the calling view can flash.
2. Real image validation - Pillow actually opens and verifies the file
   is a genuine image (not just an allowed extension), which blocks a
   disguised malicious file from ever being written to disk.
3. A pluggable backend so today's "local disk" storage can become S3 or
   Cloudinary later WITHOUT changing any calling code. Every route in the
   app calls the same three functions (`save_image`, `delete_file`,
   `resolve_url`) regardless of backend.

IMPORTANT (Render): the local backend writes to this server's own disk,
which is EPHEMERAL on Render - files do not survive a redeploy or dyno
restart. It works fine for development and low-stakes/staging use, but
production should set STORAGE_BACKEND to a real object-storage backend
once one is implemented (see `S3StorageBackend` stub below for the
intended extension point).
"""
import os
import uuid
import logging
from abc import ABC, abstractmethod

from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

logger = logging.getLogger("mtispms.storage")


class StorageError(Exception):
    """Raised for any upload failure. `.user_message` is always safe to
    show directly to the end user; the original exception (if any) is
    logged server-side but never exposed."""

    def __init__(self, user_message, original_exc=None):
        super().__init__(user_message)
        self.user_message = user_message
        self.original_exc = original_exc


class StorageBackend(ABC):
    """Interface every storage backend implements. Add a new backend (e.g.
    S3StorageBackend, CloudinaryStorageBackend) by implementing these three
    methods and switching STORAGE_BACKEND - no calling code changes."""

    @abstractmethod
    def save(self, file_storage: FileStorage, subfolder: str) -> str:
        """Persist the file, return a backend-relative reference (stored in
        the database) that `url_for_reference()` can later resolve."""

    @abstractmethod
    def delete(self, reference: str) -> None:
        """Delete a previously-saved file. Must not raise if the file is
        already missing - deletion is best-effort cleanup, not a
        transaction that should fail the calling request."""

    @abstractmethod
    def url_for_reference(self, reference: str) -> str:
        """Return a browser-loadable URL for a stored reference."""

    @abstractmethod
    def read(self, reference: str) -> bytes | None:
        """Return the raw bytes for a stored reference, or None if it
        can't be found. Needed anywhere a file's *content* is required
        directly - e.g. embedding a school logo or student photo into a
        generated PDF, which needs actual bytes, not a URL a browser would
        fetch."""


class LocalStorageBackend(StorageBackend):
    """Saves to UPLOAD_FOLDER on local disk, served via Flask's /static/
    route. See the module docstring's Render caveat."""

    def save(self, file_storage: FileStorage, subfolder: str) -> str:
        filename = secure_filename(file_storage.filename)
        ext = filename.rsplit(".", 1)[1].lower() if "." in filename else ""
        unique_name = f"{uuid.uuid4().hex}.{ext}" if ext else uuid.uuid4().hex

        folder = os.path.join(current_app.config["UPLOAD_FOLDER"], subfolder)
        try:
            os.makedirs(folder, exist_ok=True)
            path = os.path.join(folder, unique_name)
            file_storage.save(path)
        except (OSError, PermissionError) as exc:
            logger.error("Failed to save upload to %s: %s", folder, exc, exc_info=True)
            raise StorageError(
                "The file could not be saved due to a server storage issue. "
                "Please try again, or contact support if this keeps happening.",
                original_exc=exc,
            ) from exc

        return f"uploads/{subfolder}/{unique_name}"

    def delete(self, reference: str) -> None:
        if not reference or not reference.startswith("uploads/"):
            return
        try:
            static_folder = current_app.static_folder
            abs_path = os.path.join(static_folder, reference)
            if os.path.isfile(abs_path):
                os.remove(abs_path)
        except OSError as exc:
            # Best-effort cleanup - log it, but never fail the calling
            # request just because an old file couldn't be removed.
            logger.warning("Failed to delete old upload %s: %s", reference, exc)

    def url_for_reference(self, reference: str) -> str:
        from flask import url_for
        return url_for("static", filename=reference)

    def read(self, reference: str) -> bytes | None:
        if not reference or not reference.startswith("uploads/"):
            return None
        try:
            abs_path = os.path.join(current_app.static_folder, reference)
            if not os.path.isfile(abs_path):
                return None
            with open(abs_path, "rb") as f:
                return f.read()
        except OSError as exc:
            logger.warning("Failed to read upload %s: %s", reference, exc)
            return None
    """Stores file bytes as rows in PostgreSQL instead of local disk. This
    is what actually fixes files "disappearing" on Render: the local
    filesystem there is wiped on every redeploy/restart, but the database
    is not. Requires no new account, credential, or paid service - it uses
    the same DATABASE_URL the app already depends on.

    Trade-off: not meant for high file-volume/large-file production loads
    (that's what a real object-storage backend like S3 is for - see the
    module docstring). For a Madrasah's logo + a few hundred/thousand
    student photos, this is a perfectly reasonable, genuinely-persistent
    default.
    """

    def save(self, file_storage: FileStorage, subfolder: str) -> str:
        from app.models.uploaded_file import UploadedFile
        from app.extensions import db as _db

        data = file_storage.read()
        if not data:
            raise StorageError("The uploaded file appears to be empty. Please choose a different file.")

        key = uuid.uuid4().hex
        record = UploadedFile(
            reference_key=key,
            original_filename=secure_filename(file_storage.filename),
            content_type=file_storage.mimetype or "application/octet-stream",
            data=data,
            byte_size=len(data),
        )
        try:
            _db.session.add(record)
            _db.session.flush()  # assigns record.id, surfaces IntegrityError early, but does NOT commit -
            # stays part of the caller's existing transaction so the file
            # and the record referencing it (e.g. School.logo) commit or
            # roll back together atomically, never getting out of sync.
        except Exception as exc:
            _db.session.rollback()
            logger.error("Failed to save upload to database: %s", exc, exc_info=True)
            raise StorageError(
                "The file could not be saved due to a server storage issue. "
                "Please try again, or contact support if this keeps happening.",
                original_exc=exc,
            ) from exc

        # subfolder isn't structurally needed for DB storage (no directory
        # tree to manage), but is kept in the reference for readability /
        # consistency with the local backend's reference format.
        return f"db:{subfolder}:{key}"

    def delete(self, reference: str) -> None:
        from app.models.uploaded_file import UploadedFile
        from app.extensions import db as _db

        key = self._key_from_reference(reference)
        if not key:
            return
        record = UploadedFile.query.filter_by(reference_key=key).first()
        if record:
            try:
                _db.session.delete(record)
                _db.session.flush()
            except Exception as exc:
                _db.session.rollback()
                logger.warning("Failed to delete uploaded file %s: %s", reference, exc)

    def url_for_reference(self, reference: str) -> str:
        from flask import url_for
        key = self._key_from_reference(reference)
        if not key:
            return ""
        return url_for("files.serve_file", reference_key=key)

    def read(self, reference: str) -> bytes | None:
        from app.models.uploaded_file import UploadedFile
        key = self._key_from_reference(reference)
        if not key:
            return None
        record = UploadedFile.query.filter_by(reference_key=key).first()
        return record.data if record else None

    @staticmethod
    def _key_from_reference(reference: str):
        if not reference or not reference.startswith("db:"):
            return None
        return reference.rsplit(":", 1)[-1]


def _get_backend() -> StorageBackend:
    backend_name = current_app.config.get("STORAGE_BACKEND", "local")
    if backend_name == "local":
        return LocalStorageBackend()
    if backend_name == "database":
        return DatabaseStorageBackend()
    # Extension point for future backends, e.g.:
    #   if backend_name == "s3": return S3StorageBackend()
    #   if backend_name == "cloudinary": return CloudinaryStorageBackend()
    logger.warning("Unknown STORAGE_BACKEND '%s', falling back to local", backend_name)
    return LocalStorageBackend()


def _is_real_upload(file_storage) -> bool:
    """True only for an actual submitted file. Guards against a well-known
    Flask-WTF/WTForms gotcha that was the real root cause of two separate
    "Internal Server Error" reports (editing a student who already has a
    photo, and saving school branding settings without re-selecting the
    logo):

    When a form is built with `SomeForm(obj=existing_record)` (e.g.
    `StudentForm(obj=student)`, `BrandingForm(obj=school)`), WTForms calls
    `process_data()` on every field, which sets the FileField's `.data` to
    whatever the stored DB value is - a plain STRING path like
    "uploads/students/xyz.jpg", not a file.

    On submit, Werkzeug's FileStorage defines `__bool__` as
    `bool(self.filename)`, so an empty "no file chosen" file input is
    FALSY. Flask-WTF's FileField.process_formdata only overwrites `.data`
    when it finds a truthy FileStorage in the submitted data - so when no
    new file is chosen, `.data` is never reset and silently keeps the
    leftover STRING from the `obj=` population. Code that then does
    `file_storage.filename` (expecting a FileStorage) crashes with
    `AttributeError: 'str' object has no attribute 'filename'` - uncaught,
    because it isn't a StorageError, so it becomes a raw 500.

    This is exactly the scenario of "edit a student who already has a
    photo, without changing the photo" or "update branding text without
    re-uploading the logo" - both extremely common, everyday actions.
    """
    return isinstance(file_storage, FileStorage) and bool(file_storage.filename)


def validate_image(file_storage: FileStorage, max_bytes=None):
    """Verify the upload is actually a real, non-corrupt image (not just an
    allowed-looking extension) and within size limits. Raises StorageError
    with a friendly message on any problem. Call this BEFORE save_image()."""
    if not _is_real_upload(file_storage):
        return  # nothing to validate - caller treats this as "no file chosen"

    allowed_ext = current_app.config.get("ALLOWED_IMAGE_EXTENSIONS", {"png", "jpg", "jpeg", "gif"})
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in allowed_ext:
        raise StorageError(f"Unsupported file type. Allowed image types: {', '.join(sorted(allowed_ext))}.")

    max_bytes = max_bytes or current_app.config.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024)
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > max_bytes:
        raise StorageError(f"That image is too large. Maximum size is {max_bytes // (1024 * 1024)}MB.")
    if size == 0:
        raise StorageError("That file appears to be empty. Please choose a different image.")

    try:
        from PIL import Image, UnidentifiedImageError
        file_storage.stream.seek(0)
        with Image.open(file_storage.stream) as img:
            img.verify()  # raises if the bytes aren't actually a valid image
        file_storage.stream.seek(0)
    except ImportError:
        # Pillow isn't installed - skip deep validation rather than crash;
        # extension + size checks above still apply.
        logger.warning("Pillow not available - skipping deep image content validation")
    except UnidentifiedImageError as exc:
        raise StorageError(
            "That file doesn't look like a valid image. Please upload a real PNG, JPG, or GIF."
        ) from exc
    except Exception as exc:  # noqa: BLE001 - any other Pillow failure is also a validation failure
        logger.warning("Image validation error: %s", exc)
        raise StorageError("That image could not be processed. Please try a different file.") from exc


def save_image(file_storage: FileStorage, subfolder: str, old_reference: str = None) -> str | None:
    """Validate and save an image upload, deleting the previous file (if
    any) once the new one is safely written. Returns the new stored
    reference, or None if no file was actually chosen (this is not an
    error - it just means "keep the existing image"/"no image provided").

    Raises StorageError (safe to flash directly to the user) on any
    validation or storage failure - callers should catch this and
    re-render their form rather than letting it propagate to a 500.
    """
    if not _is_real_upload(file_storage):
        return None

    validate_image(file_storage)
    backend = _get_backend()
    new_reference = backend.save(file_storage, subfolder)

    if old_reference:
        # Route the cleanup by the OLD reference's own format, not the
        # (possibly different) backend the NEW file was just saved to -
        # otherwise switching STORAGE_BACKEND would silently stop cleaning
        # up old files saved under the previous backend.
        _backend_for_reference(old_reference).delete(old_reference)

    return new_reference


def save_document(file_storage: FileStorage, subfolder: str, allowed_extensions=None, max_bytes=None) -> str | None:
    """Like save_image(), but for uploads that aren't necessarily images
    (e.g. a PDF expense receipt). Validates extension and size, but does
    NOT run Pillow's image-content verification. Returns None if no file
    was chosen; raises StorageError (safe to flash) on any problem."""
    if not _is_real_upload(file_storage):
        return None

    allowed_extensions = allowed_extensions or current_app.config.get(
        "ALLOWED_UPLOAD_EXTENSIONS", {"png", "jpg", "jpeg", "gif", "pdf"}
    )
    ext = file_storage.filename.rsplit(".", 1)[-1].lower() if "." in file_storage.filename else ""
    if ext not in allowed_extensions:
        raise StorageError(f"Unsupported file type. Allowed types: {', '.join(sorted(allowed_extensions))}.")

    max_bytes = max_bytes or current_app.config.get("MAX_CONTENT_LENGTH", 5 * 1024 * 1024)
    file_storage.stream.seek(0, os.SEEK_END)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > max_bytes:
        raise StorageError(f"That file is too large. Maximum size is {max_bytes // (1024 * 1024)}MB.")
    if size == 0:
        raise StorageError("That file appears to be empty. Please choose a different file.")

    return _get_backend().save(file_storage, subfolder)


def _backend_for_reference(reference: str) -> StorageBackend:
    """Resolve which backend actually owns a given reference, based on the
    reference's own format - NOT the currently-configured default.

    This matters because STORAGE_BACKEND can change over the app's
    lifetime (e.g. this fix defaults production to "database" going
    forward). Without this, flipping that default would silently break
    every already-uploaded file saved under the old backend: a
    database-backend reference always starts with "db:", so a legacy
    local-disk reference like "uploads/branding/xyz.png" would otherwise
    be misrouted to DatabaseStorageBackend and fail to resolve/delete.
    Existing files keep working under whichever backend actually stored
    them; only NEW saves use the currently-configured default.
    """
    if reference and reference.startswith("db:"):
        return DatabaseStorageBackend()
    return LocalStorageBackend()


def delete_file(reference: str) -> None:
    if not reference:
        return
    _backend_for_reference(reference).delete(reference)


def resolve_url(reference: str) -> str | None:
    if not reference:
        return None
    return _backend_for_reference(reference).url_for_reference(reference)


def read_file_bytes(reference: str) -> bytes | None:
    """Return the raw bytes of a stored file, for callers that need actual
    content rather than a URL (e.g. embedding a logo/photo into a
    generated PDF). Routes by the reference's own format, same as
    resolve_url()/delete_file()."""
    if not reference:
        return None
    return _backend_for_reference(reference).read(reference)
