# If you keep it, fix the datetime imports like this:
from datetime import datetime, timedelta, timezone
from bson.objectid import ObjectId
from .connection import get_collection

# Inside get_monthly_trend:
cutoff = datetime.now(timezone.utc) - timedelta(days=months * 30)

# Inside get_monthly_total, get_category_breakdown, get_budget_vs_actual:
start_date = datetime(year, month, 1, tzinfo=timezone.utc)
if month == 12:
    end_date = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
else:
    end_date = datetime(year, month + 1, 1, tzinfo=timezone.utc)