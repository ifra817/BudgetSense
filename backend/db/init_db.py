"""
Database Initialization Script
Creates collections and indexes in MongoDB Atlas
Run this ONCE to set up your database
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

def init_database():
    """Initialize MongoDB database with collections and indexes"""
    
    mongo_uri = os.getenv('MONGO_URI')
    
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
        db = client['BudgetSenseDB']
        
        print("\n" + "="*70)
        print("🔄 Initializing BudgetSense Database Indexes")
        print("="*70 + "\n")
        
        # ========== USERS COLLECTION INDEXES ==========
        print("👥 Setting up USERS Collection Indexes:\n")
        
        users = db['users']
        
        # Unique index on email
        users.create_index([("email", ASCENDING)], unique=True)
        print("  ✅ Unique Index: email")
        print("     Purpose: Ensure no duplicate accounts, fast login queries\n")
        
        # ========== EXPENSES COLLECTION INDEXES ==========
        print("💸 Setting up EXPENSES Collection Indexes:\n")
        
        expenses = db['expenses']
        
        # Index 1: user_id
        expenses.create_index([("user_id", ASCENDING)])
        print("  ✅ Index 1: user_id")
        print("     Purpose: Fast lookup of all expenses for a user\n")
        
        # Index 2: date (descending - newest first)
        expenses.create_index([("date", DESCENDING)])
        print("  ✅ Index 2: date (descending)")
        print("     Purpose: Fast date-range queries, sorting by newest first\n")
        
        # Index 3: category
        expenses.create_index([("category", ASCENDING)])
        print("  ✅ Index 3: category")
        print("     Purpose: Fast filtering by expense category\n")
        
        # Index 4: COMPOUND INDEX (Most important!)
        expenses.create_index([
            ("user_id", ASCENDING),
            ("date", DESCENDING),
            ("category", ASCENDING)
        ])
        print("  ✅ COMPOUND Index: (user_id, date, category)")
        print("     Purpose: Optimizes aggregation pipelines for analytics")
        print("     Used in: Monthly totals, category breakdown, budget comparisons\n")
        
        # ========== BUDGETS COLLECTION INDEXES ==========
        print("🎯 Setting up BUDGETS Collection Indexes:\n")
        
        budgets = db['budgets']
        
        # Index 1: user_id
        budgets.create_index([("user_id", ASCENDING)])
        print("  ✅ Index 1: user_id")
        print("     Purpose: Get all budgets for a user\n")
        
        # Index 2: COMPOUND (unique constraint)
        budgets.create_index(
            [("user_id", ASCENDING), ("category", ASCENDING)],
            unique=True
        )
        print("  ✅ COMPOUND Unique Index: (user_id, category)")
        print("     Purpose: User can have only ONE budget per category\n")
        
        # ========== DISPLAY SUMMARY ==========
        print("="*70)
        print("✨ Database Initialization Complete!")
        print("="*70 + "\n")
        
        print("📊 Collections Created:")
        print(f"   • users")
        print(f"   • expenses")
        print(f"   • budgets\n")
        
        print("📈 Indexes Summary:")
        print(f"   • users: 1 index (email unique)")
        print(f"   • expenses: 4 indexes (including 1 compound)")
        print(f"   • budgets: 2 indexes (including 1 compound unique)\n")
        
        print("🚀 Your database is ready to use!\n")
        
        client.close()
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("Please check your MONGO_URI in .env file")

if __name__ == "__main__":
    init_database()