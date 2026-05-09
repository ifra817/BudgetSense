"""
Budget Model
Demonstrates: Document structure, relationships, calculated fields
"""

from datetime import datetime
from bson.objectid import ObjectId

# Built-in categories - Same as Expense
BUILT_IN_CATEGORIES = [
    "Food",
    "Transport",
    "Entertainment",
    "Utilities",
    "Healthcare",
    "Shopping",
    "Education",
    "Dining",
    "Sports",
    "Travel",
    "Groceries",
    "Other"
]


class Budget:
    """
    Budget document model
    
    Document structure:
    {
        "_id": ObjectId,
        "user_id": ObjectId,
        "category": str,
        "limit": float,
        "spent": float,
        "remaining": float,
        "percentage_used": float,
        "created_at": datetime,
        "updated_at": datetime
    }
    
    Relationships:
    - user_id references users collection
    - category should match categories used in expenses
    """
    
    def __init__(self, user_id, category, limit, spent=0, _id=None):
        self._id = _id or ObjectId()
        self.user_id = ObjectId(user_id) if isinstance(user_id, str) else user_id
        self.category = category
        self.limit = float(limit)
        self.spent = float(spent)
        self.remaining = self.limit - self.spent
        self.percentage_used = round((self.spent / self.limit * 100), 2) if self.limit > 0 else 0
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def update_spent(self, spent_amount):
        """Update spent amount and recalculate remaining/percentage"""
        self.spent = float(spent_amount)
        self.remaining = self.limit - self.spent
        self.percentage_used = round((self.spent / self.limit * 100), 2) if self.limit > 0 else 0
        self.updated_at = datetime.utcnow()
    
    def update_limit(self, new_limit):
        """Update budget limit"""
        self.limit = float(new_limit)
        self.remaining = self.limit - self.spent
        self.percentage_used = round((self.spent / self.limit * 100), 2) if self.limit > 0 else 0
        self.updated_at = datetime.utcnow()
    
    def is_exceeded(self):
        """Check if budget is exceeded"""
        return self.spent > self.limit
    
    def get_warning_level(self):
        """
        Get warning level based on percentage used
        Returns: 'safe', 'warning', 'danger'
        """
        if self.percentage_used >= 100:
            return 'danger'
        elif self.percentage_used >= 80:
            return 'warning'
        else:
            return 'safe'
    
    def to_dict(self):
        """Convert to MongoDB document"""
        return {
            '_id': self._id,
            'user_id': self.user_id,
            'category': self.category,
            'limit': self.limit,
            'spent': self.spent,
            'remaining': self.remaining,
            'percentage_used': self.percentage_used,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def to_dict_public(self):
        """Return budget data for API responses"""
        return {
            '_id': str(self._id),
            'user_id': str(self.user_id),
            'category': self.category,
            'limit': self.limit,
            'spent': self.spent,
            'remaining': self.remaining,
            'percentage_used': self.percentage_used,
            'status': self.get_warning_level(),
            'is_exceeded': self.is_exceeded(),
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @staticmethod
    def from_dict(data):
        """Create Budget object from dictionary (MongoDB document)"""
        budget = Budget(
            user_id=data.get('user_id'),
            category=data.get('category'),
            limit=data.get('limit'),
            spent=data.get('spent', 0),
            _id=data.get('_id')
        )
        budget.created_at = data.get('created_at', datetime.utcnow())
        budget.updated_at = data.get('updated_at', datetime.utcnow())
        return budget
    
    def validate(self):
        """
        Validate budget data before insertion
        Returns: (is_valid, error_message)
        """
        # Validate user_id
        if not self.user_id:
            return False, "User ID is required"
        
        # Validate category
        if not self.category or len(self.category.strip()) < 2:
            return False, "Category is required"
        
        # Validate limit
        if self.limit <= 0:
            return False, "Budget limit must be greater than 0"
        
        # Validate spent
        if self.spent < 0:
            return False, "Spent amount cannot be negative"
        
        return True, None
    
    @staticmethod
    def get_categories():
        """Get all available categories"""
        return BUILT_IN_CATEGORIES
    
    @staticmethod
    def is_valid_category(category):
        """Check if category is valid (built-in or custom)"""
        return category and len(category.strip()) > 0
