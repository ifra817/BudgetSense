"""
Expense CRUD routes for BudgetSense.

Routes:
- GET /api/expenses
- POST /api/expenses
- GET /api/expenses/<expense_id>
- PUT /api/expenses/<expense_id>
- DELETE /api/expenses/<expense_id>

Authentication for all routes is done using either:
- Authorization: Bearer <signed_token>
"""

from datetime import datetime

from bson.objectid import ObjectId
from flask import Blueprint, current_app, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from db.connection import get_collection
from models.expense import Expense, ExpenseItem

expenses_bp = Blueprint("expenses", __name__, url_prefix="/api/expenses")
TOKEN_SALT = "budgetsense-auth-token"


def _get_expenses_collection():
    return get_collection("expenses")


def _get_users_collection():
    return get_collection("users")


def _get_token_serializer():
    return URLSafeTimedSerializer(current_app.config.get("SECRET_KEY", "dev-secret-key-change-in-production"))


def _decode_access_token(token):
    try:
        payload = _get_token_serializer().loads(token, salt=TOKEN_SALT, max_age=86400)
    except (BadSignature, SignatureExpired):
        return None

    user_id = payload.get("user_id") if isinstance(payload, dict) else None
    if not user_id:
        return None

    return str(user_id)


def _get_user_id_from_request():
    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()
        return _decode_access_token(token)

    return None


def _get_current_user_id():
    user_id = _get_user_id_from_request()
    if not user_id:
        return None, (jsonify({"error": "Authentication required"}), 401)

    if not ObjectId.is_valid(user_id):
        return None, (jsonify({"error": "Invalid user ID"}), 401)

    user_object_id = ObjectId(user_id)
    user_exists = _get_users_collection().find_one({"_id": user_object_id})
    if not user_exists:
        return None, (jsonify({"error": "User not found"}), 404)

    return user_object_id, None


def _parse_datetime(value, field_name):
    if value in (None, ""):
        return None, None

    if isinstance(value, datetime):
        return value, None

    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")), None
        except ValueError:
            return None, f"{field_name} must be a valid ISO date string"

    return None, f"{field_name} must be a valid ISO date string"


def _parse_items(items_data):
    if not isinstance(items_data, list) or not items_data:
        return None, "At least one item is required"

    items = []
    for item_data in items_data:
        if not isinstance(item_data, dict):
            return None, "Each item must be an object"

        name = item_data.get("name")
        quantity = item_data.get("quantity", 1)
        price = item_data.get("price", 0)

        item = ExpenseItem(name=name, quantity=quantity, price=price)
        is_valid, error = item.validate()
        if not is_valid:
            return None, error
        items.append(item)

    return items, None


def _calculate_total_amount(items):
    total = 0
    for item in items:
        if isinstance(item, ExpenseItem):
            total += item.get_total()
        elif isinstance(item, dict):
            total += item.get("quantity", 1) * item.get("price", 0)
    return round(total, 2)


@expenses_bp.route("", methods=["GET"])
def get_expenses():
    """
    Get all expenses for current user with pagination and filters.
    Query params:
    - page (default: 1)
    - per_page (default: 10, max: 100)
    - category
    - start_date (ISO string)
    - end_date (ISO string)
    - min_amount
    - max_amount
    """
    user_id, error_response = _get_current_user_id()
    if error_response:
        return error_response

    try:
        page = max(int(request.args.get("page", 1)), 1)
        per_page = int(request.args.get("per_page", 10))
        if per_page < 1 or per_page > 100:
            raise ValueError
    except ValueError:
        return jsonify({"error": "page and per_page must be valid integers"}), 400

    query = {"user_id": user_id}

    category = (request.args.get("category") or "").strip()
    if category:
        query["category"] = category

    amount_filter = {}
    min_amount = request.args.get("min_amount")
    max_amount = request.args.get("max_amount")
    try:
        if min_amount is not None:
            amount_filter["$gte"] = float(min_amount)
        if max_amount is not None:
            amount_filter["$lte"] = float(max_amount)
    except (TypeError, ValueError):
        return jsonify({"error": "min_amount and max_amount must be numbers"}), 400
    if amount_filter:
        query["total_amount"] = amount_filter

    start_date, start_error = _parse_datetime(request.args.get("start_date"), "start_date")
    if start_error:
        return jsonify({"error": start_error}), 400

    end_date, end_error = _parse_datetime(request.args.get("end_date"), "end_date")
    if end_error:
        return jsonify({"error": end_error}), 400

    if start_date or end_date:
        query["date"] = {}
        if start_date:
            query["date"]["$gte"] = start_date
        if end_date:
            query["date"]["$lte"] = end_date

    expenses_collection = _get_expenses_collection()
    total = expenses_collection.count_documents(query)

    cursor = (
        expenses_collection.find(query)
        .sort("date", -1)
        .skip((page - 1) * per_page)
        .limit(per_page)
    )

    expenses = [Expense.from_dict(expense_data).to_dict_public() for expense_data in cursor]

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


