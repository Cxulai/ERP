from flask import Blueprint, request, jsonify
from database import get_db

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports')
def get_reports():
    report_type = request.args.get('type', 'summary')

    conn = get_db()
    cursor = conn.cursor()

    if report_type == 'summary':
        # Current month summary
        now = cursor.execute("SELECT datetime('now', 'localtime')").fetchone()[0]
        month_start = now[:8] + '01'

        sales_revenue = cursor.execute(
            "SELECT COALESCE(SUM(total_amount), 0) FROM sales_orders WHERE order_date >= ? AND status = 'completed'",
            (month_start,)
        ).fetchone()[0]

        sales_pending = cursor.execute(
            "SELECT COALESCE(SUM(total_amount), 0) FROM sales_orders WHERE status IN ('confirmed', 'shipped')"
        ).fetchone()[0]

        purchase_cost = cursor.execute(
            "SELECT COALESCE(SUM(total_amount), 0) FROM purchase_orders WHERE order_date >= ? AND status = 'completed'",
            (month_start,)
        ).fetchone()[0]

        purchase_pending = cursor.execute(
            "SELECT COALESCE(SUM(total_amount), 0) FROM purchase_orders WHERE status IN ('confirmed')"
        ).fetchone()[0]

        # Receivables (unpaid amounts from completed/confirmed/shipped sales)
        receivables = cursor.execute(
            "SELECT COALESCE(SUM(total_amount - paid_amount), 0) FROM sales_orders WHERE status NOT IN ('draft', 'cancelled')"
        ).fetchone()[0]

        # Payables
        payables = cursor.execute(
            "SELECT COALESCE(SUM(total_amount - paid_amount), 0) FROM purchase_orders WHERE status NOT IN ('draft', 'cancelled')"
        ).fetchone()[0]

        # Order counts
        sales_count = cursor.execute(
            "SELECT COUNT(*) FROM sales_orders WHERE order_date >= ?",
            (month_start,)
        ).fetchone()[0]

        purchase_count = cursor.execute(
            "SELECT COUNT(*) FROM purchase_orders WHERE order_date >= ?",
            (month_start,)
        ).fetchone()[0]

        profit = round(sales_revenue - purchase_cost, 2)

        conn.close()

        return jsonify({
            'sales_revenue': round(sales_revenue, 2),
            'sales_pending': round(sales_pending, 2),
            'purchase_cost': round(purchase_cost, 2),
            'purchase_pending': round(purchase_pending, 2),
            'receivables': round(receivables, 2),
            'payables': round(payables, 2),
            'sales_count': sales_count,
            'purchase_count': purchase_count,
            'profit': profit
        })

    elif report_type == 'income':
        # Monthly income trend (last 12 months)
        monthly = cursor.execute(
            """SELECT strftime('%Y-%m', order_date) as month,
                      SUM(CASE WHEN status = 'completed' THEN total_amount ELSE 0 END) as completed_amount,
                      SUM(CASE WHEN status NOT IN ('draft', 'cancelled') THEN total_amount ELSE 0 END) as total_amount,
                      COUNT(*) as order_count
               FROM sales_orders
               GROUP BY month ORDER BY month ASC"""
        ).fetchall()

        # Monthly purchase trend
        monthly_purchase = cursor.execute(
            """SELECT strftime('%Y-%m', order_date) as month,
                      SUM(CASE WHEN status = 'completed' THEN total_amount ELSE 0 END) as completed_amount,
                      SUM(CASE WHEN status NOT IN ('draft', 'cancelled') THEN total_amount ELSE 0 END) as total_amount,
                      COUNT(*) as order_count
               FROM purchase_orders
               GROUP BY month ORDER BY month ASC"""
        ).fetchall()

        conn.close()

        return jsonify({
            'sales_monthly': [dict(row) for row in monthly],
            'purchase_monthly': [dict(row) for row in monthly_purchase]
        })

    elif report_type == 'top-products':
        # Top selling products
        top_products = cursor.execute(
            """SELECT p.id, p.name, p.code,
                      COALESCE(SUM(soi.qty), 0) as total_qty,
                      COALESCE(SUM(soi.amount), 0) as total_amount
               FROM products p
               LEFT JOIN sales_order_items soi ON p.id = soi.product_id
               LEFT JOIN sales_orders so ON soi.sales_order_id = so.id AND so.status = 'completed'
               GROUP BY p.id ORDER BY total_qty DESC LIMIT 10"""
        ).fetchall()

        conn.close()
        return jsonify([dict(row) for row in top_products])

    else:
        conn.close()
        return jsonify({'error': '未知报表类型'}), 400
