"""
User Model
Demonstrates: Document structure, field types, validation, password hashing
"""

from datetime import datetime
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

class User:
    """
    User document model
    
    Document structure:
    {
        "_id": ObjectId,
        "name": str,
        "email": str (unique),
        "password": str (hashed),
        "monthly_income": float,
        "created_at": datetime,
        "updated_at": datetime
    }
    
    Security:
    - Passwords are hashed using werkzeug (PBKDF2)
    - Email is stored lowercase for case-insensitive lookups
    - Unique index on email prevents duplicate accounts
    """
    
    def __init__(self, name=None, email=None, password=None, monthly_income=0, _id=None):
        self._id = _id or ObjectId()
        self.name = name
        self.email = email.lower() if email else None  # Store email as lowercase
        self.password = generate_password_hash(password) if password else None
        self.monthly_income = float(monthly_income) if monthly_income else 0
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def update_profile(self, name=None, monthly_income=None):
        """Update user profile information"""
        if name:
            self.name = name
        if monthly_income is not None:
            self.monthly_income = float(monthly_income)
        self.updated_at = datetime.utcnow()
    
    def change_password(self, new_password):
        """Change user password"""
        if new_password and len(new_password) >= 8:
            self.password = generate_password_hash(new_password)
            self.updated_at = datetime.utcnow()
            return True, None
        return False, "Password must be at least 8 characters"
    
    def check_password(self, password):
        """
        Verify password against hash
        
        Args:
            password (str): Plain text password to verify
            
        Returns:
            bool: True if password matches, False otherwise
        """
        if not self.password or not password:
            return False
        return check_password_hash(self.password, password)
    
    def to_dict(self):
        """Convert user to dictionary for MongoDB insertion"""
        return {
            '_id': self._id,
            'name': self.name,
            'email': self.email,
            'password': self.password,
            'monthly_income': self.monthly_income,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    def to_dict_public(self):
        """Return user data without password (for API responses)"""
        return {
            '_id': str(self._id),
            'name': self.name,
            'email': self.email,
            'monthly_income': self.monthly_income,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    @staticmethod
    def from_dict(data):
        """Create User object from dictionary (MongoDB document)"""
        user = User(
            name=data.get('name'),
            email=data.get('email'),
            monthly_income=data.get('monthly_income', 0),
            _id=data.get('_id')
        )
        user.password = data.get('password')
        user.created_at = data.get('created_at', datetime.utcnow())
        user.updated_at = data.get('updated_at', datetime.utcnow())
        return user
    
    def validate(self):
        """
        Validate user data before insertion
        Returns: (is_valid, error_message)
        """
        # Validate name
        if not self.name or len(self.name.strip()) < 2:
            return False, "Name must be at least 2 characters"
        
        # Validate email
        if not self.email or '@' not in self.email or '.' not in self.email.split('@')[1]:
            return False, "Valid email is required (must contain @ and domain)"
        
        # Validate password (only on creation, not on update)
        if self.password and self.password.startswith('pbkdf2:'):
            # Password is already hashed, this is fine
            pass
        else:
            # If password is being set during creation but not hashed, it's an error
            if not self.password:
                return False, "Password is required"
        
        # Validate monthly income
        if self.monthly_income < 0:
            return False, "Monthly income cannot be negative"
        
        return True, None
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        if not email or '@' not in email:
            return False
        parts = email.split('@')
        if len(parts) != 2 or not parts[1] or '.' not in parts[1]:
            return False
        return True
    
    @staticmethod
    def validate_password(password):
        """Validate password strength"""
        if not password:
            return False, "Password is required"
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        if len(password) > 128:
            return False, "Password is too long"
        return True, None
