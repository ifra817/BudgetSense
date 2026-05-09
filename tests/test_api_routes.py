import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from bson.objectid import ObjectId
from flask import Flask
from itsdangerous import URLSafeTimedSerializer

ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from routes.auth import auth_bp  # noqa: E402
from routes.expenses import expenses_bp  # noqa: E402
from models.user import User  # noqa: E402


class ApiRoutesTestCase(unittest.TestCase):
    def setUp(self):
        app = Flask(__name__)
        app.config["TESTING"] = True
        app.config["SECRET_KEY"] = "test-secret-key"
        app.register_blueprint(auth_bp)
        app.register_blueprint(expenses_bp)
        self.client = app.test_client()

    def _auth_header(self, user_id):
        token = URLSafeTimedSerializer("test-secret-key").dumps(
            {"user_id": str(user_id)},
            salt="budgetsense-auth-token",
        )
        return {"Authorization": f"Bearer {token}"}

    @patch("routes.auth.get_collection")
    def test_register_hashes_password(self, mock_get_collection):
        users = MagicMock()
        users.find_one.return_value = None
        mock_get_collection.return_value = users

        response = self.client.post(
            "/api/auth/register",
            json={
                "name": "Alice",
                "email": "alice@example.com",
                "password": "password123",
                "monthly_income": 5000,
            },
        )

        self.assertEqual(response.status_code, 201)
        inserted_doc = users.insert_one.call_args[0][0]
        self.assertTrue(inserted_doc["password"].startswith("pbkdf2:"))
        self.assertNotEqual(inserted_doc["password"], "password123")

    @patch("routes.auth.get_collection")
    def test_login_returns_access_token(self, mock_get_collection):
        users = MagicMock()
        mock_get_collection.return_value = users

        existing_user = User("Alice", "alice@example.com", "password123", 5000)
        users.find_one.return_value = existing_user.to_dict()

        response = self.client.post(
            "/api/auth/login",
            json={"email": "alice@example.com", "password": "password123"},
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        token_payload = URLSafeTimedSerializer("test-secret-key").loads(
            body["auth"]["access_token"],
            salt="budgetsense-auth-token",
        )
        self.assertEqual(token_payload["user_id"], str(existing_user._id))

    @patch("routes.auth.get_collection")
    def test_profile_update_changes_name_and_income(self, mock_get_collection):
        users = MagicMock()
        mock_get_collection.return_value = users

        user_id = ObjectId()
        base_user = User("Alice", "alice@example.com", "password123", 5000, _id=user_id).to_dict()
        updated_user = dict(base_user)
        updated_user["name"] = "Alice Updated"
        updated_user["monthly_income"] = 7000

        users.find_one.side_effect = [base_user, updated_user]

        response = self.client.put(
            "/api/auth/profile",
            headers=self._auth_header(user_id),
            json={"name": "Alice Updated", "monthly_income": 7000},
        )

        self.assertEqual(response.status_code, 200)
        users.update_one.assert_called_once()

    @patch("routes.auth.get_collection")
    def test_change_password_requires_valid_old_password(self, mock_get_collection):
        users = MagicMock()
        mock_get_collection.return_value = users

        user_id = ObjectId()
        user_doc = User("Alice", "alice@example.com", "oldpassword123", 5000, _id=user_id).to_dict()
        users.find_one.return_value = user_doc

        response = self.client.post(
            "/api/auth/change-password",
            headers=self._auth_header(user_id),
            json={"old_password": "wrongpassword", "new_password": "newpassword123"},
        )

        self.assertEqual(response.status_code, 401)
        users.update_one.assert_not_called()

    @patch("routes.expenses.get_collection")
    def test_create_expense_success(self, mock_get_collection):
        users = MagicMock()
        expenses = MagicMock()
        mock_get_collection.side_effect = lambda name: users if name == "users" else expenses

        user_id = ObjectId()
        users.find_one.return_value = {"_id": user_id, "name": "Alice"}

        response = self.client.post(
            "/api/expenses",
            headers=self._auth_header(user_id),
            json={
                "title": "Groceries",
                "category": "Food",
                "items": [
                    {"name": "Milk", "quantity": 2, "price": 3.5},
                    {"name": "Bread", "quantity": 1, "price": 2.0},
                ],
            },
        )

        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertEqual(body["expense"]["total_amount"], 9.0)
        expenses.insert_one.assert_called_once()

    @patch("routes.expenses.get_collection")
    def test_get_expenses_with_pagination(self, mock_get_collection):
        users = MagicMock()
        expenses = MagicMock()
        mock_get_collection.side_effect = lambda name: users if name == "users" else expenses

        user_id = ObjectId()
        expense_id = ObjectId()
        users.find_one.return_value = {"_id": user_id, "name": "Alice"}
        now = datetime.utcnow()

        expenses.count_documents.return_value = 1

        cursor = MagicMock()
        cursor.sort.return_value = cursor
        cursor.skip.return_value = cursor
        cursor.limit.return_value = cursor
        cursor.__iter__.return_value = iter(
            [
                {
                    "_id": expense_id,
                    "user_id": user_id,
                    "title": "Groceries",
                    "category": "Food",
                    "items": [{"name": "Milk", "quantity": 1, "price": 5}],
                    "date": now,
                    "total_amount": 5,
                    "receipt_image": None,
                    "notes": None,
                    "created_at": now,
                    "updated_at": now,
                }
            ]
        )
        expenses.find.return_value = cursor

        response = self.client.get(
            "/api/expenses?page=1&per_page=10",
            headers=self._auth_header(user_id),
        )

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(body["pagination"]["total"], 1)
        self.assertEqual(len(body["expenses"]), 1)

    @patch("routes.expenses.get_collection")
    def test_get_expense_by_id_success(self, mock_get_collection):
        users = MagicMock()
        expenses = MagicMock()
        mock_get_collection.side_effect = lambda name: users if name == "users" else expenses

        user_id = ObjectId()
        expense_id = ObjectId()
        now = datetime.utcnow()
        users.find_one.return_value = {"_id": user_id, "name": "Alice"}
        expenses.find_one.return_value = {
            "_id": expense_id,
            "user_id": user_id,
            "title": "Groceries",
            "category": "Food",
            "items": [{"name": "Milk", "quantity": 1, "price": 5}],
            "date": now,
            "total_amount": 5,
            "receipt_image": None,
            "notes": None,
            "created_at": now,
            "updated_at": now,
        }

        response = self.client.get(
            f"/api/expenses/{expense_id}",
            headers=self._auth_header(user_id),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["expense"]["_id"], str(expense_id))

    @patch("routes.expenses.get_collection")
    def test_update_expense_success(self, mock_get_collection):
        users = MagicMock()
        expenses = MagicMock()
        mock_get_collection.side_effect = lambda name: users if name == "users" else expenses

        user_id = ObjectId()
        expense_id = ObjectId()
        now = datetime.utcnow()
        users.find_one.return_value = {"_id": user_id, "name": "Alice"}
        existing_doc = {
            "_id": expense_id,
            "user_id": user_id,
            "title": "Old Title",
            "category": "Food",
            "items": [{"name": "Milk", "quantity": 1, "price": 5}],
            "date": now,
            "total_amount": 5,
            "receipt_image": None,
            "notes": None,
            "created_at": now,
            "updated_at": now,
        }
        updated_doc = dict(existing_doc)
        updated_doc["title"] = "New Title"
        expenses.find_one.side_effect = [existing_doc, updated_doc]

        response = self.client.put(
            f"/api/expenses/{expense_id}",
            headers=self._auth_header(user_id),
            json={"title": "New Title"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["expense"]["title"], "New Title")
        expenses.update_one.assert_called_once()

    @patch("routes.expenses.get_collection")
    def test_delete_expense_success(self, mock_get_collection):
        users = MagicMock()
        expenses = MagicMock()
        mock_get_collection.side_effect = lambda name: users if name == "users" else expenses

        user_id = ObjectId()
        expense_id = ObjectId()
        users.find_one.return_value = {"_id": user_id, "name": "Alice"}
        expenses.delete_one.return_value = MagicMock(deleted_count=1)

        response = self.client.delete(
            f"/api/expenses/{expense_id}",
            headers=self._auth_header(user_id),
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["message"], "Expense deleted successfully")


if __name__ == "__main__":
    unittest.main()
