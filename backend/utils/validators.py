"""
backend/utils/validators.py
Ramlah Munir — Input Validation & Data Integrity

ADS Course Concepts Demonstrated:
  ✅ Data Validation     — enforce correct types and positive amounts BEFORE
                           any document reaches MongoDB
  ✅ Data Integrity      — validate embedded items[] sub-documents too
  ✅ Schema Enforcement  — Python-layer schema rules (MongoDB is schemaless;
                           we enforce rules here to keep data clean)
"""

from datetime import datetime
from bson import ObjectId


# ─────────────────────────────────────────────
#  CONSTANTS
# ─────────────────────────────────────────────

VALID_CATEGORIES = [
    "Dining", "Education", "Entertainment", "Food", "Groceries",
    "Healthcare", "Other", "Shopping", "Sports", "Transport",
    "Travel", "Utilities"
]

ALLOWED_IMAGE_EXTENSIONS = {"jpg", "jpeg", "png", "gif", "webp"}

MAX_TITLE_LENGTH    = 100
MAX_NOTES_LENGTH    = 500
MAX_ITEM_NAME_LEN   = 100
MAX_ITEMS_PER_DOC   = 50    # guard against absurdly large embedded arrays


# ─────────────────────────────────────────────
#  HELPER UTILITIES
# ─────────────────────────────────────────────

def _err(field: str, message: str) -> dict:
    """Return a standardised error dict."""
    return {"valid": False, "field": field, "error": message}


def _ok() -> dict:
    return {"valid": True}


# ─────────────────────────────────────────────
#  INDIVIDUAL FIELD VALIDATORS
# ─────────────────────────────────────────────

def validate_amount(value, field_name: str = "amount") -> dict:
    """
    Amount must be a positive number.
    Rejects: negative values, zero, strings, None.
    """
    if value is None:
        return _err(field_name, f"{field_name} is required.")
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return _err(field_name, f"{field_name} must be a number.")
    if amount <= 0:
        return _err(field_name, f"{field_name} must be greater than 0.")
    return _ok()


def validate_category(value) -> dict:
    """Category must be one of the allowed strings."""
    if not value or not isinstance(value, str):
        return _err("category", "Category is required.")
    if value.strip() not in VALID_CATEGORIES:
        return _err(
            "category",
            f"Invalid category '{value}'. "
            f"Must be one of: {', '.join(VALID_CATEGORIES)}."
        )
    return _ok()


def validate_title(value) -> dict:
    """Title must be a non-empty string within the max length."""
    if not value or not isinstance(value, str) or not value.strip():
        return _err("title", "Title is required.")
    if len(value.strip()) > MAX_TITLE_LENGTH:
        return _err("title", f"Title must be {MAX_TITLE_LENGTH} characters or fewer.")
    return _ok()


def validate_date(value) -> dict:
    """
    Date must be a non-empty string parseable as YYYY-MM-DD,
    or already a datetime object.
    """
    if value is None:
        return _err("date", "Date is required.")
    if isinstance(value, datetime):
        return _ok()
    if not isinstance(value, str) or not value.strip():
        return _err("date", "Date must be a string in YYYY-MM-DD format.")
    try:
        datetime.strptime(value.strip(), "%Y-%m-%d")
    except ValueError:
        return _err("date", "Date must be in YYYY-MM-DD format (e.g. 2026-05-10).")
    return _ok()


def validate_user_id(value) -> dict:
    """user_id must be a valid MongoDB ObjectId string."""
    if not value:
        return _err("user_id", "user_id is required.")
    try:
        ObjectId(str(value))
    except Exception:
        return _err("user_id", "user_id must be a valid MongoDB ObjectId.")
    return _ok()


def validate_notes(value) -> dict:
    """Notes are optional but must not exceed max length if provided."""
    if value is None:
        return _ok()
    if not isinstance(value, str):
        return _err("notes", "Notes must be a string.")
    if len(value) > MAX_NOTES_LENGTH:
        return _err("notes", f"Notes must be {MAX_NOTES_LENGTH} characters or fewer.")
    return _ok()


# ─────────────────────────────────────────────
#  EMBEDDED ITEMS VALIDATOR
# ─────────────────────────────────────────────

def validate_items(items) -> dict:
    """
    Validate the embedded 'items' array (LineItem sub-documents).

    ADS note: we validate embedded sub-documents just as rigorously as
    top-level fields — bad data in nested arrays is harder to detect later.

    Each item must have:
      - 'name'  : non-empty string
      - 'price' : positive number
    """
    if items is None:
        return _ok()   # items are optional

    if not isinstance(items, list):
        return _err("items", "Items must be a list.")

    if len(items) > MAX_ITEMS_PER_DOC:
        return _err("items", f"Cannot have more than {MAX_ITEMS_PER_DOC} items per expense.")

    for idx, item in enumerate(items):
        # Each item must be a dict
        if not isinstance(item, dict):
            return _err("items", f"Item at index {idx} must be an object.")

        # Validate name
        name = item.get("name")
        if not name or not isinstance(name, str) or not name.strip():
            return _err("items", f"Item {idx + 1}: 'name' is required and must be a non-empty string.")
        if len(name.strip()) > MAX_ITEM_NAME_LEN:
            return _err("items", f"Item {idx + 1}: name must be {MAX_ITEM_NAME_LEN} characters or fewer.")

        # Validate price
        price = item.get("price")
        result = validate_amount(price, field_name=f"items[{idx}].price")
        if not result["valid"]:
            return _err("items", f"Item {idx + 1} '{name}': price must be a positive number.")

    return _ok()


# ─────────────────────────────────────────────
#  FULL DOCUMENT VALIDATORS
# ─────────────────────────────────────────────

def validate_expense_data(data: dict) -> dict:
    """
    Validate all fields for a new or updated expense document.

    Returns:
        {"valid": True}
        or
        {"valid": False, "field": str, "error": str}

    Usage in a route:
        result = validate_expense_data(request.form)
        if not result["valid"]:
            return jsonify({"error": result["error"]}), 400
    """
    checks = [
        validate_user_id(data.get("user_id")),
        validate_title(data.get("title")),
        validate_category(data.get("category")),
        validate_amount(data.get("total_amount"), "total_amount"),
        validate_date(data.get("date")),
        validate_notes(data.get("notes")),
        validate_items(data.get("items")),   # validates embedded sub-documents
    ]

    for result in checks:
        if not result["valid"]:
            return result   # return the first failure found

    return _ok()


def validate_budget_data(data: dict) -> dict:
    """
    Validate fields for a new or updated budget document.

    Returns:
        {"valid": True}
        or
        {"valid": False, "field": str, "error": str}
    """
    checks = [
        validate_user_id(data.get("user_id")),
        validate_category(data.get("category")),
        validate_amount(data.get("limit"), "limit"),
    ]

    for result in checks:
        if not result["valid"]:
            return result

    return _ok()


# ─────────────────────────────────────────────
#  FILE UPLOAD VALIDATOR
# ─────────────────────────────────────────────

def validate_file_extension(filename: str) -> dict:
    """
    Check that an uploaded file has an allowed image extension.

    Allowed: jpg, jpeg, png, gif, webp
    """
    if not filename or "." not in filename:
        return _err("receipt_image", "File must have a valid extension (jpg, jpeg, png, gif, webp).")

    ext = filename.rsplit(".", 1)[1].lower()
    if ext not in ALLOWED_IMAGE_EXTENSIONS:
        return _err(
            "receipt_image",
            f"File type '.{ext}' is not allowed. "
            f"Use: {', '.join(sorted(ALLOWED_IMAGE_EXTENSIONS))}."
        )
    return _ok()