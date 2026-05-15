"""
Authentication routes for BudgetSense.

Routes:
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/logout
- GET /api/auth/profile
- PUT /api/auth/profile
- POST /api/auth/change-password
"""

from datetime import datetime
from bson.objectid import ObjectId
from flask import Blueprint, jsonify, request
from pymongo.errors import DuplicateKeyError

from db.connection import get_collection
from models.user import User
from utils.auth import generate_access_token, get_user_id_from_request

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _get_users_collection():
    """Get users collection from MongoDB"""
    return get_collection("users")

def _get_current_user():
    """
    Get current authenticated user from request.
    
    Returns:
        tuple: (User object, None) or (None, error_response)
    """
    user_id = get_user_id_from_request()
    
    # If no user_id found in request
    if not user_id:
        return None, (jsonify({"error": "Authentication required"}), 401)

    # Validate ObjectId format
    if not ObjectId.is_valid(str(user_id)):
        return None, (jsonify({"error": "Invalid user ID format"}), 401)

    try:
        user_data = _get_users_collection().find_one({"_id": ObjectId(user_id)})
        if not user_data:
            return None, (jsonify({"error": "User not found"}), 404)
        
        return User.from_dict(user_data), None
    
    except Exception as e:
        print(f"❌ Error fetching current user: {e}")
        return None, (jsonify({"error": "Server error"}), 500)

@auth_bp.route("/register", methods=["POST"])
def register():
    """Register a new user."""
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password")
    monthly_income_value = data.get("monthly_income", 0)

    # ──────────────────────────────────────────────────────────────
    # VALIDATION
    # ──────────────────────────────────────────────────────────────
    if not name:
        return jsonify({"error": "Name is required"}), 400

    if not User.validate_email(email):
        return jsonify({"error": "Valid email is required"}), 400

    is_password_valid, password_error = User.validate_password(password)
    if not is_password_valid:
        return jsonify({"error": password_error}), 400

    # Convert monthly_income to float
    try:
        monthly_income = float(monthly_income_value) if monthly_income_value else 0.0
    except (TypeError, ValueError):
        return jsonify({"error": "Monthly income must be a number"}), 400

    if monthly_income < 0:
        return jsonify({"error": "Monthly income cannot be negative"}), 400

    # ──────────────────────────────────────────────────────────────
    # CHECK IF EMAIL ALREADY EXISTS
    # ──────────────────────────────────────────────────────────────
    users = _get_users_collection()
    
    if users.find_one({"email": email}):
        return jsonify({"error": "Email already registered"}), 409

    # ──────────────────────────────────────────────────────────────
    # CREATE USER OBJECT
    # ──────────────────────────────────────────────────────────────
    user = User(
        name=name,
        email=email,
        password=password,
        monthly_income=monthly_income
    )

    is_valid, error = user.validate()
    if not is_valid:
        return jsonify({"error": error}), 400

    # ──────────────────────────────────────────────────────────────
    # INSERT INTO DATABASE ← THIS WAS MISSING!
    # ──────────────────────────────────────────────────────────────
    try:
        result = users.insert_one(user.to_dict())
        print(f"✅ User inserted with ID: {result.inserted_id}")
    except DuplicateKeyError:
        return jsonify({"error": "Email already registered"}), 409
    except Exception as e:
        print(f"❌ Error inserting user: {e}")
        return jsonify({"error": f"Failed to register user: {str(e)}"}), 500

    # ──────────────────────────────────────────────────────────────
    # RETURN RESPONSE
    # ──────────────────────────────────────────────────────────────
    return (
        jsonify(
            {
                "message": "User registered successfully",
                "user_id": str(user._id),
                "user": user.to_dict_public(),
            }
        ),
        201,
    )

