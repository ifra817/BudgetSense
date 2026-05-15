# from db.connection import get_db

# def create_project_indexes():
#     """
#     Haleema's Task: Creating indexes to optimize filtering and searching.
#     Demonstrates: Advanced DB Query Optimization.
#     """
#     db = get_db()
    
#     # user_id par index: Taake specific user ka data foran mil jaye [cite: 48, 52]
#     db.expenses.create_index([("user_id", 1)])
    
#     # Compound Index on date and category: 
#     # Taake history page ke filters (Date range aur Category) fast kaam karein [cite: 49, 50, 51]
#     db.expenses.create_index([("date", -1), ("category", 1)])
    
#     print("✅ MongoDB Indexes created successfully!")

# if __name__ == "__main__":
#     create_project_indexes()