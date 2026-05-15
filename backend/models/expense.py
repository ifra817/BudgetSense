"""
Expense Model
Demonstrates: Embedded documents, nested arrays, data validation
"""
from datetime import datetime, timezone
from typing import Optional, List
from bson import ObjectId


class ExpenseItem:
    """
    Embedded sub-document stored INSIDE an Expense document.

    NoSQL concept: instead of a separate 'expense_items' collection with a
    foreign key, each item is nested directly in the parent document —
    one MongoDB read fetches the expense AND all its items (no JOIN needed).

    Example BSON structure inside an expense:
        "items": [
            { "name": "Milk",  "quantity": 2, "price": 150 },
            { "name": "Bread", "quantity": 1, "price": 200 }
        ]
    """

    def __init__(self, name: str, quantity: int = 1, price: float = 0.0):
        self.name: str = str(name).strip()
        self.quantity: int = int(quantity) if quantity else 1
        self.price: float = float(price) if price else 0.0

    # ── helpers ───────────────────────────────

    def get_total(self) -> float:
        """Line total = quantity × price."""
        return round(self.quantity * self.price, 2)

    def validate(self):
        """Return (True, None) on success or (False, error_str) on failure."""
        if not self.name or len(self.name.strip()) < 1:
            return False, "Item name is required"
        if self.quantity < 1:
            return False, "Quantity must be at least 1"
        if self.price < 0:
            return False, "Price cannot be negative"
        return True, None

    # ── serialisation ─────────────────────────

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "quantity": self.quantity,
            "price": self.price,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExpenseItem":
        return cls(
            name=data.get("name", ""),
            quantity=data.get("quantity", 1),
            price=data.get("price", 0.0),
        )

    def __repr__(self):
        return f"ExpenseItem(name={self.name!r}, qty={self.quantity}, price={self.price})"


# Backward-compat alias for any code that still imports LineItem
LineItem = ExpenseItem


# ─────────────────────────────────────────────────────────────────────────────
#  EXPENSE DOCUMENT MODEL
# ─────────────────────────────────────────────────────────────────────────────

