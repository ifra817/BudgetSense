from pymongo import ASCENDING, DESCENDING
from db.connection import get_collection

def create_indexes():
    """Create all necessary MongoDB indexes"""
    try:
        users = get_collection("users")
        expenses = get_collection("expenses")
        budgets = get_collection("budgets")

        # 1. User Indexes (Ensure emails are unique)
        users.create_index([("email", ASCENDING)], unique=True)

        # 2. Expense Indexes (Optimized for Haleema's date & category filters)
        expenses.create_index([("user_id", ASCENDING), ("date", DESCENDING)])
        expenses.create_index([("user_id", ASCENDING), ("category", ASCENDING)])
        
        # 3. Budget Indexes (Ensure one budget per category per user)
        budgets.create_index([("user_id", ASCENDING), ("category", ASCENDING)], unique=True)

        print("✅ MongoDB Indexes created successfully.")
    except Exception as e:
        print(f"⚠️ Warning: Could not create indexes: {e}")