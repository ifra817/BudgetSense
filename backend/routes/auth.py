"""
Authentication routes for BudgetSense.

Routes:
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/logout
- GET /api/auth/profile
- PUT /api/auth/profile
- POST /api/auth/change-password

Authentication for protected routes is done using either:
- X-User-Id header
- Authorization: Bearer <user_id>
"""

from datetime import datetime

from bson.objectid import ObjectId
from flask import Blueprint, jsonify, request
from pymongo.errors import DuplicateKeyError

from db.connection import get_collection
from models.user import User

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _get_users_collection():
    return get_collection("users")


def _get_user_id_from_request():
    header_user_id = request.headers.get("X-User-Id")
    if header_user_id:
        return header_user_id.strip()

    auth_header = request.headers.get("Authorization", "").strip()
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()

    return None


def _get_current_user():
    user_id = _get_user_id_from_request()
    if not user_id:
        return None, (jsonify({"error": "Authentication required"}), 401)

    if not ObjectId.is_valid(user_id):
        return None, (jsonify({"error": "Invalid user ID"}), 401)

    user_data = _get_users_collection().find_one({"_id": ObjectId(user_id)})
    if not user_data:
        return None, (jsonify({"error": "User not found"}), 404)

    return User.from_dict(user_data), None


@auth_bp.route("/register", methods=["POST"])
def register():
    """
    Register a new user.
    Required JSON body: name, email, password
    Optional JSON body: monthly_income
    """
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    monthly_income = data.get("monthly_income", 0)

    if not name:
        return jsonify({"error": "Name is required"}), 400

    if not User.validate_email(email):
        return jsonify({"error": "Valid email is required"}), 400

    is_password_valid, password_error = User.validate_password(password)
    if not is_password_valid:
        return jsonify({"error": password_error}), 400

    try:
        monthly_income = float(monthly_income)
    except (TypeError, ValueError):
        return jsonify({"error": "Monthly income must be a number"}), 400

    if monthly_income < 0:
        return jsonify({"error": "Monthly income cannot be negative"}), 400

    users = _get_users_collection()
    if users.find_one({"email": email}):
        return jsonify({"error": "Email already registered"}), 409

    user = User(name=name, email=email, password=password, monthly_income=monthly_income)
    is_valid, error = user.validate()
    if not is_valid:
        return jsonify({"error": error}), 400

    try:
        users.insert_one(user.to_dict())
    except DuplicateKeyError:
        return jsonify({"error": "Email already registered"}), 409

    return (
        jsonify(
            {
                "message": "User registered successfully",
                "user": user.to_dict_public(),
            }
        ),
        201,
    )


@auth_bp.route("/login", methods=["POST"])
def login():
    """
    Log in a user using email and password.
    Required JSON body: email, password
    """
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user_data = _get_users_collection().find_one({"email": email})
    if not user_data:
        return jsonify({"error": "Invalid email or password"}), 401

    user = User.from_dict(user_data)
    if not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    return jsonify(
        {
            "message": "Login successful",
            "user": user.to_dict_public(),
            "auth": {
                "token_type": "user_id",
                "access_token": str(user._id),
            },
        }
    ), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    """
    Log out endpoint for stateless authentication.
    Clients should clear the stored token on their side.
    """
    return jsonify({"message": "Logout successful"}), 200


@auth_bp.route("/profile", methods=["GET"])
def get_profile():
    """Get current user profile."""
    user, error_response = _get_current_user()
    if error_response:
        return error_response

    return jsonify({"user": user.to_dict_public()}), 200


@auth_bp.route("/profile", methods=["PUT"])
def update_profile():
    """
    Update current user profile.
    Allowed JSON fields: name, monthly_income
    """
    user, error_response = _get_current_user()
    if error_response:
        return error_response

    data = request.get_json(silent=True) or {}

    if "name" not in data and "monthly_income" not in data:
        return jsonify({"error": "Provide at least one field: name or monthly_income"}), 400

    update_fields = {"updated_at": datetime.utcnow()}

    if "name" in data:
        name = (data.get("name") or "").strip()
        if len(name) < 2:
            return jsonify({"error": "Name must be at least 2 characters"}), 400
        update_fields["name"] = name

    if "monthly_income" in data:
        try:
            monthly_income = float(data.get("monthly_income"))
        except (TypeError, ValueError):
            return jsonify({"error": "Monthly income must be a number"}), 400
        if monthly_income < 0:
            return jsonify({"error": "Monthly income cannot be negative"}), 400
        update_fields["monthly_income"] = monthly_income

    users = _get_users_collection()
    users.update_one({"_id": user._id}, {"$set": update_fields})

    updated_user_data = users.find_one({"_id": user._id})
    if not updated_user_data:
        return jsonify({"error": "User not found"}), 404

    return (
        jsonify(
            {
                "message": "Profile updated successfully",
                "user": User.from_dict(updated_user_data).to_dict_public(),
            }
        ),
        200,
    )


@auth_bp.route("/change-password", methods=["POST"])
def change_password():
    """
    Change current user's password.
    Required JSON body: old_password, new_password
    """
    user, error_response = _get_current_user()
    if error_response:
        return error_response

    data = request.get_json(silent=True) or {}
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not old_password or not new_password:
        return jsonify({"error": "Old password and new password are required"}), 400

    if not user.check_password(old_password):
        return jsonify({"error": "Old password is incorrect"}), 401

    is_valid_password, password_error = User.validate_password(new_password)
    if not is_valid_password:
        return jsonify({"error": password_error}), 400

    change_success, change_error = user.change_password(new_password)
    if not change_success:
        return jsonify({"error": change_error}), 400

    _get_users_collection().update_one(
        {"_id": user._id},
        {"$set": {"password": user.password, "updated_at": datetime.utcnow()}},
    )

    return jsonify({"message": "Password changed successfully"}), 200