class Expense:
    """
    Represents one MongoDB document in the 'expenses' collection.

    ADS Concepts:
      - Embedded Documents : 'items' is an array of ExpenseItem sub-documents
        stored directly inside this document (not a separate collection).
      - Schema Flexibility  : 'notes', 'receipt_image', 'updated_at' are
        optional — older documents without these fields still load correctly
        because from_dict() uses .get() with safe defaults.
      - Document-Oriented  : everything about one receipt lives in one place,
        making receipt display a single DB read.

    MongoDB Document Schema:
    {
        "_id":           ObjectId,
        "user_id":       ObjectId,          <- references users collection
        "title":         str,
        "category":      str,
        "total_amount":  float,
        "date":          datetime (UTC),
        "items": [                          <- EMBEDDED array of sub-documents
            { "name": str, "quantity": int, "price": float },
            ...
        ],
        "receipt_image": str | None,        <- path to uploaded file (optional)
        "notes":         str | None,        <- extra context (optional)
        "created_at":    datetime (UTC),
        "updated_at":    datetime (UTC)
    }
    """

    COLLECTION = "expenses"

    # Ramlah's original list + Ifra's additions, deduped and sorted
    VALID_CATEGORIES = [
        "Dining",
        "Education",
        "Entertainment",
        "Food",
        "Groceries",
        "Healthcare",
        "Other",
        "Shopping",
        "Sports",
        "Transport",
        "Travel",
        "Utilities",
    ]

    def __init__(
        self,
        user_id,
        title: str,
        category: str,
        items: Optional[List[ExpenseItem]] = None,
        date: Optional[datetime] = None,
        receipt_image: Optional[str] = None,
        notes: Optional[str] = None,
        _id: Optional[ObjectId] = None,
        total_amount: Optional[float] = None,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
    ):
        self._id: ObjectId = _id or ObjectId()
        self.user_id: ObjectId = (
            ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id
        )

        self.title: str = str(title).strip()
        self.category: str = category
        self.items: List[ExpenseItem] = items if items is not None else []
        self.date: datetime = date or datetime.now(timezone.utc)
        self.receipt_image: Optional[str] = receipt_image
        self.notes: Optional[str] = notes

        # total_amount: use explicit value when given, otherwise sum items
        if total_amount is not None:
            self.total_amount: float = round(float(total_amount), 2)
        else:
            self.total_amount = self._calculate_total()

        self.created_at: datetime = created_at or datetime.now(timezone.utc)
        self.updated_at: datetime = updated_at or datetime.now(timezone.utc)

    # ── computed ──────────────────────────────

    def _calculate_total(self) -> float:
        """Sum all embedded item totals."""
        total = 0.0
        for item in self.items:
            if isinstance(item, ExpenseItem):
                total += item.get_total()
            elif isinstance(item, dict):
                total += item.get("quantity", 1) * item.get("price", 0)
        return round(total, 2)

    @property
    def items_total(self) -> float:
        """Convenience property — same as _calculate_total()."""
        return self._calculate_total()

    # ── item mutation helpers ─────────────────

    def add_item(self, name: str, quantity: int = 1, price: float = 0.0):
        """Append a validated ExpenseItem and recalculate total."""
        item = ExpenseItem(name, quantity, price)
        is_valid, error = item.validate()
        if not is_valid:
            return False, error
        self.items.append(item)
        self.total_amount = self._calculate_total()
        return True, None

    def remove_item(self, index: int):
        """Remove item by index and recalculate total."""
        if 0 <= index < len(self.items):
            self.items.pop(index)
            self.total_amount = self._calculate_total()
            return True, None
        return False, "Item index out of range"

    # ── validation ────────────────────────────

    def validate(self):
        """
        Validate before DB insert/update.
        Returns (True, None) on success or (False, error_str) on failure.
        """
        if not self.title or len(self.title.strip()) < 2:
            return False, "Title must be at least 2 characters"

        if not self.category or len(self.category.strip()) < 2:
            return False, "Category is required"

        # Must have either items or a positive total_amount
        if not self.items and (self.total_amount is None or self.total_amount <= 0):
            return False, "Either add items or enter a total amount greater than 0"

        # Validate each item
        for item in self.items:
            if isinstance(item, ExpenseItem):
                is_valid, error = item.validate()
                if not is_valid:
                    return False, error

        if self.total_amount is not None and self.total_amount <= 0:
            return False, "Total amount must be greater than 0"

        if not self.date:
            return False, "Date is required"

        return True, None

    # ── serialisation ─────────────────────────

    def to_dict(self) -> dict:
        """
        BSON-ready dict for pymongo insert_one() / replace_one().
        The 'items' key contains the EMBEDDED array of sub-documents.
        """
        items_list = [
            item.to_dict() if isinstance(item, ExpenseItem) else item
            for item in self.items
        ]
        return {
            "_id": self._id,
            "user_id": self.user_id,
            "title": self.title,
            "category": self.category,
            "total_amount": self.total_amount,
            "date": self.date,
            "items": items_list,
            "receipt_image": self.receipt_image,
            "notes": self.notes,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_dict_public(self) -> dict:
        """
        API-safe dict: ObjectIds → str, datetimes → ISO strings.
        Used in all JSON responses so the frontend never sees raw BSON types.
        """
        items_list = [
            item.to_dict() if isinstance(item, ExpenseItem) else item
            for item in self.items
        ]
        return {
            "_id": str(self._id),
            "user_id": str(self.user_id),
            "title": self.title,
            "category": self.category,
            "total_amount": self.total_amount,
            "date": self.date.isoformat() if self.date else None,
            "items": items_list,
            "receipt_image": self.receipt_image,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "Expense":
        """
        Reconstruct an Expense from a raw MongoDB document.
        Uses .get() with defaults for schema-flexible fields so documents
        created before 'notes', 'receipt_image', or 'updated_at' was added
        still load without errors.
        """
        if data is None:
            raise ValueError("Cannot create Expense from None")

        items = [ExpenseItem.from_dict(i) for i in data.get("items", [])]

        expense = cls(
            _id=data.get("_id"),
            user_id=data["user_id"],
            title=data["title"],
            category=data["category"],
            total_amount=data.get("total_amount"),
            date=data.get("date"),
            items=items,
            receipt_image=data.get("receipt_image"),
            notes=data.get("notes"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )
        return expense

    # ── category helpers ──────────────────────

    @staticmethod
    def get_categories() -> list:
        return Expense.VALID_CATEGORIES

    @staticmethod
    def is_valid_category(category: str) -> bool:
        """Allow any non-empty category (built-in or custom)."""
        return bool(category and len(category.strip()) > 0)


    def __repr__(self):
        return (
            f"Expense(_id={self._id}, title={self.title!r}, "
            f"amount={self.total_amount}, items={len(self.items)})"
        )


# ─────────────────────────────────────────────────────────────────────────────
#  BUDGET DOCUMENT MODEL  (Ramlah owns; no conflict with Ifra)
# ─────────────────────────────────────────────────────────────────────────────

class Budget:
    """
    Represents one MongoDB document in the 'budgets' collection.
    Stores a per-category spending limit for a user.

    MongoDB Document Schema:
    {
        "_id":        ObjectId,
        "user_id":    ObjectId,    <- references users collection
        "category":   str,
        "limit":      float,
        "created_at": datetime (UTC)
    }
    """

    COLLECTION = "budgets"

    def __init__(
        self,
        user_id,
        category: str,
        limit: float,
        _id: Optional[ObjectId] = None,
        created_at: Optional[datetime] = None,
    ):
        self._id: ObjectId = _id or ObjectId()
        self.user_id: ObjectId = (
            ObjectId(user_id) if not isinstance(user_id, ObjectId) else user_id
        )
        self.category: str = str(category).strip()
        self.limit: float = round(float(limit), 2)
        self.created_at: datetime = created_at or datetime.now(timezone.utc)

    def to_dict(self) -> dict:
        return {
            "_id": self._id,
            "user_id": self.user_id,
            "category": self.category,
            "limit": self.limit,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Budget":
        return cls(
            _id=data.get("_id"),
            user_id=data["user_id"],
            category=data["category"],
            limit=data["limit"],
            created_at=data.get("created_at"),
        )

    def __repr__(self):
        return f"Budget(category={self.category!r}, limit={self.limit})"