@auth_bp.route("/test-connection", methods=["GET"])
def test_connection():
    """Test if database connection works"""
    try:
        col = _get_users_collection()
        
        # Try to insert a test document
        test_doc = {
            "name": "Test User",
            "email": "test@test.com",
            "password": "hashed_password",
            "monthly_income": 0,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        result = col.insert_one(test_doc)
        
        return jsonify({
            "message": "Test insert successful",
            "inserted_id": str(result.inserted_id),
            "collection_name": col.name,
            "database_name": col.database.name
        }), 200
    except Exception as e:
        return jsonify({
            "error": str(e),
            "type": type(e).__name__
        }), 500

@auth_bp.route("/login", methods=["POST"])
def login():
    """Log in a user using email and password."""
    data = request.get_json(silent=True) or {}

    email = (data.get("email") or "").strip().lower()
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    try:
        user_data = _get_users_collection().find_one({"email": email})
        if not user_data:
            # Generic error message (don't reveal if email exists)
            return jsonify({"error": "Invalid email or password"}), 401

        user = User.from_dict(user_data)
        if not user.check_password(password):
            return jsonify({"error": "Invalid email or password"}), 401

        return jsonify(
            {
                "message": "Login successful",
                "user": user.to_dict_public(),
                "auth": {
                    "token_type": "Bearer",
                    "access_token": generate_access_token(user._id),
                },
            }
        ), 200
    
    except Exception as e:
        print(f"❌ Error during login: {e}")
        return jsonify({"error": "Server error during login"}), 500
    
@auth_bp.route("/logout", methods=["POST"])
def logout():
    """Log out endpoint for stateless authentication."""
    return jsonify({"message": "Logout successful"}), 200

@auth_bp.route("/profile", methods=["GET"])
def get_profile():
    """Get current user profile."""
    try:
        user, error_response = _get_current_user()
        if error_response:
            return error_response

        if not user:
            return jsonify({"error": "User not found"}), 404

        return jsonify({"user": user.to_dict_public()}), 200
    
    except Exception as e:
        print(f"❌ Error fetching profile: {e}")
        return jsonify({"error": "Server error"}), 500

@auth_bp.route("/profile", methods=["PUT"])
def update_profile():
    """Update current user profile."""
    try:
        user, error_response = _get_current_user()
        if error_response:
            return error_response

        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json(silent=True) or {}

        if "name" not in data and "monthly_income" not in data:
            return jsonify({"error": "Provide at least one field: name or monthly_income"}), 400

        update_fields: dict = {"updated_at": datetime.utcnow()}
        
        # Update name if provided
        if "name" in data:
            name = (data.get("name") or "").strip()
            if len(name) < 2:
                return jsonify({"error": "Name must be at least 2 characters"}), 400
            update_fields["name"] = name

        # Update monthly_income if provided
        if "monthly_income" in data:
            monthly_income_value = data.get("monthly_income")
            
            if monthly_income_value is None:
                return jsonify({"error": "Monthly income cannot be null"}), 400
            
            try:
                monthly_income = float(monthly_income_value)
            except (TypeError, ValueError):
                return jsonify({"error": "Monthly income must be a number"}), 400
            
            if monthly_income < 0:
                return jsonify({"error": "Monthly income cannot be negative"}), 400
            
            update_fields["monthly_income"] = monthly_income

        users = _get_users_collection()
        
        # Check if update was successful
        result = users.update_one({"_id": user._id}, {"$set": update_fields})
        
        if result.matched_count == 0:
            return jsonify({"error": "User not found"}), 404
        
        if result.modified_count == 0:
            return jsonify({"error": "No changes made"}), 400

        # Fetch updated user
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
    
    except Exception as e:
        print(f"❌ Error updating profile: {e}")
        return jsonify({"error": "Server error"}), 500

@auth_bp.route("/change-password", methods=["POST"])
def change_password():
    """Change current user's password."""
    try:
        user, error_response = _get_current_user()
        if error_response:
            return error_response

        if not user:
            return jsonify({"error": "User not found"}), 404

        data = request.get_json(silent=True) or {}
        old_password = data.get("old_password")
        new_password = data.get("new_password")

        if not old_password or not new_password:
            return jsonify({"error": "Old password and new password are required"}), 400

        if not user.check_password(old_password):
            return jsonify({"error": "Old password is incorrect"}), 401

        change_success, change_error = user.change_password(new_password)
        if not change_success:
            return jsonify({"error": change_error}), 400

        # Update password in database
        result = _get_users_collection().update_one(
            {"_id": user._id},
            {"$set": {"password": user.password, "updated_at": datetime.utcnow()}},
        )
        
        if result.modified_count == 0:
            return jsonify({"error": "Failed to update password"}), 500

        return jsonify({"message": "Password changed successfully"}), 200
    
    except Exception as e:
        print(f"❌ Error changing password: {e}")
        return jsonify({"error": "Server error"}), 500