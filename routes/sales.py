from flask import Blueprint, request, jsonify
from database import db, SalesOrder, SalesOrderItem, Product, InventoryLog, Customer
from datetime import datetime

sales_bp = Blueprint('sales', __name__)

def _order_dict(so):
    return {
        'id': so.id, 'order_no': so.order_no, 'customer_id': so.customer_id,
        'order_date': so.order_date, 'total_amount': so.total_amount,
        'paid_amount': so.paid_amount, 'status': so.status, 'notes': so.notes,
        'customer_name': so.customer.name
    }

@sales_bp.route('/sales-orders')
def list_sales_orders():
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    q = SalesOrder.query.options(db.joinedload(SalesOrder.customer))
    if search:
        like = f'%{search}%'
        q = q.filter(db.or_(SalesOrder.order_no.like(like), Customer.name.like(like)))
    if status:
        q = q.filter(SalesOrder.status == status)
    orders = q.order_by(SalesOrder.created_at.desc()).all()
    return jsonify([_order_dict(so) for so in orders])

@sales_bp.route('/sales-orders/<int:order_id>')
def get_sales_order(order_id):
    so = SalesOrder.query.options(db.joinedload(SalesOrder.customer), db.joinedload(SalesOrder.items).joinedload(SalesOrderItem.product)).get(order_id)
    if not so:
        return jsonify({'error': '订单不存在'}), 404
    return jsonify({
        'order': _order_dict(so),
        'items': [{
            'id': i.id, 'sales_order_id': i.sales_order_id, 'product_id': i.product_id,
            'qty': i.qty, 'price': i.price, 'amount': i.amount,
            'product_name': i.product.name, 'product_code': i.product.code, 'unit': i.product.unit
        } for i in so.items]
    })

@sales_bp.route('/sales-orders', methods=['POST'])
def create_sales_order():
    data = request.json
    try:
        now = datetime.now()
        count = SalesOrder.query.count() + 1
        order_no = f'SO-{now.year}{now.month:02d}{now.day:02d}-{count:03d}'
        so = SalesOrder(
            order_no=order_no, customer_id=data['customer_id'],
            order_date=data['order_date'], total_amount=0,
            paid_amount=data.get('paid_amount', 0), status='draft',
            notes=data.get('notes', '')
        )
        db.session.add(so)
        db.session.flush()
        total = 0
        for item in data['items']:
            product = Product.query.get(item['product_id'])
            if not product:
                raise Exception(f"商品 {item['product_id']} 不存在")
            price = item['price']
            qty = int(item['qty'])
            amount = round(price * qty, 2)
            total += amount
            db.session.add(SalesOrderItem(sales_order_id=so.id, product_id=item['product_id'], qty=qty, price=price, amount=amount))
        so.total_amount = round(total, 2)
        db.session.commit()
        return jsonify({'id': so.id, 'order_no': order_no, 'message': '创建成功'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@sales_bp.route('/sales-orders/<int:order_id>', methods=['PUT'])
def update_sales_order(order_id):
    data = request.json
    so = SalesOrder.query.options(db.joinedload(SalesOrder.items)).get(order_id)
    if not so:
        return jsonify({'error': '订单不存在'}), 404
    try:
        action = data.get('action', 'update')

        if action == 'confirm':
            if so.status != 'draft':
                raise Exception('只能确认草稿状态的订单')
            for item in so.items:
                product = Product.query.get(item.product_id)
                if product.stock_qty < item.qty:
                    raise Exception(f"商品 {product.name} 库存不足 (当前: {product.stock_qty}, 需要: {item.qty})")
                before_qty = product.stock_qty
                after_qty = before_qty - item.qty
                product.stock_qty = after_qty
                db.session.add(InventoryLog(product_id=item.product_id, change_type='sale', qty=item.qty, before_qty=before_qty, after_qty=after_qty, reference=so.order_no))
            so.status = 'confirmed'

        elif action == 'ship':
            if so.status != 'confirmed':
                raise Exception('只能发货已确认的订单')
            so.status = 'shipped'

        elif action == 'complete':
            if so.status not in ('confirmed', 'shipped'):
                raise Exception('只能完成已确认或已发货的订单')
            so.status = 'completed'
            so.paid_amount = so.total_amount

        elif action == 'cancel':
            if so.status == 'completed':
                raise Exception('已完成的订单不能取消')
            if so.status in ('confirmed', 'shipped'):
                for item in so.items:
                    product = Product.query.get(item.product_id)
                    before_qty = product.stock_qty
                    after_qty = before_qty + item.qty
                    product.stock_qty = after_qty
                    db.session.add(InventoryLog(product_id=item.product_id, change_type='cancel_return', qty=item.qty, before_qty=before_qty, after_qty=after_qty, reference=so.order_no))
            so.status = 'cancelled'

        elif action == 'update':
            if so.status != 'draft':
                raise Exception('只能编辑草稿状态的订单')
            so.customer_id = data.get('customer_id', so.customer_id)
            so.order_date = data.get('order_date', so.order_date)
            so.paid_amount = data.get('paid_amount', so.paid_amount)
            so.notes = data.get('notes', so.notes)
            if 'items' in data:
                SalesOrderItem.query.filter_by(sales_order_id=order_id).delete()
                total = 0
                for item in data['items']:
                    amount = round(item['price'] * item['qty'], 2)
                    total += amount
                    db.session.add(SalesOrderItem(sales_order_id=order_id, product_id=item['product_id'], qty=item['qty'], price=item['price'], amount=amount))
                so.total_amount = round(total, 2)

        db.session.commit()
        return jsonify({'message': '操作成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@sales_bp.route('/sales-orders/<int:order_id>', methods=['DELETE'])
def delete_sales_order(order_id):
    so = SalesOrder.query.get(order_id)
    if not so:
        return jsonify({'error': '订单不存在'}), 404
    if so.status not in ('draft', 'cancelled'):
        return jsonify({'error': '只能删除草稿或已取消的订单'}), 400
    try:
        db.session.delete(so)
        db.session.commit()
        return jsonify({'message': '删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
