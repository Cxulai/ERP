from flask import Blueprint, request, jsonify
from database import db, SalesOrder, PurchaseOrder, SalesOrderItem, Product
from datetime import datetime
from sqlalchemy import func

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/reports')
def get_reports():
    report_type = request.args.get('type', 'summary')
    now = datetime.now()
    month_start = now.strftime('%Y-%m-01')

    if report_type == 'summary':
        sales_revenue = db.session.query(func.coalesce(func.sum(SalesOrder.total_amount), 0))\
            .filter(SalesOrder.order_date >= month_start, SalesOrder.status == 'completed').scalar()

        sales_pending = db.session.query(func.coalesce(func.sum(SalesOrder.total_amount), 0))\
            .filter(SalesOrder.status.in_(['confirmed', 'shipped'])).scalar()

        purchase_cost = db.session.query(func.coalesce(func.sum(PurchaseOrder.total_amount), 0))\
            .filter(PurchaseOrder.order_date >= month_start, PurchaseOrder.status == 'completed').scalar()

        purchase_pending = db.session.query(func.coalesce(func.sum(PurchaseOrder.total_amount), 0))\
            .filter(PurchaseOrder.status == 'confirmed').scalar()

        receivables = db.session.query(func.coalesce(func.sum(SalesOrder.total_amount - SalesOrder.paid_amount), 0))\
            .filter(SalesOrder.status.notin_(['draft', 'cancelled'])).scalar()

        payables = db.session.query(func.coalesce(func.sum(PurchaseOrder.total_amount - PurchaseOrder.paid_amount), 0))\
            .filter(PurchaseOrder.status.notin_(['draft', 'cancelled'])).scalar()

        sales_count = SalesOrder.query.filter(SalesOrder.order_date >= month_start).count()
        purchase_count = PurchaseOrder.query.filter(PurchaseOrder.order_date >= month_start).count()
        profit = round(sales_revenue - purchase_cost, 2)

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
        # Aggregate monthly trends in Python (portable across SQLite + PostgreSQL)
        all_sales = SalesOrder.query.all()
        sales_monthly = {}
        for so in all_sales:
            month = so.order_date[:7]
            if month not in sales_monthly:
                sales_monthly[month] = {'completed_amount': 0, 'total_amount': 0, 'order_count': 0}
            if so.status == 'completed':
                sales_monthly[month]['completed_amount'] += so.total_amount
            if so.status not in ('draft', 'cancelled'):
                sales_monthly[month]['total_amount'] += so.total_amount
            sales_monthly[month]['order_count'] += 1

        all_purchases = PurchaseOrder.query.all()
        purchase_monthly = {}
        for po in all_purchases:
            month = po.order_date[:7]
            if month not in purchase_monthly:
                purchase_monthly[month] = {'completed_amount': 0, 'total_amount': 0, 'order_count': 0}
            if po.status == 'completed':
                purchase_monthly[month]['completed_amount'] += po.total_amount
            if po.status not in ('draft', 'cancelled'):
                purchase_monthly[month]['total_amount'] += po.total_amount
            purchase_monthly[month]['order_count'] += 1

        return jsonify({
            'sales_monthly': [{'month': k, **v} for k, v in sorted(sales_monthly.items())],
            'purchase_monthly': [{'month': k, **v} for k, v in sorted(purchase_monthly.items())]
        })

    elif report_type == 'top-products':
        results = db.session.query(
            Product.id, Product.name, Product.code,
            func.coalesce(func.sum(SalesOrderItem.qty), 0).label('total_qty'),
            func.coalesce(func.sum(SalesOrderItem.amount), 0).label('total_amount')
        ).outerjoin(SalesOrderItem, Product.id == SalesOrderItem.product_id)\
         .outerjoin(SalesOrder, db.and_(SalesOrderItem.sales_order_id == SalesOrder.id, SalesOrder.status == 'completed'))\
         .group_by(Product.id).order_by(func.sum(SalesOrderItem.qty).desc()).limit(10).all()

        return jsonify([{
            'id': r.id, 'name': r.name, 'code': r.code,
            'total_qty': int(r.total_qty or 0), 'total_amount': round(r.total_amount or 0, 2)
        } for r in results])

    else:
        return jsonify({'error': '未知报表类型'}), 400
