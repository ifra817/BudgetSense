"""
backend/routes/expenses.py
Merged: Ramlah Munir + Team Lead + Ifra

Ownership:
  Ramlah  — POST/PUT/DELETE (multipart + file upload), Budget routes
  Lead    — GET (list/single), pagination, filtering
  Ifra    — ExpenseItem model, validate(), to_dict_public()

Supports:
  ✅ user_id passed directly in request body / query params (no token auth)
  ✅ multipart/form-data (text fields + receipt image upload)
  ✅ application/json body
  ✅ Paginated, filtered GET /api/expenses
  ✅ Embedded items[] with quantity support
  ✅ Receipt image stored to disk; old image deleted on update
  ✅ Budget creation endpoint
"""

from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any, List
from bson import ObjectId
from bson.errors import InvalidId
from flask import Blueprint, jsonify, request, current_app

from db.connection import get_db, get_collection
from models.expense import Expense, ExpenseItem, Budget
from utils.validators import validate_budget_data
from utils.helpers import save_receipt_image, delete_receipt_image, parse_items_from_form

expenses_bp = Blueprint("expenses", __name__, url_prefix="/api/expenses")


# ─────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────────────────


def _get_expenses_collection():
    """Get the expenses collection from MongoDB."""
    return get_collection("expenses")


def _get_user_id(source: Dict[str, Any], field: str = "user_id") -> Tuple[Optional[ObjectId], Optional[Tuple]]:
    """
    Extract and validate user_id from a dict (form, JSON body, or query args).
    Returns (ObjectId, None) on success or (None, error_response) on failure.
    """
    raw = source.get(field)
    if not raw:
        return None, (jsonify({"error": "user_id is required"}), 400)
    if not ObjectId.is_valid(raw):
        return None, (jsonify({"error": "Invalid user_id format"}), 400)
    return ObjectId(str(raw)), None


def _parse_datetime(
    value: Optional[str], field_name: str
) -> Tuple[Optional[datetime], Optional[str]]:
    """
    Parse ISO string or datetime. 
    Returns (datetime, None) on success or (None, error_str) on failure.
    """
    if value in (None, ""):
        return None, None
    if isinstance(value, datetime):
        return value, None
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", None):
            try:
                if fmt:
                    return (
                        datetime.strptime(value.strip(), fmt).replace(tzinfo=timezone.utc),
                        None,
                    )
                else:
                    return (
                        datetime.fromisoformat(value.replace("Z", "+00:00")),
                        None,
                    )
            except ValueError:
                continue
    return None, f"{field_name} must be a valid ISO date string (YYYY-MM-DD or ISO 8601)"


def _parse_items_json(items_data: Any) -> Tuple[Optional[List[ExpenseItem]], Optional[str]]:
    """
    Parse items from a JSON list.
    Returns ([ExpenseItem, ...], None) or (None, error_str).
    """
    if not isinstance(items_data, list) or not items_data:
        return None, "At least one item is required"
    items = []
    for item_data in items_data:
        if not isinstance(item_data, dict):
            return None, "Each item must be an object"
        name = item_data.get("name")
        if not name:
            return None, "Item name is required"
        item = ExpenseItem(
            name=str(name),
            quantity=item_data.get("quantity", 1),
            price=item_data.get("price", 0),
        )
        is_valid, error = item.validate()
        if not is_valid:
            return None, error
        items.append(item)
    return items, None


def _parse_items_multipart(form: Any) -> Tuple[List[ExpenseItem], Optional[str]]:
    """Parse items from multipart form data."""
    raw = parse_items_from_form(form)
    items = []
    for r in raw:
        item = ExpenseItem(
            name=r["name"],
            quantity=r.get("quantity", 1),
            price=float(r["price"]),
        )
        is_valid, error = item.validate()
        if not is_valid:
            return [], error
        items.append(item)
    return items, None


def _calculate_total_amount(items: List[ExpenseItem]) -> float:
    """Calculate total amount from items."""
    return round(sum(item.get_total() for item in items), 2)


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/expenses  — List expenses with pagination + filters
# ─────────────────────────────────────────────────────────────────────────────


