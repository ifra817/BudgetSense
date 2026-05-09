# 👥 Team Roles & Database Responsibilities

This document clearly defines who owns what part of the BudgetSense project and which **Advanced Database Systems concepts** each member demonstrates.

---

## 🔵 **Ifra Ahmed** — Backend Core + Database Architecture

### Primary Responsibilities

- Flask application setup & configuration
- **MongoDB connection & initialization** ⭐
- **Database schema design & document structure** ⭐
- **Aggregation pipelines** (monthly totals, category breakdown) ⭐
- User authentication (register/login routes)
- Expense CRUD operations
- Budget CRUD operations

### Files You Own

```
backend/
├── app.py                    # Main Flask application
├── config.py                 # Database config, environment setup
├── db/
│   ├── __init__.py
│   ├── connection.py         # MongoDB connection setup ⭐ PRIMARY
│   └── aggregations.py       # Aggregation pipelines ⭐ PRIMARY
├── routes/
│   ├── __init__.py
│   ├── auth.py              # Register/login endpoints (PRIMARY)
│   ├── expenses.py          # Expense CRUD endpoints (PRIMARY)
│   └── budgets.py           # Budget CRUD endpoints (PRIMARY)
└── models/
    ├── __init__.py
    └── user.py              # User schema (PRIMARY)
```

### Database Concepts You Demonstrate

✅ **Document-Based Database Design** - Flexible JSON-like documents  
✅ **Document Structure** - Proper schema design with fields  
✅ **Embedded Documents** - items[] array within expense documents  
✅ **Aggregation Pipelines** - Calculate totals, group by category, filter by date, compare vs budget  
✅ **Relationships** - user_id references between collections  
✅ **Database Connection Management** - Connection pooling, error handling  

### Timeline: 5 Weeks

**Week 1-2:** Backend Setup & DB Connection
**Week 2-3:** Authentication Routes
**Week 3-4:** Expense CRUD Routes
**Week 4:** Budget Routes
**Week 4-5:** Aggregation Pipelines & Analytics ⭐ MOST IMPORTANT

---

## 🟢 **Haleema Zafar** — Frontend + Query Optimization

### Primary Responsibilities

- All frontend pages (HTML/CSS)
- Dashboard & analytics visualization
- **Implement filtered expense queries** (date range, category, amount)
- **Document index usage & query optimization**
- Budget settings page & routes
- Chart.js integration
- Responsive design

### Files You Own

```
frontend/
├── index.html               # Login/Register page (PRIMARY)
├── dashboard.html           # Main dashboard (PRIMARY)
├── history.html             # Expense history with filters (PRIMARY)
├── budget_settings.html     # Budget management (PRIMARY)
├── css/
│   └── style.css            # Styling (PRIMARY)
└── js/
    ├── main.js              # Main JavaScript (PRIMARY)
    └── chart.js             # Chart.js integration (PRIMARY)

backend/
├── db/
│   └── indexes.py           # Index creation & documentation (PRIMARY)
└── routes/
    └── analytics.py         # GET endpoints for dashboard (SECONDARY)
```

### Database Concepts You Demonstrate

✅ **Indexing** - Create indexes on date, category, user_id  
✅ **Query Optimization** - Show how indexes improve query performance  
✅ **Filtering & Searching** - Implement indexed range queries  
✅ **Performance Comparison** - Use explain() to show indexed vs non-indexed query times  

### Timeline: 4 Weeks

**Week 1-3:** Frontend Setup & Dashboard
**Week 3-4:** Expense History & Filtering + Index Creation
**Week 4:** Budget Settings Page
**Week 4-5:** Charts & Visualization

---

## 🟡 **Ramlah Munir** — Receipt Upload + Document Modeling & Data Validation

### Primary Responsibilities

- Receipt image upload handling
- OCR integration (optional)
- **Expense document schema & validation** ⭐
- **Input validation & data integrity** ⭐
- Add expense page & form handling
- Expense/receipt insert, update, delete operations

### Files You Own

