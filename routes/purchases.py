from flask import Blueprint, request, jsonify
from database import db, PurchaseOrder, PurchaseOrderItem, Product, InventoryLog, Supplier
from datetime import datetime

purchases_bp = Blueprint('purchases', __name__)

def _order_dict(po):
    return {
        'id': po.id, 'order_no': po.order_no, 'supplier_id': po.supplier_id,
        'order_date': po.order_date, 'total_amount': po.total_amount,
        'paid_amount': po.paid_amount, 'status': po.status, 'notes': po.notes,
        'supplier_name': po.supplier.name
    }

@purchases_bp.route('/purchase-orders')
def list_purchase_orders():
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    q = PurchaseOrder.query.options(db.joinedload(PurchaseOrder.supplier))
    if search:
        like = f'%{search}%'
        q = q.filter(db.or_(PurchaseOrder.order_no.like(like), Supplier.name.like(like)))
    if status:
        q = q.filter(PurchaseOrder.status == status)
    orders = q.order_by(PurchaseOrder.created_at.desc()).all()
    return jsonify([_order_dict(po) for po in orders])

@purchases_bp.route('/purchase-orders/<int:order_id>')
def get_purchase_order(order_id):
    po = PurchaseOrder.query.options(db.joinedload(PurchaseOrder.supplier), db.joinedload(PurchaseOrder.items).joinedload(PurchaseOrderItem.product)).get(order_id)
    if not po:
        return jsonify({'error': '订单不存在'}), 404
    return jsonify({
        'order': _order_dict(po),
        'items': [{
            'id': i.id, 'purchase_order_id': i.purchase_order_id, 'product_id': i.product_id,
            'qty': i.qty, 'price': i.price, 'amount': i.amount,
            'product_name': i.product.name, 'product_code': i.product.code, 'unit': i.product.unit
        } for i in po.items]
    })

@purchases_bp.route('/purchase-orders', methods=['POST'])
def create_purchase_order():
    data = request.json
    try:
        now = datetime.now()
        count = PurchaseOrder.query.count() + 1
        order_no = f'PO-{now.year}{now.month:02d}{now.day:02d}-{count:03d}'
        po = PurchaseOrder(
            order_no=order_no, supplier_id=data['supplier_id'],
            order_date=data['order_date'], total_amount=0,
            paid_amount=data.get('paid_amount', 0), status='draft',
            notes=data.get('notes', '')
        )
        db.session.add(po)
        db.session.flush()
        total = 0
        for item in data['items']:
            price = item['price']
            qty = int(item['qty'])
            amount = round(price * qty, 2)
            total += amount
            db.session.add(PurchaseOrderItem(purchase_order_id=po.id, product_id=item['product_id'], qty=qty, price=price, amount=amount))
        po.total_amount = round(total, 2)
        db.session.commit()
        return jsonify({'id': po.id, 'order_no': order_no, 'message': '创建成功'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@purchases_bp.route('/purchase-orders/<int:order_id>', methods=['PUT'])
def update_purchase_order(order_id):
    data = request.json
    po = PurchaseOrder.query.options(db.joinedload(PurchaseOrder.items)).get(order_id)
    if not po:
        return jsonify({'error': '订单不存在'}), 404
    try:
        action = data.get('action', 'update')

        if action == 'confirm':
            if po.status != 'draft':
                raise Exception('只能确认草稿状态的订单')
            po.status = 'confirmed'

        elif action == 'receive':
            if po.status != 'confirmed':
                raise Exception('只能收货已确认的订单')
            for item in po.items:
                product = Product.query.get(item.product_id)
                before_qty = product.stock_qty
                after_qty = before_qty + item.qty
                product.stock_qty = after_qty
                db.session.add(InventoryLog(product_id=item.product_id, change_type='purchase', qty=item.qty, before_qty=before_qty, after_qty=after_qty, reference=po.order_no))
            po.status = 'received'

        elif action == 'complete':
            if po.status != 'received':
                raise Exception('只能完成已收货的订单')
            po.status = 'completed'
            po.paid_amount = po.total_amount

        elif action == 'cancel':
            if po.status in ('received', 'completed'):
                raise Exception('已收货或已完成的订单不能取消')
            po.status = 'cancelled'

        elif action == 'update':
            if po.status != 'draft':
                raise Exception('只能编辑草稿状态的订单')
            po.supplier_id = data.get('supplier_id', po.supplier_id)
            po.order_date = data.get('order_date', po.order_date)
            po.paid_amount = data.get('paid_amount', po.paid_amount)
            po.notes = data.get('notes', po.notes)
            if 'items' in data:
                PurchaseOrderItem.query.filter_by(purchase_order_id=order_id).delete()
                total = 0
                for item in data['items']:
                    amount = round(item['price'] * item['qty'], 2)
                    total += amount
                    db.session.add(PurchaseOrderItem(purchase_order_id=order_id, product_id=item['product_id'], qty=item['qty'], price=item['price'], amount=amount))
                po.total_amount = round(total, 2)

        db.session.commit()
        return jsonify({'message': '操作成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@purchases_bp.route('/purchase-orders/<int:order_id>', methods=['DELETE'])
def delete_purchase_order(order_id):
    po = PurchaseOrder.query.get(order_id)
    if not po:
        return jsonify({'error': '订单不存在'}), 404
    if po.status not in ('draft', 'cancelled'):
        return jsonify({'error': '只能删除草稿或已取消的订单'}), 400
    try:
        db.session.delete(po)
        db.session.commit()
        return jsonify({'message': '删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