@expenses_bp.route("", methods=["GET"])
def get_expenses():
    """
    Get all expenses for a user with pagination and filters.
    Query params: user_id*, page, per_page, category,
                  start_date, end_date, min_amount, max_amount
    """
    user_id, error_response = _get_user_id(request.args)
    if error_response:
        return error_response

    try:
        page = max(int(request.args.get("page", 1)), 1)
        per_page = int(request.args.get("per_page", 10))
        if per_page < 1 or per_page > 100:
            raise ValueError
    except ValueError:
        return (
            jsonify({"error": "page and per_page must be valid integers (1-100)"}),
            400,
        )

    query: Dict[str, Any] = {"user_id": user_id}

    category = (request.args.get("category") or "").strip()
    if category:
        query["category"] = category

    amount_filter: Dict[str, float] = {}
    min_amount = request.args.get("min_amount")
    max_amount = request.args.get("max_amount")
    try:
        if min_amount is not None:
            amount_filter["$gte"] = float(min_amount)
        if max_amount is not None:
            amount_filter["$lte"] = float(max_amount)
    except (TypeError, ValueError):
        return (
            jsonify({"error": "min_amount and max_amount must be numbers"}),
            400,
        )

    if amount_filter:
    query["total_amount"] = amount_filter  # type: ignore



    start_date, start_error = _parse_datetime(request.args.get("start_date"), "start_date")
    if start_error:
        return jsonify({"error": start_error}), 400

    end_date, end_error = _parse_datetime(request.args.get("end_date"), "end_date")
    if end_error:
        return jsonify({"error": end_error}), 400

    if start_date or end_date:
        date_filter: dict = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date
        query["date"] = date_filter  # type: ignore

    col = _get_expenses_collection()
    total = col.count_documents(query)
    cursor = (
        col.find(query)
        .sort("date", -1)
        .skip((page - 1) * per_page)
        .limit(per_page)
    )
    expenses = [Expense.from_dict(e).to_dict_public() for e in cursor]

    return (
        jsonify(
            {
                "expenses": expenses,
                "pagination": {
                    "page": page,
                    "per_page": per_page,
                    "total": total,
                    "pages": (total + per_page - 1) // per_page if total else 0,
                },
                "filters": {
                    "category": category or None,
                    "start_date": request.args.get("start_date"),
                    "end_date": request.args.get("end_date"),
                    "min_amount": min_amount,
                    "max_amount": max_amount,
                },
            }
        ),
        200,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/expenses/<expense_id>
# ─────────────────────────────────────────────────────────────────────────────


@expenses_bp.route("/<expense_id>", methods=["GET"])
def get_expense(expense_id: str):
    """Get one expense by ID. Pass user_id as a query param."""
    user_id, error_response = _get_user_id(request.args)
    if error_response:
        return error_response

    if not ObjectId.is_valid(expense_id):
        return jsonify({"error": "Invalid expense ID"}), 400

    expense_data = _get_expenses_collection().find_one(
        {"_id": ObjectId(expense_id), "user_id": user_id}
    )
    if not expense_data:
        return jsonify({"error": "Expense not found"}), 404

    return (
        jsonify(
            {"expense": Expense.from_dict(expense_data).to_dict_public()}
        ),
        200,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  POST /api/expenses  — Create expense
# ─────────────────────────────────────────────────────────────────────────────


@expenses_bp.route("", methods=["POST"])
def create_expense():
    """
    Create a new expense.
    Accepts multipart/form-data (with optional receipt file) OR application/json.

    multipart fields : user_id*, title*, category*, date, total_amount or items[],
                       notes, receipt (file)
    JSON fields      : user_id*, title*, category*, date, items[] or total_amount,
                       notes, receipt_image (path string)
    """
    is_multipart = request.content_type and "multipart/form-data" in request.content_type

    if is_multipart:
        form = request.form
        user_id, error_response = _get_user_id(form)
        if error_response:
            return error_response
        title = form.get("title")
        category = form.get("category")
        notes = form.get("notes")
        total_amount_direct = form.get("total_amount")
        raw_date = form.get("date")
        items_data = None
    else:
        data = request.get_json(silent=True) or {}
        user_id, error_response = _get_user_id(data)
        if error_response:
            return error_response
        title = data.get("title")
        category = data.get("category")
        notes = data.get("notes")
        total_amount_direct = data.get("total_amount")
        raw_date = data.get("date")
        receipt_image = data.get("receipt_image")
        items_data = data.get("items")

    if not title or not category:
        return jsonify({"error": "title and category are required"}), 400

    expense_date, date_error = _parse_datetime(raw_date, "date")
    if date_error:
        return jsonify({"error": date_error}), 400

    # ── Handle receipt upload FIRST ───────────────────────────────────────
    receipt_image = None
    if is_multipart:
        uploaded_file = request.files.get("receipt")
        if uploaded_file and uploaded_file.filename:
            upload_result = save_receipt_image(uploaded_file, app=current_app)
            if not upload_result["success"]:
                return (
                    jsonify(
                        {"error": upload_result["error"], "field": "receipt"}
                    ),
                    400,
                )
            receipt_image = upload_result["filepath"]

    # ── Parse items ───────────────────────────────────────────────────────
    items: Optional[List[ExpenseItem]] = []

    if is_multipart:
        parsed_items, items_error = _parse_items_multipart(form)
        if items_error:
            return jsonify({"error": items_error, "field": "items"}), 400
        items = parsed_items if not items_error else []
    elif items_data:
        items, items_error = _parse_items_json(items_data)
        if items_error:
            return jsonify({"error": items_error}), 400

    if not items and total_amount_direct is None:
        return (
            jsonify(
                {"error": "Provide either items[] or a total_amount"}
            ),
            400,
        )

    # ── Build and validate Expense ────────────────────────────────────────
    expense = Expense(
        user_id=user_id,
        title=title,
        category=category,
        items=items,
        date=expense_date or datetime.now(timezone.utc),
        receipt_image=receipt_image,
        notes=notes,
        total_amount=float(total_amount_direct) if total_amount_direct and not items else None,
    )

    is_valid, validation_error = expense.validate()
    if not is_valid:
        return jsonify({"error": validation_error}), 400

    _get_expenses_collection().insert_one(expense.to_dict())
    return (
        jsonify(
            {
                "message": "Expense created successfully.",
                "expense": expense.to_dict_public(),
            }
        ),
        201,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  PUT /api/expenses/<expense_id>  — Update expense
# ─────────────────────────────────────────────────────────────────────────────


@expenses_bp.route("/<expense_id>", methods=["PUT"])
def update_expense(expense_id: str):
    """
    Update an existing expense.
    Accepts multipart/form-data OR application/json.
    user_id must be included in the body to confirm ownership.
    """
    is_multipart = request.content_type and "multipart/form-data" in request.content_type

    if is_multipart:
        form = request.form
        user_id, error_response = _get_user_id(form)
    else:
        data = request.get_json(silent=True) or {}
        user_id, error_response = _get_user_id(data)

    if error_response:
        return error_response

    if not ObjectId.is_valid(expense_id):
        return jsonify({"error": "Invalid expense ID"}), 400

    col = _get_expenses_collection()
    existing_data = col.find_one(
        {"_id": ObjectId(expense_id), "user_id": user_id}
    )
    if not existing_data:
        return jsonify({"error": "Expense not found"}), 404

    expense = Expense.from_dict(existing_data)

    if not is_multipart and not data:
        return jsonify({"error": "No data provided for update"}), 400

    source = form if is_multipart else data
    if "title" in source:
        expense.title = source["title"]
    if "category" in source:
        expense.category = source["category"]
    if "notes" in source:
        expense.notes = source["notes"]
    if "date" in source:
        parsed_date, date_error = _parse_datetime(source["date"], "date")
        if date_error:
            return jsonify({"error": date_error}), 400
        if parsed_date is not None:
            expense.date = parsed_date

    # Items update
    if is_multipart:
        parsed_items, items_error = _parse_items_multipart(form)
        if items_error:
            return jsonify({"error": items_error, "field": "items"}), 400
        if parsed_items:
            expense.items = parsed_items
            expense.total_amount = _calculate_total_amount(parsed_items)
    elif "items" in data:
        parsed_items, items_error = _parse_items_json(data["items"])
        if items_error:
            return jsonify({"error": items_error}), 400
        if parsed_items is not None:
            expense.items = parsed_items
            expense.total_amount = _calculate_total_amount(parsed_items)
    elif "total_amount" in source:
        expense.total_amount = float(source["total_amount"])

    if not is_multipart and "receipt_image" in data:
        expense.receipt_image = data["receipt_image"]

    # Receipt file replacement (multipart only)
    if is_multipart:
        uploaded_file = request.files.get("receipt")
        if uploaded_file and uploaded_file.filename:
            upload_result = save_receipt_image(uploaded_file, app=current_app)
            if not upload_result["success"]:
                return (
                    jsonify(
                        {"error": upload_result["error"], "field": "receipt"}
                    ),
                    400,
                )
            if existing_data.get("receipt_image"):
                delete_receipt_image(
                    existing_data["receipt_image"],
                    app=current_app,
                )
            expense.receipt_image = upload_result["filepath"]

    expense.updated_at = datetime.now(timezone.utc)

    is_valid, validation_error = expense.validate()
    if not is_valid:
        return jsonify({"error": validation_error}), 400

    updated_doc = expense.to_dict()
    updated_doc.pop("_id", None)
    updated_doc["user_id"] = user_id

    col.update_one(
        {"_id": ObjectId(expense_id), "user_id": user_id},
        {"$set": updated_doc},
    )

    refreshed = col.find_one(
        {"_id": ObjectId(expense_id), "user_id": user_id}
    )
    return (
        jsonify(
            {
                "message": "Expense updated successfully.",
                "expense": Expense.from_dict(refreshed).to_dict_public(),
            }
        ),
        200,
    )


# ─────────────────────────────────────────────────────────────────────────────
#  DELETE /api/expenses/<expense_id>
# ─────────────────────────────────────────────────────────────────────────────


@expenses_bp.route("/<expense_id>", methods=["DELETE"])
def delete_expense(expense_id: str):
    """
    Delete an expense and its receipt file.
    Pass user_id in the JSON body to confirm ownership.
    """
    data = request.get_json(silent=True) or {}
    user_id, error_response = _get_user_id(data)
    if error_response:
        return error_response

    if not ObjectId.is_valid(expense_id):
        return jsonify({"error": "Invalid expense ID"}), 400

    col = _get_expenses_collection()
    existing = col.find_one(
        {"_id": ObjectId(expense_id), "user_id": user_id}
    )
    if not existing:
        return jsonify({"error": "Expense not found"}), 404

    if existing.get("receipt_image"):
        delete_receipt_image(
            existing["receipt_image"],
            app=current_app,
        )

    col.delete_one({"_id": ObjectId(expense_id), "user_id": user_id})
    return jsonify({"message": "Expense deleted successfully."}), 200


# ─────────────────────────────────────────────────────────────────────────────
#  POST /api/expenses/budgets  — Create budget (Ramlah owns)
# ─────────────────────────────────────────────────────────────────────────────


@expenses_bp.route("/budgets", methods=["POST"])
def create_budget():
    """
    Create a new budget for a category.
    Accepts: application/json OR multipart/form-data
    Fields: user_id*, category*, limit* (> 0)
    """
    data = request.get_json(silent=True) or request.form.to_dict()

    validation = validate_budget_data(data)
    if not validation["valid"]:
        return (
            jsonify(
                {
                    "error": validation["error"],
                    "field": validation.get("field"),
                }
            ),
            400,
        )

    budget = Budget(
        user_id=data["user_id"],
        category=data["category"],
        limit=float(data["limit"]),
    )

    try:
        db = get_db()
        result = db[Budget.COLLECTION].insert_one(budget.to_dict())
        return (
            jsonify(
                {
                    "message": "Budget created successfully.",
                    "budget_id": str(result.inserted_id),
                }
            ),
            201,
        )

    except Exception as exc:
        current_app.logger.error(f"Failed to insert budget: {exc}")
        return (
            jsonify(
                {"error": "Server error. Could not save budget."}
            ),
            500,
        )
