"""
Expense Model
Demonstrates: Embedded documents, nested arrays, data validation
"""

from datetime import datetime
from bson.objectid import ObjectId

class ExpenseItem:
    """
    Represents a single item in an expense
    Demonstrates: Embedded document structure
    """
    
    def __init__(self, name, quantity=1, price=0):
        self.name = name
        self.quantity = int(quantity) if quantity else 1
        self.price = float(price) if price else 0
    
    def to_dict(self):
        """Convert item to dictionary"""
        return {
            'name': self.name,
            'quantity': self.quantity,
            'price': self.price
        }
    
    def get_total(self):
        """Calculate total for this item"""
        return self.quantity * self.price
    
    @staticmethod
    def from_dict(data):
        """Create ExpenseItem from dictionary"""
        return ExpenseItem(
            name=data.get('name'),
            quantity=data.get('quantity', 1),
            price=data.get('price', 0)
        )
    
    def validate(self):
        """Validate item data"""
        if not self.name or len(self.name.strip()) < 1:
            return False, "Item name is required"
        
        if self.quantity < 1:
            return False, "Quantity must be at least 1"
        
        if self.price < 0:
            return False, "Price cannot be negative"
        
        return True, None


class Expense:
    """
    Expense document model
    
    Document structure:
    {
        "_id": ObjectId,
        "user_id": ObjectId,
        "title": str,
        "category": str,
        "total_amount": float,
        "date": datetime,
        "items": [
            {
                "name": str,
                "quantity": int,
                "price": float
            }
        ],
        "receipt_image": str (optional),
        "notes": str (optional),
        "created_at": datetime,
        "updated_at": datetime
    }
    """
    
    # Built-in categories - Can be extended by users
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
    
    def __init__(self, user_id, title, category, items=None, date=None, 
                 receipt_image=None, notes=None, _id=None):
        self._id = _id or ObjectId()
        self.user_id = ObjectId(user_id) if isinstance(user_id, str) else user_id
        self.title = title
        self.category = category
        self.items = items or []
        self.date = date or datetime.utcnow()
        self.receipt_image = receipt_image
        self.notes = notes
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        # Calculate total amount from items
        self.total_amount = self._calculate_total()
    
    def _calculate_total(self):
        """Calculate total amount from items"""
        if not self.items:
            return 0
        
        total = 0
        for item in self.items:
            if isinstance(item, ExpenseItem):
                total += item.get_total()
            elif isinstance(item, dict):
                total += item.get('quantity', 1) * item.get('price', 0)
        
        return round(total, 2)
    
    def add_item(self, name, quantity=1, price=0):
        """Add an item to the expense"""
        item = ExpenseItem(name, quantity, price)
        is_valid, error = item.validate()
        
        if not is_valid:
            return False, error
        
        self.items.append(item)
        self.total_amount = self._calculate_total()
        return True, None
    
    def remove_item(self, index):
        """Remove an item by index"""
        if 0 <= index < len(self.items):
            self.items.pop(index)
            self.total_amount = self._calculate_total()
            return True, None
        return False, "Item index out of range"
    
    def to_dict(self):
        """Convert expense to dictionary for MongoDB insertion"""
        items_list = []
        for item in self.items:
            if isinstance(item, ExpenseItem):
                items_list.append(item.to_dict())
            else:
                items_list.append(item)
        
        return {
            '_id': self._id,
            'user_id': self.user_id,
            'title': self.title,
            'category': self.category,
            'total_amount': self.total_amount,
            'date': self.date,
            'items': items_list,
            'receipt_image': self.receipt_image,
            'notes': self.notes,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def to_dict_public(self):
        """Return expense data for API responses"""
        items_list = []
        for item in self.items:
            if isinstance(item, ExpenseItem):
                items_list.append(item.to_dict())
            else:
                items_list.append(item)
        
        return {
            '_id': str(self._id),
            'user_id': str(self.user_id),
            'title': self.title,
            'category': self.category,
            'total_amount': self.total_amount,
            'date': self.date.isoformat() if self.date else None,
            'items': items_list,
            'receipt_image': self.receipt_image,
            'notes': self.notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @staticmethod
    def from_dict(data):
        """Create Expense object from dictionary (MongoDB document)"""
        # Parse items
        items = []
        for item_data in data.get('items', []):
            items.append(ExpenseItem.from_dict(item_data))
        
        expense = Expense(
            user_id=data.get('user_id'),
            title=data.get('title'),
            category=data.get('category'),
            items=items,
            date=data.get('date'),
            receipt_image=data.get('receipt_image'),
            notes=data.get('notes'),
            _id=data.get('_id')
        )
        
        expense.created_at = data.get('created_at', datetime.utcnow())
        expense.updated_at = data.get('updated_at', datetime.utcnow())
        
        return expense
    
    def validate(self):
        """
        Validate expense data before insertion
        Returns: (is_valid, error_message)
        """
        # Validate title
        if not self.title or len(self.title.strip()) < 2:
            return False, "Title must be at least 2 characters"
        
        # Validate category
        if not self.category or len(self.category.strip()) < 2:
            return False, "Category is required"
        
        # Validate items
        if not self.items or len(self.items) == 0:
            return False, "At least one item is required"
        
        # Validate each item
        for item in self.items:
            if isinstance(item, ExpenseItem):
                is_valid, error = item.validate()
                if not is_valid:
                    return False, error
        
        # Validate total amount
        if self.total_amount <= 0:
            return False, "Total amount must be greater than 0"
        
        # Validate date
        if not self.date:
            return False, "Date is required"
        
        return True, None
    
    @staticmethod
    def get_categories():
        """Get all available categories"""
        return Expense.BUILT_IN_CATEGORIES
    
    @staticmethod
    def is_valid_category(category):
        """Check if category is valid (built-in or custom)"""
        # Allow both built-in and custom categories
        return category and len(category.strip()) > 0
