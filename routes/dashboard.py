from flask import Blueprint, jsonify
from database import get_db

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
def dashboard():
    conn = get_db()
    cursor = conn.cursor()

    # KPI stats
    now = cursor.execute("SELECT datetime('now', 'localtime')").fetchone()[0]
    month_start = now[:8] + '01'

    monthly_sales = cursor.execute(
        "SELECT COALESCE(SUM(total_amount), 0) FROM sales_orders WHERE order_date >= ? AND status != 'cancelled'",
        (month_start,)
    ).fetchone()[0]

    monthly_purchases = cursor.execute(
        "SELECT COALESCE(SUM(total_amount), 0) FROM purchase_orders WHERE order_date >= ? AND status != 'cancelled'",
        (month_start,)
    ).fetchone()[0]

    product_count = cursor.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    customer_count = cursor.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    supplier_count = cursor.execute("SELECT COUNT(*) FROM suppliers").fetchone()[0]

    pending_sales = cursor.execute(
        "SELECT COUNT(*) FROM sales_orders WHERE status IN ('confirmed', 'shipped')"
    ).fetchone()[0]

    pending_purchases = cursor.execute(
        "SELECT COUNT(*) FROM purchase_orders WHERE status IN ('confirmed')"
    ).fetchone()[0]

    # Low stock products
    low_stock = cursor.execute(
        "SELECT id, code, name, stock_qty, min_stock FROM products WHERE stock_qty <= min_stock ORDER BY stock_qty ASC"
    ).fetchall()

    # Recent sales orders
    recent_sales = cursor.execute(
        """SELECT so.id, so.order_no, so.order_date, so.total_amount, so.status, c.name as customer_name
           FROM sales_orders so
           JOIN customers c ON so.customer_id = c.id
           ORDER BY so.created_at DESC LIMIT 5"""
    ).fetchall()

    # Monthly sales trend (last 12 months)
    sales_trend = cursor.execute(
        """SELECT strftime('%Y-%m', order_date) as month, SUM(total_amount) as amount
           FROM sales_orders WHERE status != 'cancelled'
           GROUP BY month ORDER BY month DESC LIMIT 12"""
    ).fetchall()

    conn.close()

    return jsonify({
        'monthly_sales': round(monthly_sales, 2),
        'monthly_purchases': round(monthly_purchases, 2),
        'product_count': product_count,
        'customer_count': customer_count,
        'supplier_count': supplier_count,
        'pending_sales': pending_sales,
        'pending_purchases': pending_purchases,
        'low_stock': [dict(row) for row in low_stock],
        'recent_sales': [dict(row) for row in recent_sales],
        'sales_trend': [{'month': row['month'], 'amount': round(row['amount'], 2)} for row in sales_trend]
    })
