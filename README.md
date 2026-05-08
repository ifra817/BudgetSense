# 💰 BudgetSense - Smart Receipt Scanner & Budget-Aware Expense Tracker

A lightweight, MongoDB-backed web application to help users manage expenses, track spending, and maintain budgets.

## 📋 Project Features

- 📸 Upload and scan receipts (with OCR support)
- 💳 Manually add expenses
- 📊 View analytics and spending dashboard
- 💰 Set monthly budgets by category
- 🚨 Get alerts when overspending
- 📈 Track spending trends
- 🔍 Filter expenses by date, category, and amount
- 📱 Responsive web interface

## 🏗️ Tech Stack

- **Backend:** Flask (Python web framework)
- **Database:** MongoDB (NoSQL document database)
- **Frontend:** HTML5, CSS3, Bootstrap 5
- **Charts:** Chart.js (data visualization)
- **OCR:** Pytesseract (receipt text extraction - optional)
- **Storage:** Local file system for receipt images

## 📁 Project Structure

```
BudgetSense/
├── backend/
│   ├── __init__.py
│   ├── app.py
│   ├── config.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── expenses.py
│   │   ├── budgets.py
│   │   └── analytics.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── expense.py
│   │   └── budget.py
│   ├── db/
│   │   ├── __init__.py
│   │   ├── connection.py
│   │   ├── indexes.py
│   │   └── aggregations.py
│   └── utils/
│       ├── __init__.py
│       ├── validators.py
│       └── helpers.py
├── frontend/
│   ├── index.html
│   ├── dashboard.html
│   ├── add_expense.html
│   ├── history.html
│   ├── budget_settings.html
│   ├── css/
│   │   └── style.css
│   └── js/
│       ├── main.js
│       └── chart.js
├── uploads/
│   └── .gitkeep
├── docs/
├── .gitignore
├── requirements.txt
├── README.md
├── .env.example
└── TEAM_ROLES.md
```

## 🚀 Getting Started

### Prerequisites

- **Python 3.8 or higher**
- **MongoDB** (local or MongoDB Atlas cloud)
- **pip** (Python package manager)
- **Git**

### Installation

#### 1️⃣ Clone the Repository

```bash
git clone https://github.com/ifra817/BudgetSense.git
cd BudgetSense
```

#### 2️⃣ Create Virtual Environment

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### 3️⃣ Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4️⃣ Set Up Environment Variables

```.env
# Copy the example env file
cp .env.example .env

# Edit .env with your settings
Edit .env file with your MongoDB URI:

env
FLASK_ENV=development
FLASK_DEBUG=True
SECRET_KEY=your-secret-key-here

# MongoDB local setup
MONGO_URI=mongodb://localhost:27017/budgetsense

# OR MongoDB Atlas cloud (recommended)
# MONGO_URI=mongodb+srv://username:password@cluster.mongodb.net/budgetsense?retryWrites=true&w=majority

UPLOAD_FOLDER=uploads
MAX_CONTENT_LENGTH=16777216
```

#### 5️⃣ Run the Application

```bash
python backend/app.py
```

#### 6️⃣ Open in Browser
```code
http://localhost:5000
```

## 📚 Database Design

### MongoDB Collections

1. users Collection
   
Stores user account information.

```json
{
  "_id": ObjectId,
  "name": "Ifra Ahmed",
  "email": "ifra@email.com",
  "password": "hashed_password",
  "monthly_income": 80000,
  "created_at": ISODate("2026-05-08T10:30:00Z")
}
```

2. budgets Collection
   
Stores category-wise budget limits.
```json
{
  "_id": ObjectId,
  "user_id": ObjectId("..."),
  "category": "Food",
  "limit": 15000,
  "created_at": ISODate("2026-05-08T10:30:00Z")
}
```

3. expenses/receipts Collection ⭐
  
Main collection for expense tracking with embedded documents.

```json
{
  "_id": ObjectId,
  "user_id": ObjectId("..."),
  "title": "Grocery Shopping",
  "category": "Food",
  "total_amount": 2500,
  "date": ISODate("2026-05-08T14:00:00Z"),
  "receipt_image": "uploads/img1.jpg",
  "items": [
    {
      "name": "Milk",
      "price": 300
    },
    {
      "name": "Bread",
      "price": 200
    }
  ],
  "created_at": ISODate("2026-05-08T14:05:00Z")
}
```

### Database Indexes

For optimized performance:

```JavaScript
// On user_id for faster lookups
db.expenses.createIndex({ "user_id": 1 })

// On date for range queries
db.expenses.createIndex({ "date": -1 })

// On category for filtering
db.expenses.createIndex({ "category": 1 })

// Compound index for common queries
db.expenses.createIndex({ "user_id": 1, "date": -1, "category": 1 })
```

## 📊 API Endpoints

### Authentication
- POST /auth/register - User registration
- POST /auth/login - User login
- POST /auth/logout - User logout

### Expenses
- GET /api/expenses - Get all user expenses
- POST /api/expenses - Add new expense
- GET /api/expenses/<id> - Get specific expense
- PUT /api/expenses/<id> - Update expense
- DELETE /api/expenses/<id> - Delete expense

### Analytics
- GET /api/analytics/monthly - Monthly spending totals
- GET /api/analytics/category - Category-wise breakdown
- GET /api/analytics/trends - Spending trends

### Budgets
- GET /api/budgets - Get all budgets
- POST /api/budgets - Create budget
- PUT /api/budgets/<id> - Update budget
- DELETE /api/budgets/<id> - Delete budget
  
## 💡 Key MongoDB Concepts Demonstrated

### 1. Document-Based Design

Flexible JSON-like documents allowing semi-structured receipt data.

### 2. Embedded Documents

Items array within expense documents demonstrating nested data.

### 3. References/Relationships

Using user_id ObjectId to link expenses to users.

### 4. Aggregation Pipelines ⭐

Advanced queries for analytics:

- Monthly expense totals
- Category-wise spending breakdown
- Budget vs. actual comparison

### 5. Indexing & Query Optimization

Indexes on frequently queried fields (user_id, date, category) for performance.

### 6. Data Validation

Schema validation to ensure data integrity before insertion.

## 👥 Team Roles & Responsibilities

See TEAM_ROLES.md for detailed information about each team member's role and database responsibilities:

- Ifra Ahmed - Backend Core & Database Architecture
- Haleema Zafar - Frontend & Query Optimization
- Ramlah Munir - Receipt Processing & Data Validation

## 📖 Documentation

Detailed documentation is available in the docs/ folder:

- DATABASE_DESIGN.md - Complete schema design & rationale
- AGGREGATION_PIPELINES.md - MongoDB aggregation examples
- API_ENDPOINTS.md - Detailed API documentation

## 🔐 Security Notes

- Passwords: Always hash passwords before storing (using werkzeug.security)
- Authentication: Implement JWT tokens or Flask sessions for secure auth
- Input Validation: All user input is validated before database insertion
- HTTPS: Use HTTPS in production
- Environment Variables: Never commit .env file to repository

## 🧪 Testing
```bash
# Run tests (when implemented)
pytest tests/
```

## 📦 Dependencies

All dependencies are listed in requirements.txt:

- Flask - Web framework
- pymongo - MongoDB driver
- python-dotenv - Environment management
- Pillow - Image processing
- pytesseract - OCR (optional)

## 🚨 Common Issues & Troubleshooting

### MongoDB Connection Error

- Ensure MongoDB is running: mongod
- Check MONGO_URI in .env file
- Verify MongoDB credentials if using Atlas
  
### Port Already in Use
```bash
# Kill process on port 5000
# Windows
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# macOS/Linux
lsof -ti:5000 | xargs kill -9
```

### Module Not Found Error
```bash
# Ensure you're in the virtual environment
# Windows: venv\Scripts\activate
# macOS/Linux: source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt

```
## 📝 License
This project is part of an academic assignment for Advanced Database Systems course.

## 👨‍💻 Contributors

| Member | Role | Database Focus |
|--------|------|-----------------|
| **Ifra Ahmed** | Backend & DB Architecture | Aggregation Pipelines, Connection, Schema Design |
| **Haleema** | Frontend & Query Optimization | Indexing, Query Performance, Filtering |
| **Ramlah** | Receipt Processing & Validation | Document Modeling, Data Integrity |

## 📞 Support

For issues or questions:

1. Check the `docs/` folder for detailed documentation
2. Review error messages in Flask console output
3. Check MongoDB connection logs
4. Consult `TEAM_ROLES.md` for task clarification

   
## ✨ Future Enhancements

- [ ] Advanced OCR with image preprocessing
- [ ] Email notifications for budget alerts
- [ ] Data export to CSV/PDF
- [ ] Mobile app version
- [ ] Recurring expense tracking
- [ ] Multi-currency support
- [ ] Bill reminders
- [ ] Collaborative budgeting

---

**Happy budgeting! 💰**