```
backend/
├── models/
│   ├── __init__.py
│   ├── expense.py           # Expense schema (PRIMARY) ⭐
│   └── budget.py            # Budget schema (PRIMARY)
├── routes/
│   └── expenses.py          # POST/PUT/DELETE endpoints (SECONDARY)
├── utils/
│   ├── __init__.py
│   ├── validators.py        # Input validation (PRIMARY) ⭐
│   └── helpers.py           # File upload logic (PRIMARY)

frontend/
├── add_expense.html         # Receipt upload & manual entry form (PRIMARY)
```

### Database Concepts You Demonstrate

✅ **Document-Oriented Design** - Proper expense document structure  
✅ **Embedded Documents** - items[] array with name & price  
✅ **Data Validation** - Ensure only clean data enters MongoDB  
✅ **Schema Design** - Demonstrate flexibility of NoSQL schemas  
✅ **CRUD Operations** - Insert, update, delete expense documents  

### Timeline: 5 Weeks

**Week 1-2:** Add Expense Page & Form
**Week 2-3:** Expense Model & Validation
**Week 3-4:** Receipt Upload & File Handling
**Week 4-5:** OCR Integration (Optional)
**Week 4:** Budget Model

---

## 📊 Database Concepts Each Member Demonstrates

| Concept | Owner | Details |
|---------|-------|---------|
| **Connection Management** | Ifra | Setup, pooling, error handling |
| **Schema Design** | Ifra & Ramlah | Documents, fields, types |
| **Embedded Documents** | Ramlah | items[] array structure |
| **Validation** | Ramlah | Input validation, data integrity |
| **Aggregation Pipelines** | Ifra | $match, $group, $sum, $sort ⭐ |
| **Indexing** | Haleema | Performance optimization |
| **Filtering** | Haleema | Range queries, date filters |
| **Relationships** | Ifra | user_id references |

---

## 🎯 Specific Tasks Summary

### Ifra's Key Tasks
- [ ] Flask app setup with blueprints
- [ ] MongoDB connection (connection.py)
- [ ] User model & schema
- [ ] Auth routes (register, login)
- [ ] Expense CRUD routes
- [ ] Budget CRUD routes
- [ ] Aggregation pipelines (MOST IMPORTANT)
- [ ] Analytics endpoints

### Haleema's Key Tasks
- [ ] Create all HTML pages
- [ ] Responsive CSS styling with Bootstrap
- [ ] Dashboard layout & cards
- [ ] History page with filters
- [ ] Budget settings page
- [ ] Create indexes (indexes.py)
- [ ] Chart.js integration
- [ ] Performance documentation

### Ramlah's Key Tasks
- [ ] Add expense HTML form
- [ ] File upload UI
- [ ] Expense model class
- [ ] Budget model class
- [ ] Validation functions
- [ ] File upload handler
- [ ] POST/PUT/DELETE endpoints
- [ ] OCR integration (optional)

---

## 🤝 Communication Guidelines

- **Daily Standup:** 5-minute update on progress
- **Weekly Sync:** Discuss blockers & integration issues
- **Code Review:** Before merging to main
- **Emergency Help:** Slack/Discord for quick questions

---

## ✨ Definition of Done

All work must meet these criteria before being considered complete:

### Ifra's Definition of Done
- ✅ Flask app runs without errors
- ✅ MongoDB connection successful
- ✅ All routes tested with Postman
- ✅ Error handling implemented
- ✅ Code documented
- ✅ Aggregation pipelines produce correct results

### Haleema's Definition of Done
- ✅ All pages display correctly
- ✅ Responsive on mobile/tablet/desktop
- ✅ Navigation works between pages
- ✅ Filters work with proper indexing
- ✅ Charts display and update correctly
- ✅ Performance documentation created

### Ramlah's Definition of Done
- ✅ Form validation works client-side
- ✅ File upload validated and saved
- ✅ Models properly defined
- ✅ All validation functions tested
- ✅ CRUD endpoints functional
- ✅ Error messages clear and helpful

---

## 📞 Support Resources

- **MongoDB Docs:** https://docs.mongodb.com/
- **Flask Docs:** https://flask.palletsprojects.com/
- **Bootstrap Docs:** https://getbootstrap.com/docs/
- **Chart.js Docs:** https://www.chartjs.org/docs/

---

**Happy coding! Let's build something amazing together! 🚀**