@expenses_bp.route("/<expense_id>", methods=["GET"])
def get_expense(expense_id):
    """Get one expense by ID for the current user."""
    user_id, error_response = _get_current_user_id()
    if error_response:
        return error_response

    if not ObjectId.is_valid(expense_id):
        return jsonify({"error": "Invalid expense ID"}), 400

    expense_data = _get_expenses_collection().find_one(
        {"_id": ObjectId(expense_id), "user_id": user_id}
    )
    if not expense_data:
        return jsonify({"error": "Expense not found"}), 404

    return jsonify({"expense": Expense.from_dict(expense_data).to_dict_public()}), 200


@expenses_bp.route("", methods=["POST"])
def create_expense():
    """
    Create a new expense for the current user.
    Required JSON body: title, category, items
    Optional JSON body: date, receipt_image, notes
    """
    user_id, error_response = _get_current_user_id()
    if error_response:
        return error_response

    data = request.get_json(silent=True) or {}

    title = data.get("title")
    category = data.get("category")
    items_data = data.get("items")
    receipt_image = data.get("receipt_image")
    notes = data.get("notes")

    if not title or not category:
        return jsonify({"error": "title and category are required"}), 400

    items, items_error = _parse_items(items_data)
    if items_error:
        return jsonify({"error": items_error}), 400

    expense_date, date_error = _parse_datetime(data.get("date"), "date")
    if date_error:
        return jsonify({"error": date_error}), 400

    expense = Expense(
        user_id=user_id,
        title=title,
        category=category,
        items=items,
        date=expense_date or datetime.utcnow(),
        receipt_image=receipt_image,
        notes=notes,
    )

    is_valid, validation_error = expense.validate()
    if not is_valid:
        return jsonify({"error": validation_error}), 400

    _get_expenses_collection().insert_one(expense.to_dict())
    return (
        jsonify(
            {
                "message": "Expense created successfully",
                "expense": expense.to_dict_public(),
            }
        ),
        201,
    )


@expenses_bp.route("/<expense_id>", methods=["PUT"])
def update_expense(expense_id):
    """
    Update an existing expense for the current user.
    Allowed JSON fields: title, category, items, date, receipt_image, notes
    """
    user_id, error_response = _get_current_user_id()
    if error_response:
        return error_response

    if not ObjectId.is_valid(expense_id):
        return jsonify({"error": "Invalid expense ID"}), 400

    expenses_collection = _get_expenses_collection()
    existing_expense_data = expenses_collection.find_one(
        {"_id": ObjectId(expense_id), "user_id": user_id}
    )
    if not existing_expense_data:
        return jsonify({"error": "Expense not found"}), 404

    data = request.get_json(silent=True) or {}
    if not data:
        return jsonify({"error": "No data provided for update"}), 400

    expense = Expense.from_dict(existing_expense_data)

    if "title" in data:
        expense.title = data.get("title")
    if "category" in data:
        expense.category = data.get("category")
    if "receipt_image" in data:
        expense.receipt_image = data.get("receipt_image")
    if "notes" in data:
        expense.notes = data.get("notes")
    if "date" in data:
        parsed_date, date_error = _parse_datetime(data.get("date"), "date")
        if date_error:
            return jsonify({"error": date_error}), 400
        expense.date = parsed_date
    if "items" in data:
        items, items_error = _parse_items(data.get("items"))
        if items_error:
            return jsonify({"error": items_error}), 400
        expense.items = items

    expense.total_amount = _calculate_total_amount(expense.items)
    expense.updated_at = datetime.utcnow()

    is_valid, validation_error = expense.validate()
    if not is_valid:
        return jsonify({"error": validation_error}), 400

    updated_doc = expense.to_dict()
    updated_doc.pop("_id", None)
    updated_doc["user_id"] = user_id

    expenses_collection.update_one(
        {"_id": ObjectId(expense_id), "user_id": user_id},
        {"$set": updated_doc},
    )

    refreshed_expense_data = expenses_collection.find_one(
        {"_id": ObjectId(expense_id), "user_id": user_id}
    )
    if not refreshed_expense_data:
        return jsonify({"error": "Expense not found"}), 404

    return (
        jsonify(
            {
                "message": "Expense updated successfully",
                "expense": Expense.from_dict(refreshed_expense_data).to_dict_public(),
            }
        ),
        200,
    )


@expenses_bp.route("/<expense_id>", methods=["DELETE"])
def delete_expense(expense_id):
    """Delete an expense for the current user."""
    user_id, error_response = _get_current_user_id()
    if error_response:
        return error_response

    if not ObjectId.is_valid(expense_id):
        return jsonify({"error": "Invalid expense ID"}), 400

    result = _get_expenses_collection().delete_one({"_id": ObjectId(expense_id), "user_id": user_id})
    if result.deleted_count == 0:
        return jsonify({"error": "Expense not found"}), 404

    return jsonify({"message": "Expense deleted successfully"}), 200
