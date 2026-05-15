"""
backend/routes/analytics.py
Haleema's Task: Analytics & Aggregations with optimized queries

Ownership:
  Haleema — All analytics routes (GET), query optimization, aggregations
  Ifra    — Aggregation pipeline design
  Lead    — Pagination, filtering

Supports:
  ✅ GET /api/analytics/history - Filtered expense history
  ✅ GET /api/analytics/monthly-total - Month expense totals
  ✅ GET /api/analytics/category-breakdown - Category-wise spending
  ✅ GET /api/analytics/budget-vs-actual - Compare budgets to actual
  ✅ GET /api/analytics/spending-trend - Last 6 months trend
  ✅ GET /api/analytics/dashboard - All dashboard data combined
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple, Dict, Any, List
from bson import ObjectId
from flask import Blueprint, jsonify, request, current_app

from db.connection import get_collection
from models.expense import Expense
from models.budget import Budget

analytics_bp = Blueprint("analytics", __name__, url_prefix="/api/analytics")


# ─────────────────────────────────────────────────────────────────────────────
#  Internal helpers
# ─────────────────────────────────────────────────────────────────────────────


def _get_user_id(source: Dict[str, Any], field: str = "user_id") -> Tuple[Optional[ObjectId], Optional[Tuple]]:
    """
    Extract and validate user_id from a dict.
    Returns (ObjectId, None) on success or (None, error_response) on failure.
    """
    raw = source.get(field)
    if not raw:
        return None, (jsonify({"error": "user_id is required"}), 400)
    if not ObjectId.is_valid(raw):
        return None, (jsonify({"error": "Invalid user_id format"}), 400)
    return ObjectId(str(raw)), None


def _parse_datetime(
    value: Optional[str], field_name: str
) -> Tuple[Optional[datetime], Optional[str]]:
    """
    Parse ISO string or datetime.
    Returns (datetime, None) on success or (None, error_str) on failure.
    """
    if value in (None, ""):
        return None, None
    if isinstance(value, datetime):
        return value, None
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d", None):
            try:
                if fmt:
                    return (
                        datetime.strptime(value.strip(), fmt).replace(tzinfo=timezone.utc),
                        None,
                    )
                else:
                    return (
                        datetime.fromisoformat(value.replace("Z", "+00:00")),
                        None,
                    )
            except ValueError:
                continue
    return None, f"{field_name} must be a valid ISO date string (YYYY-MM-DD or ISO 8601)"


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/analytics/history  — Filtered expense history with pagination
# ─────────────────────────────────────────────────────────────────────────────


@analytics_bp.route("/history", methods=["GET"])
def get_filtered_history():
    """
    Get filtered expense history for a user.
    Query params: user_id*, page, per_page, category, start_date, end_date, min_amount, max_amount
    
    Haleema's optimization: Uses indexes on user_id, date, category for fast queries.
    """
    user_id, error_response = _get_user_id(request.args)
    if error_response:
        return error_response

    try:
        page = max(int(request.args.get("page", 1)), 1)
        per_page = int(request.args.get("per_page", 10))
        if per_page < 1 or per_page > 100:
            raise ValueError
    except ValueError:
        return (
            jsonify({"error": "page and per_page must be valid integers (1-100)"}),
            400,
        )

    # Build query filter
    query: Dict[str, Any] = {"user_id": user_id}

    # Category filter
    category = (request.args.get("category") or "").strip()
    if category and category != "All Categories":
        query["category"] = category

    # Date range filter
    start_date, start_error = _parse_datetime(request.args.get("start_date"), "start_date")
    if start_error:
        return jsonify({"error": start_error}), 400

    end_date, end_error = _parse_datetime(request.args.get("end_date"), "end_date")
    if end_error:
        return jsonify({"error": end_error}), 400

    if start_date or end_date:
        date_filter: Dict[str, datetime] = {}
        if start_date:
            date_filter["$gte"] = start_date
        if end_date:
            date_filter["$lte"] = end_date
        query["date"] = date_filter

    # Amount range filter
    amount_filter: Dict[str, float] = {}
    min_amount = request.args.get("min_amount")
    max_amount = request.args.get("max_amount")
    try:
        if min_amount is not None:
            amount_filter["$gte"] = float(min_amount)
        if max_amount is not None:
            amount_filter["$lte"] = float(max_amount)
    except (TypeError, ValueError):
        return (
            jsonify({"error": "min_amount and max_amount must be numbers"}),
            400,
        )
    if amount_filter:
        query["total_amount"] = amount_filter

    try:
        col = get_collection("expenses")
        total = col.count_documents(query)
        
        # Optimization: Uses index on (user_id, date, category)
        cursor = (
            col.find(query)
            .sort("date", -1)
            .skip((page - 1) * per_page)
            .limit(per_page)
        )
        
        expenses = [Expense.from_dict(e).to_dict_public() for e in cursor]

        return (
            jsonify(
                {
                    "expenses": expenses,
                    "pagination": {
                        "page": page,
                        "per_page": per_page,
                        "total": total,
                        "pages": (total + per_page - 1) // per_page if total else 0,
                    },
                }
            ),
            200,
        )

    except Exception as exc:
        current_app.logger.error(f"Failed to fetch expense history: {exc}")
        return (
            jsonify({"error": "Server error. Could not fetch history."}),
            500,
        )


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/analytics/monthly-total  — Monthly spending totals
# ─────────────────────────────────────────────────────────────────────────────


@analytics_bp.route("/monthly-total", methods=["GET"])
def get_monthly_total():
    """
    Get total spending for current month.
    Query params: user_id*, year, month
    
    Aggregation Pipeline: Groups by month, sums total_amount
    """
    user_id, error_response = _get_user_id(request.args)
    if error_response:
        return error_response

    try:
        year = int(request.args.get("year", datetime.now(timezone.utc).year))
        month = int(request.args.get("month", datetime.now(timezone.utc).month))
        
        if month < 1 or month > 12:
            return jsonify({"error": "Month must be between 1 and 12"}), 400
            
    except ValueError:
        return jsonify({"error": "Year and month must be valid integers"}), 400

    try:
        col = get_collection("expenses")
        
        # Aggregation pipeline: Sum all expenses for the month
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "date": {
                        "$gte": datetime(year, month, 1, tzinfo=timezone.utc),
                        "$lt": datetime(year, month + 1, 1, tzinfo=timezone.utc) if month < 12 
                               else datetime(year + 1, 1, 1, tzinfo=timezone.utc),
                    },
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_spent": {"$sum": "$total_amount"},
                    "expense_count": {"$sum": 1},
                    "avg_expense": {"$avg": "$total_amount"},
                }
            },
        ]

        result = list(col.aggregate(pipeline))

        if not result:
            return (
                jsonify(
                    {
                        "year": year,
                        "month": month,
                        "total_spent": 0,
                        "expense_count": 0,
                        "avg_expense": 0,
                    }
                ),
                200,
            )

        data = result[0]
        return (
            jsonify(
                {
                    "year": year,
                    "month": month,
                    "total_spent": round(data["total_spent"], 2),
                    "expense_count": data["expense_count"],
                    "avg_expense": round(data["avg_expense"], 2),
                }
            ),
            200,
        )

    except Exception as exc:
        current_app.logger.error(f"Failed to fetch monthly total: {exc}")
        return (
            jsonify({"error": "Server error. Could not fetch monthly total."}),
            500,
        )


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/analytics/category-breakdown  — Category-wise spending
# ─────────────────────────────────────────────────────────────────────────────


@analytics_bp.route("/category-breakdown", methods=["GET"])
def get_category_breakdown():
    """
    Get spending breakdown by category.
    Query params: user_id*, year, month (optional)
    
    Aggregation Pipeline: Groups by category, calculates percentage
    """
    user_id, error_response = _get_user_id(request.args)
    if error_response:
        return error_response

    year = request.args.get("year")
    month = request.args.get("month")

    try:
        col = get_collection("expenses")

        # Build match stage
        match_query: Dict[str, Any] = {"user_id": user_id}
        if year and month:
            try:
                y = int(year)
                m = int(month)
                if m < 1 or m > 12:
                    return jsonify({"error": "Month must be between 1 and 12"}), 400
                
                month_start = datetime(y, m, 1, tzinfo=timezone.utc)
                if m < 12:
                    month_end = datetime(y, m + 1, 1, tzinfo=timezone.utc)
                else:
                    month_end = datetime(y + 1, 1, 1, tzinfo=timezone.utc)
        
                match_query["date"] = {
                    "$gte": month_start,
                    "$lt": month_end,
                }
            except ValueError:
                return jsonify({"error": "Year and month must be valid integers"}), 400

        # Aggregation pipeline: Group by category and calculate percentage
        pipeline = [
            {"$match": match_query},
            {
                "$group": {
                    "_id": "$category",
                    "total_amount": {"$sum": "$total_amount"},
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"total_amount": -1}},
        ]

        results = list(col.aggregate(pipeline))

        # Calculate total and percentages
        total = sum(r["total_amount"] for r in results)
        
        breakdown = [
            {
                "category": r["_id"],
                "amount": round(r["total_amount"], 2),
                "count": r["count"],
                "percentage": round((r["total_amount"] / total * 100), 2) if total > 0 else 0,
            }
            for r in results
        ]

        return (
            jsonify(
                {
                    "breakdown": breakdown,
                    "total": round(total, 2),
                    "categories_count": len(breakdown),
                }
            ),
            200,
        )

    except Exception as exc:
        current_app.logger.error(f"Failed to fetch category breakdown: {exc}")
        return (
            jsonify({"error": "Server error. Could not fetch category breakdown."}),
            500,
        )


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/analytics/budget-vs-actual  — Compare budgets to actual spending
# ─────────────────────────────────────────────────────────────────────────────


@analytics_bp.route("/budget-vs-actual", methods=["GET"])
def get_budget_vs_actual():
    """
    Compare budgeted amounts vs actual spending by category.
    Query params: user_id*, year, month
    """
    user_id, error_response = _get_user_id(request.args)
    if error_response:
        return error_response

    try:
        year = int(request.args.get("year", datetime.now(timezone.utc).year))
        month = int(request.args.get("month", datetime.now(timezone.utc).month))
        
        if month < 1 or month > 12:
            return jsonify({"error": "Month must be between 1 and 12"}), 400
            
    except ValueError:
        return jsonify({"error": "Year and month must be valid integers"}), 400

    try:
        expenses_col = get_collection("expenses")
        budgets_col = get_collection("budgets")

        # Get actual spending by category
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "date": {
                        "$gte": datetime(year, month, 1, tzinfo=timezone.utc),
                        "$lt": datetime(year, month + 1, 1, tzinfo=timezone.utc) if month < 12 
                               else datetime(year + 1, 1, 1, tzinfo=timezone.utc),
                    },
                }
            },
            {
                "$group": {
                    "_id": "$category",
                    "actual_spent": {"$sum": "$total_amount"},
                }
            },
        ]

        actual_spending = {r["_id"]: r["actual_spent"] for r in expenses_col.aggregate(pipeline)}

        # Get budgets
        budgets = list(budgets_col.find({"user_id": user_id}))

        # Compare
        comparison = []
        for budget_data in budgets:
            budget = Budget.from_dict(budget_data)
            actual = actual_spending.get(budget.category, 0)
            
            comparison.append({
                "category": budget.category,
                "budget_limit": budget.limit,
                "actual_spent": round(actual, 2),
                "remaining": round(budget.limit - actual, 2),
                "percentage_used": round((actual / budget.limit * 100), 2) if budget.limit > 0 else 0,
                "status": "danger" if actual > budget.limit else "warning" if actual >= budget.limit * 0.8 else "safe",
            })

        return (
            jsonify(
                {
                    "year": year,
                    "month": month,
                    "comparison": comparison,
                    "total_budget": round(sum(b["budget_limit"] for b in comparison), 2),
                    "total_spent": round(sum(b["actual_spent"] for b in comparison), 2),
                }
            ),
            200,
        )

    except Exception as exc:
        current_app.logger.error(f"Failed to fetch budget vs actual: {exc}")
        return (
            jsonify({"error": "Server error. Could not fetch budget comparison."}),
            500,
        )


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/analytics/spending-trend  — Last 6 months spending trend
# ─────────────────────────────────────────────────────────────────────────────


@analytics_bp.route("/spending-trend", methods=["GET"])
def get_spending_trend():
    """
    Get spending trend for last 6 months.
    Query params: user_id*, months (default 6, max 12)
    
    Aggregation Pipeline: Groups by month, shows trend
    """
    user_id, error_response = _get_user_id(request.args)
    if error_response:
        return error_response

    try:
        months_back = int(request.args.get("months", 6))
        if months_back < 1 or months_back > 12:
            months_back = 6
    except ValueError:
        months_back = 6

    try:
        col = get_collection("expenses")

        # Get start date (6 months ago)
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=30 * months_back)

        # Aggregation pipeline: Group by year-month
        pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "date": {"$gte": start_date},
                }
            },
            {
                "$group": {
                    "_id": {
                        "year": {"$year": "$date"},
                        "month": {"$month": "$date"},
                    },
                    "total_spent": {"$sum": "$total_amount"},
                    "expense_count": {"$sum": 1},
                }
            },
            {
                "$sort": {"_id.year": 1, "_id.month": 1}
            },
        ]

        results = list(col.aggregate(pipeline))

        trend = [
            {
                "year": r["_id"]["year"],
                "month": r["_id"]["month"],
                "total_spent": round(r["total_spent"], 2),
                "expense_count": r["expense_count"],
            }
            for r in results
        ]

        return (
            jsonify(
                {
                    "trend": trend,
                    "months_shown": len(trend),
                    "highest_month": max(trend, key=lambda x: x["total_spent"]) if trend else None,
                    "lowest_month": min(trend, key=lambda x: x["total_spent"]) if trend else None,
                    "average_monthly": round(sum(t["total_spent"] for t in trend) / len(trend), 2) if trend else 0,
                }
            ),
            200,
        )

    except Exception as exc:
        current_app.logger.error(f"Failed to fetch spending trend: {exc}")
        return (
            jsonify({"error": "Server error. Could not fetch spending trend."}),
            500,
        )


# ─────────────────────────────────────────────────────────────────────────────
#  GET /api/analytics/dashboard  — Complete dashboard data
# ─────────────────────────────────────────────────────────────────────────────


@analytics_bp.route("/dashboard", methods=["GET"])
def get_dashboard():
    """
    Get complete dashboard data combining all analytics.
    Query params: user_id*, year, month
    """
    user_id, error_response = _get_user_id(request.args)
    if error_response:
        return error_response

    try:
        year = int(request.args.get("year", datetime.now(timezone.utc).year))
        month = int(request.args.get("month", datetime.now(timezone.utc).month))
        
        if month < 1 or month > 12:
            return jsonify({"error": "Month must be between 1 and 12"}), 400
            
    except ValueError:
        return jsonify({"error": "Year and month must be valid integers"}), 400

    try:
        expenses_col = get_collection("expenses")
        budgets_col = get_collection("budgets")

        # Monthly total
        monthly_pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "date": {
                        "$gte": datetime(year, month, 1, tzinfo=timezone.utc),
                        "$lt": datetime(year, month + 1, 1, tzinfo=timezone.utc) if month < 12 
                               else datetime(year + 1, 1, 1, tzinfo=timezone.utc),
                    },
                }
            },
            {
                "$group": {
                    "_id": None,
                    "total_spent": {"$sum": "$total_amount"},
                    "expense_count": {"$sum": 1},
                    "avg_expense": {"$avg": "$total_amount"},
                }
            },
        ]

        monthly_result = list(expenses_col.aggregate(monthly_pipeline))
        monthly_data = monthly_result[0] if monthly_result else {
            "total_spent": 0,
            "expense_count": 0,
            "avg_expense": 0,
        }

        # Category breakdown
        category_pipeline = [
            {
                "$match": {
                    "user_id": user_id,
                    "date": {
                        "$gte": datetime(year, month, 1, tzinfo=timezone.utc),
                        "$lt": datetime(year, month + 1, 1, tzinfo=timezone.utc) if month < 12 
                               else datetime(year + 1, 1, 1, tzinfo=timezone.utc),
                    },
                }
            },
            {
                "$group": {
                    "_id": "$category",
                    "amount": {"$sum": "$total_amount"},
                }
            },
            {"$sort": {"amount": -1}},
            {"$limit": 5},
        ]

        categories = list(expenses_col.aggregate(category_pipeline))
        total_spent = monthly_data["total_spent"]

        category_data = [
            {
                "category": c["_id"],
                "amount": round(c["amount"], 2),
                "percentage": round((c["amount"] / total_spent * 100), 2) if total_spent > 0 else 0,
            }
            for c in categories
        ]

        # Budget status
        budgets = list(budgets_col.find({"user_id": user_id}))
        exceeded_count = sum(1 for b in budgets if Budget.from_dict(b).is_exceeded())

        return (
            jsonify(
                {
                    "dashboard": {
                        "year": year,
                        "month": month,
                        "monthly_summary": {
                            "total_spent": round(monthly_data["total_spent"], 2),
                            "expense_count": monthly_data["expense_count"],
                            "avg_expense": round(monthly_data["avg_expense"], 2),
                        },
                        "top_categories": category_data,
                        "budget_status": {
                            "total_budgets": len(budgets),
                            "exceeded_count": exceeded_count,
                            "on_track_count": len(budgets) - exceeded_count,
                        },
                    }
                }
            ),
            200,
        )

    except Exception as exc:
        current_app.logger.error(f"Failed to fetch dashboard: {exc}")
        return (
            jsonify({"error": "Server error. Could not fetch dashboard."}),
            500,
        )