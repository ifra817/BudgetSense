from flask import Blueprint, request, jsonify
from db.connection import get_db
from bson.objectid import ObjectId

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/api/history', methods=['GET'])
def get_filtered_history():
    """
    Haleema's Task: Implement optimized filtered queries using indexes.
    """
    db = get_db()
    
    # Frontend se aane wale filters
    user_id = request.args.get('user_id') 
    category = request.args.get('category')
    start_date = request.args.get('start_date') # Format: YYYY-MM-DD
    end_date = request.args.get('end_date')

    # Query Filter setup [cite: 119]
    query = {"user_id": ObjectId(user_id)}

    if category and category != "All Categories":
        query["category"] = category
    
    if start_date and end_date:
        query["date"] = {"$gte": start_date, "$lte": end_date}

    # Optimization: Sort by date descending (latest first) [cite: 50, 101]
    # Yeh query aapke banaye huye indexes ko use karegi
    expenses = list(db.expenses.find(query).sort("date", -1))

    return jsonify(expenses)