from datetime import datetime, timezone
from typing import Optional, Tuple, Dict, Any
from bson import ObjectId
from flask import Blueprint, jsonify, request, current_app

from db.connection import get_collection
from models.budget import Budget
from utils.validators import validate_budget_data

budgets_bp = Blueprint("budgets", __name__, url_prefix="/api/budgets")


# ─────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────────────────


def _get_budgets_collection():
    """Get the budgets collection from MongoDB."""
    return get_collection("budgets")


def _get_user_id(source: Dict[str, Any], field: str = "user_id") -> Tuple[Optional[ObjectId], Optional[Tuple]]:
    """
    Extract and validate user_id from a dict.
    Returns (ObjectId, None) on success or (None, error_response) on failure.
    """
    raw = source.get(field)
    if not raw:
        return None, (jsonify({"error": "user_id is required"}), 400)
    if not ObjectId.is_valid(raw):
        return None, (jsonify({"error": "Invalid user_id format"}), 400)
    return ObjectId(str(raw)), None


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/budgets  — List all budgets for user
# ─────────────────────────────────────────────────────────────────────────────


@budgets_bp.route("", methods=["GET"])
def get_budgets():
    """
    Get all budgets for a user.
    Query params: user_id*
    """
    user_id, error_response = _get_user_id(request.args)
    if error_response:
        return error_response

    try:
        col = _get_budgets_collection()
        budgets_data = list(col.find({"user_id": user_id}).sort("category", 1))
        budgets = [Budget.from_dict(b).to_dict_public() for b in budgets_data]

        return (
            jsonify(
                {
                    "budgets": budgets,
                    "total": len(budgets),
                    "message": f"Retrieved {len(budgets)} budgets",
                }
            ),
            200,
        )

    except Exception as exc:
        current_app.logger.error(f"Failed to fetch budgets: {exc}")
        return (
            jsonify({"error": "Server error. Could not fetch budgets."}),
            500,
        )


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/budgets/<budget_id>  — Get single budget
# ─────────────────────────────────────────────────────────────────────────────


@budgets_bp.route("/<budget_id>", methods=["GET"])
def get_budget(budget_id: str):
    """Get a specific budget by ID. Pass user_id as query param."""
    user_id, error_response = _get_user_id(request.args)
    if error_response:
        return error_response

    if not ObjectId.is_valid(budget_id):
        return jsonify({"error": "Invalid budget ID"}), 400

    try:
        col = _get_budgets_collection()
        budget_data = col.find_one(
            {"_id": ObjectId(budget_id), "user_id": user_id}
        )

        if not budget_data:
            return jsonify({"error": "Budget not found"}), 404

        budget = Budget.from_dict(budget_data)
        return (
            jsonify({"budget": budget.to_dict_public()}),
            200,
        )

    except Exception as exc:
        current_app.logger.error(f"Failed to fetch budget: {exc}")
        return (
            jsonify({"error": "Server error. Could not fetch budget."}),
            500,
        )


# ─────────────────────────────────────────────────────────────────────────────
#  POST /api/budgets  — Create budget
# ─────────────────────────────────────────────────────────────────────────────


@budgets_bp.route("", methods=["POST"])
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

    # Validate budget object
    is_valid, error_msg = budget.validate()
    if not is_valid:
        return jsonify({"error": error_msg}), 400

    try:
        col = _get_budgets_collection()
        
        # Check if budget already exists for this category and user
        existing = col.find_one(
            {"user_id": budget.user_id, "category": budget.category}
        )
        if existing:
            return (
                jsonify(
                    {"error": f"Budget for '{budget.category}' already exists for this user"}
                ),
                409,  # Conflict
            )

        result = col.insert_one(budget.to_dict())
        return (
            jsonify(
                {
                    "message": "Budget created successfully.",
                    "budget_id": str(result.inserted_id),
                    "budget": budget.to_dict_public(),
                }
            ),
            201,
        )

    except Exception as exc:
        current_app.logger.error(f"Failed to create budget: {exc}")
        return (
            jsonify({"error": "Server error. Could not create budget."}),
            500,
        )


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/budgets/check-exceeded  — Check which budgets are exceeded
# ─────────────────────────────────────────────────────────────────────────────

