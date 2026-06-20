from flask import Blueprint, jsonify
from database import db, Product, Customer, Supplier, SalesOrder, PurchaseOrder
from datetime import datetime
from sqlalchemy import func, extract

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
def dashboard():
    now = datetime.now()
    month_start = now.strftime('%Y-%m-01')

    monthly_sales = db.session.query(func.coalesce(func.sum(SalesOrder.total_amount), 0))\
        .filter(SalesOrder.order_date >= month_start, SalesOrder.status != 'cancelled').scalar()

    monthly_purchases = db.session.query(func.coalesce(func.sum(PurchaseOrder.total_amount), 0))\
        .filter(PurchaseOrder.order_date >= month_start, PurchaseOrder.status != 'cancelled').scalar()

    product_count = Product.query.count()
    customer_count = Customer.query.count()
    supplier_count = Supplier.query.count()

    pending_sales = SalesOrder.query.filter(SalesOrder.status.in_(['confirmed', 'shipped'])).count()
    pending_purchases = PurchaseOrder.query.filter(PurchaseOrder.status == 'confirmed').count()

    low_stock = Product.query.filter(Product.stock_qty <= Product.min_stock)\
        .order_by(Product.stock_qty.asc()).all()

    recent_sales = SalesOrder.query.options(db.joinedload(SalesOrder.customer))\
        .order_by(SalesOrder.created_at.desc()).limit(5).all()

    # Sales trend: group by month manually (compatible with SQLite + PostgreSQL)
    all_sales = SalesOrder.query.filter(SalesOrder.status != 'cancelled')\
        .order_by(SalesOrder.order_date.desc()).all()
    monthly = {}
    for so in all_sales:
        month_key = so.order_date[:7]  # 'YYYY-MM'
        monthly[month_key] = monthly.get(month_key, 0) + so.total_amount
    sales_trend = [{'month': k, 'amount': round(v, 2)} for k, v in sorted(monthly.items(), reverse=True)[:12]]

    return jsonify({
        'monthly_sales': round(monthly_sales, 2),
        'monthly_purchases': round(monthly_purchases, 2),
        'product_count': product_count,
        'customer_count': customer_count,
        'supplier_count': supplier_count,
        'pending_sales': pending_sales,
        'pending_purchases': pending_purchases,
        'low_stock': [{'id': p.id, 'code': p.code, 'name': p.name, 'stock_qty': p.stock_qty, 'min_stock': p.min_stock} for p in low_stock],
        'recent_sales': [{
            'id': so.id, 'order_no': so.order_no, 'order_date': so.order_date,
            'total_amount': so.total_amount, 'status': so.status,
            'customer_name': so.customer.name
        } for so in recent_sales],
        'sales_trend': sales_trend
    })
