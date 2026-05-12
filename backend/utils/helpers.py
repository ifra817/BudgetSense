"""
backend/utils/helpers.py
Ramlah Munir — Receipt File Upload Handler

Responsibilities:
  - Accept an uploaded receipt image from a multipart/form-data request
  - Validate the file extension (delegates to validators.py)
  - Generate a collision-proof unique filename using UUID4
  - Save the file to the configured upload folder
  - Return the relative path to store in MongoDB

Security principles applied:
  - Original filename is NEVER used on disk (prevents path traversal)
  - Extension is extracted safely from the original name after validation
  - Only whitelisted extensions are accepted
"""

import os
import uuid
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage

from utils.validators import validate_file_extension, ALLOWED_IMAGE_EXTENSIONS


# ─────────────────────────────────────────────
#  UPLOAD FOLDER (fallback if app not configured)
# ─────────────────────────────────────────────

DEFAULT_UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")


def get_upload_folder(app=None) -> str:
    """
    Return the upload directory path.
    Reads UPLOAD_FOLDER from the Flask app config if available,
    otherwise falls back to the project-level 'uploads/' directory.
    Creates the directory if it doesn't exist.
    """
    if app and app.config.get("UPLOAD_FOLDER"):
        folder = app.config["UPLOAD_FOLDER"]
    else:
        folder = DEFAULT_UPLOAD_FOLDER

    os.makedirs(folder, exist_ok=True)
    return folder


# ─────────────────────────────────────────────
#  CORE UPLOAD FUNCTION
# ─────────────────────────────────────────────

def save_receipt_image(file: FileStorage, app=None) -> dict:
    """
    Validate and save an uploaded receipt image.

    Args:
        file   : werkzeug FileStorage object from request.files
        app    : Flask app instance (used to read UPLOAD_FOLDER config)

    Returns on success:
        {
            "success":   True,
            "filename":  "a3f1c2d4-...-uuid.jpg",      <- unique filename on disk
            "filepath":  "uploads/a3f1c2d4-...-uuid.jpg"  <- stored in MongoDB
        }

    Returns on failure:
        {
            "success": False,
            "error":   "descriptive error message"
        }

    Security:
        - The original filename is NEVER written to disk.
        - A UUID4-based name is generated to prevent collisions and
          path traversal attacks.
        - Only whitelisted extensions pass validation.
    """

    # ── 1. Check a file was actually submitted ───
    if file is None or file.filename == "":
        return {"success": False, "error": "No file was uploaded."}

    original_filename = file.filename

    # ── 2. Validate extension ────────────────────
    ext_check = validate_file_extension(original_filename)
    if not ext_check["valid"]:
        return {"success": False, "error": ext_check["error"]}

    # ── 3. Extract the extension safely ─────────
    #    secure_filename sanitises the name; we only use it to get the ext.
    safe_original = secure_filename(original_filename)
    extension = safe_original.rsplit(".", 1)[1].lower()

    # ── 4. Generate a unique filename ────────────
    #    UUID4 is random — no two uploads will ever collide.
    unique_filename = f"{uuid.uuid4().hex}.{extension}"

    # ── 5. Build the full disk path and save ─────
    upload_folder = get_upload_folder(app)
    full_path     = os.path.join(upload_folder, unique_filename)

    try:
        file.save(full_path)
    except OSError as exc:
        return {"success": False, "error": f"Could not save file: {exc}"}

    # ── 6. Return the relative path for MongoDB ──
    #    Store a relative path (not an absolute OS path) so the DB record
    #    stays portable across environments.
    relative_path = os.path.join("uploads", unique_filename).replace("\\", "/")

    return {
        "success":  True,
        "filename": unique_filename,
        "filepath": relative_path,       # <- this value goes into expense.receipt_image
    }


# ─────────────────────────────────────────────
#  HELPER: DELETE A STORED RECEIPT
# ─────────────────────────────────────────────

def delete_receipt_image(filepath: str, app=None) -> bool:
    """
    Delete a previously saved receipt image from disk.

    Args:
        filepath : relative path stored in MongoDB (e.g. "uploads/abc123.jpg")
        app      : Flask app instance

    Returns:
        True if deleted successfully, False otherwise.
    """
    if not filepath:
        return False

    # Resolve the absolute path from the project root
    project_root  = os.path.join(os.path.dirname(__file__), "..", "..")
    absolute_path = os.path.normpath(os.path.join(project_root, filepath))

    # Safety check: ensure the resolved path is inside the uploads folder
    upload_folder = os.path.normpath(get_upload_folder(app))
    if not absolute_path.startswith(upload_folder):
        # Potential path traversal — refuse to delete
        return False

    if os.path.isfile(absolute_path):
        try:
            os.remove(absolute_path)
            return True
        except OSError:
            return False

    return False


# ─────────────────────────────────────────────
#  HELPER: PARSE ITEMS FROM FORM DATA
# ─────────────────────────────────────────────

def parse_items_from_form(form) -> list:
    """
    Parse the embedded items[] array from multipart/form-data.

    HTML forms cannot send nested JSON natively, so the frontend sends
    items using indexed field names:
        items[0][name]  = "Milk"
        items[0][price] = "300"
        items[1][name]  = "Bread"
        items[1][price] = "200"

    This function collects those fields into a list of dicts that can be
    validated by validate_items() and converted to LineItem objects.

    Returns:
        [ {"name": "Milk", "price": 300.0}, ... ]
    """
    items = []
    index = 0

    while True:
        name  = form.get(f"items[{index}][name]")
        price = form.get(f"items[{index}][price]")

        # Stop when no more indexed fields are found
        if name is None and price is None:
            break

        if name is not None and price is not None:
            try:
                items.append({"name": name.strip(), "price": float(price)})
            except (ValueError, TypeError):
                items.append({"name": name.strip(), "price": price})  # let validator catch it

        index += 1

    return items