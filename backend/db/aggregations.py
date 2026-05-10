"""
MongoDB Aggregation Pipelines
Demonstrates: $match, $group, $sum, $sort, $project
These are used for analytics and monthly expense reports
"""

from pymongo import DESCENDING
from .connection import get_collection
from datetime import datetime, timedelta
from bson.objectid import ObjectId

class ExpenseAggregations:
    """
    Aggregation pipeline queries for expense analytics
    These demonstrate advanced MongoDB concepts
    """
    
    @staticmethod
    def get_monthly_total(user_id, year, month):
        """
        Get total expenses for a specific month
        
        Pipeline stages:
        1. $match: Filter by user_id and date range
        2. $group: Group all expenses and sum the amounts
        3. $project: Format the output
        """
        expenses = get_collection('expenses')
        
        # Calculate date range for the month
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        pipeline = [
            {
                '$match': {
                    'user_id': ObjectId(user_id),
                    'date': {
                        '$gte': start_date,
                        '$lt': end_date
                    }
                }
            },
            {
                '$group': {
                    '_id': None,
                    'total': {'$sum': '$total_amount'},
                    'count': {'$sum': 1}
                }
            },
            {
                '$project': {
                    '_id': 0,
                    'total': 1,
                    'count': 1
                }
            }
        ]
        
        result = list(expenses.aggregate(pipeline))
        return result[0] if result else {'total': 0, 'count': 0}

    @staticmethod
    def get_monthly_trend(user_id, months=6):
        """Spending total per month over last N months"""
        expenses = get_collection('expenses')
        cutoff = datetime.utcnow() - timedelta(days=months * 30)
        
        pipeline = [
            {"$match": {
                "user_id": ObjectId(user_id),
                "date": {"$gte": cutoff}
            }},
            {"$group": {
                "_id": {
                    "year": {"$year": "$date"},
                    "month": {"$month": "$date"}
                },
                "total": {"$sum": "$total_amount"}
            }},
            {"$sort": {"_id.year": 1, "_id.month": 1}}
        ]
        return list(expenses.aggregate(pipeline))
    
    @staticmethod
    def get_category_breakdown(user_id, year, month):
        """
        Get expense breakdown by category for a month
        
        Pipeline stages:
        1. $match: Filter by user_id and date
        2. $group: Group by category and sum amounts
        3. $sort: Sort by total descending
        """
        expenses = get_collection('expenses')
        
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        pipeline = [
            {
                '$match': {
                    'user_id': ObjectId(user_id),
                    'date': {
                        '$gte': start_date,
                        '$lt': end_date
                    }
                }
            },
            {
                '$group': {
                    '_id': '$category',
                    'total': {'$sum': '$total_amount'},
                    'count': {'$sum': 1}
                }
            },
            {
                '$sort': {'total': -1}
            },
            {
                '$project': {
                    '_id': 0,
                    'category': '$_id',
                    'total': 1,
                    'count': 1
                }
            }
        ]
        
        return list(expenses.aggregate(pipeline))
    
    @staticmethod
    def get_budget_vs_actual(user_id, year, month):
        """
        Compare actual expenses vs budget limits
        Uses $lookup to join expenses with budgets collection
        """
        expenses = get_collection('expenses')
        
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)
        
        pipeline = [
            {
                '$match': {
                    'user_id': ObjectId(user_id),
                    'date': {
                        '$gte': start_date,
                        '$lt': end_date
                    }
                }
            },
            {
                '$group': {
                    '_id': '$category',
                    'actual': {'$sum': '$total_amount'}
                }
            },
            {
                '$lookup': {
                    'from': 'budgets',
                    'let': {'category': '$_id', 'user_id': ObjectId(user_id)},
                    'pipeline': [
                        {
                            '$match': {
                                '$expr': {
                                    '$and': [
                                        {'$eq': ['$category', '$$category']},
                                        {'$eq': ['$user_id', '$$user_id']}
                                    ]
                                }
                            }
                        }
                    ],
                    'as': 'budget_info'
                }
            },
            {
                '$project': {
                    '_id': 0,
                    'category': '$_id',
                    'actual': 1,
                    'budget': {
                        '$cond': [
                            {'$gt': [{'$size': '$budget_info'}, 0]},
                            {'$arrayElemAt': ['$budget_info.limit', 0]},
                            0
                        ]
                    },
                    'remaining': {
                        '$cond': [
                            {'$gt': [{'$size': '$budget_info'}, 0]},
                            {
                                '$subtract': [
                                    {'$arrayElemAt': ['$budget_info.limit', 0]},
                                    '$actual'
                                ]
                            },
                            {'$multiply': ['$actual', -1]}
                        ]
                    }
                }
            }
        ]
        
        return list(expenses.aggregate(pipeline))

# Export for use in routes
def get_monthly_total(user_id, year, month):
    return ExpenseAggregations.get_monthly_total(user_id, year, month)

def get_category_breakdown(user_id, year, month):
    return ExpenseAggregations.get_category_breakdown(user_id, year, month)

def get_budget_vs_actual(user_id, year, month):
    return ExpenseAggregations.get_budget_vs_actual(user_id, year, month)