@budgets_bp.route("/check-exceeded", methods=["GET"])
def check_exceeded_budgets():
    """
    Check which budgets are exceeded for a user.
    Query params: user_id*
    Returns: List of exceeded budgets with warning levels
    """
    user_id, error_response = _get_user_id(request.args)
    if error_response:
        return error_response

    try:
        col = _get_budgets_collection()
        budgets_data = list(col.find({"user_id": user_id}))

        exceeded_budgets = []
        warning_budgets = []
        safe_budgets = []

        for b_data in budgets_data:
            budget = Budget.from_dict(b_data)
            status = budget.get_warning_level()
            budget_dict = budget.to_dict_public()

            if status == "danger":
                exceeded_budgets.append(budget_dict)
            elif status == "warning":
                warning_budgets.append(budget_dict)
            else:
                safe_budgets.append(budget_dict)

        return (
            jsonify(
                {
                    "exceeded": exceeded_budgets,
                    "warning": warning_budgets,
                    "safe": safe_budgets,
                    "summary": {
                        "total_budgets": len(budgets_data),
                        "exceeded_count": len(exceeded_budgets),
                        "warning_count": len(warning_budgets),
                        "safe_count": len(safe_budgets),
                    },
                }
            ),
            200,
        )

    except Exception as exc:
        current_app.logger.error(f"Failed to check exceeded budgets: {exc}")
        return (
            jsonify(
                {"error": "Server error. Could not check exceeded budgets."}
            ),
            500,
        )

# ─────────────────────────────────────────────────────────────────────────────
#  PUT /api/budgets/<budget_id>  — Update budget
# ─────────────────────────────────────────────────────────────────────────────


@budgets_bp.route("/<budget_id>", methods=["PUT"])
def update_budget(budget_id: str):
    """
    Update budget limit or other fields.
    Pass user_id in the JSON body to confirm ownership.
    Fields to update: limit, spent, category (optional)
    """
    data = request.get_json(silent=True) or {}
    user_id, error_response = _get_user_id(data)
    if error_response:
        return error_response

    if not ObjectId.is_valid(budget_id):
        return jsonify({"error": "Invalid budget ID"}), 400

    if not data:
        return jsonify({"error": "No data provided for update"}), 400

    try:
        col = _get_budgets_collection()
        existing_data = col.find_one(
            {"_id": ObjectId(budget_id), "user_id": user_id}
        )

        if not existing_data:
            return jsonify({"error": "Budget not found"}), 404

        budget = Budget.from_dict(existing_data)

        # Update limit if provided
        if "limit" in data:
            new_limit = float(data["limit"])
            if new_limit <= 0:
                return jsonify({"error": "Budget limit must be greater than 0"}), 400
            budget.update_limit(new_limit)

        # Update spent if provided
        if "spent" in data:
            new_spent = float(data["spent"])
            if new_spent < 0:
                return jsonify({"error": "Spent amount cannot be negative"}), 400
            budget.update_spent(new_spent)

        # Update category if provided
        if "category" in data:
            budget.category = str(data["category"]).strip()

        # Validate updated budget
        is_valid, error_msg = budget.validate()
        if not is_valid:
            return jsonify({"error": error_msg}), 400

        # Update in database
        updated_doc = budget.to_dict()
        updated_doc.pop("_id", None)
        updated_doc["user_id"] = user_id

        col.update_one(
            {"_id": ObjectId(budget_id), "user_id": user_id},
            {"$set": updated_doc},
        )

        refreshed = col.find_one(
            {"_id": ObjectId(budget_id), "user_id": user_id}
        )

        return (
            jsonify(
                {
                    "message": "Budget updated successfully.",
                    "budget": Budget.from_dict(refreshed).to_dict_public(),
                }
            ),
            200,
        )

    except ValueError as ve:
        return jsonify({"error": f"Invalid value: {str(ve)}"}), 400
    except Exception as exc:
        current_app.logger.error(f"Failed to update budget: {exc}")
        return (
            jsonify({"error": "Server error. Could not update budget."}),
            500,
        )


# ─────────────────────────────────────────────────────────────────────────────
#  DELETE /api/budgets/<budget_id>  — Delete budget
# ─────────────────────────────────────────────────────────────────────────────


@budgets_bp.route("/<budget_id>", methods=["DELETE"])
def delete_budget(budget_id: str):
    """
    Delete a budget.
    Pass user_id in JSON body to confirm ownership.
    """
    data = request.get_json(silent=True) or {}
    user_id, error_response = _get_user_id(data)
    if error_response:
        return error_response

    if not ObjectId.is_valid(budget_id):
        return jsonify({"error": "Invalid budget ID"}), 400

    try:
        col = _get_budgets_collection()
        existing = col.find_one(
            {"_id": ObjectId(budget_id), "user_id": user_id}
        )

        if not existing:
            return jsonify({"error": "Budget not found"}), 404

        col.delete_one({"_id": ObjectId(budget_id), "user_id": user_id})

        return (
            jsonify(
                {
                    "message": "Budget deleted successfully.",
                    "budget_id": budget_id,
                }
            ),
            200,
        )

    except Exception as exc:
        current_app.logger.error(f"Failed to delete budget: {exc}")
        return (
            jsonify({"error": "Server error. Could not delete budget."}),
            500,
        )
