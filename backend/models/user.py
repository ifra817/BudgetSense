from datetime import datetime, timezone
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

class User:
    def __init__(self, name=None, email=None, password=None, monthly_income=0.0, _id=None):
        self._id = _id or ObjectId()
        self.name = name
        self.email = email.lower() if email else None
        self.password = generate_password_hash(password) if password else None
        self.monthly_income = float(monthly_income) if monthly_income else 0.0
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)
    
    def update_profile(self, name=None, monthly_income=None):
        if name:
            self.name = name
        if monthly_income is not None:
            self.monthly_income = float(monthly_income)
        self.updated_at = datetime.now(timezone.utc)
    
    def change_password(self, new_password):
        if new_password and len(new_password) >= 8:
            self.password = generate_password_hash(new_password)
            self.updated_at = datetime.now(timezone.utc)
            return True, None
        return False, "Password must be at least 8 characters"
    
    def check_password(self, password):
        if not self.password or not password:
            return False
        return check_password_hash(self.password, password)
    
    def to_dict(self):
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
        user = User(
            name=data.get('name'),
            email=data.get('email'),
            monthly_income=data.get('monthly_income', 0),
            _id=data.get('_id')
        )
        user.password = data.get('password')
        user.created_at = data.get('created_at', datetime.now(timezone.utc))
        user.updated_at = data.get('updated_at', datetime.now(timezone.utc))
        return user
    
    def validate(self):
        if not self.name or len(self.name.strip()) < 2:
            return False, "Name must be at least 2 characters"
        if not self.email or '@' not in self.email or '.' not in self.email.split('@')[1]:
            return False, "Valid email is required"
        if self.password and self.password.startswith('pbkdf2:'):
            pass
        else:
            if not self.password:
                return False, "Password is required"
        if self.monthly_income < 0:
            return False, "Monthly income cannot be negative"
        return True, None
    
    @staticmethod
    def validate_email(email):
        if not email or '@' not in email:
            return False
        parts = email.split('@')
        if len(parts) != 2 or not parts[1] or '.' not in parts[1]:
            return False
        return True
    
    @staticmethod
    def validate_password(password):
        if not password:
            return False, "Password is required"
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        if len(password) > 128:
            return False, "Password is too long"
        return True, None