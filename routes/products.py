from flask import Blueprint, request, jsonify
from database import db, Product, SalesOrderItem, PurchaseOrderItem, InventoryLog

products_bp = Blueprint('products', __name__)

@products_bp.route('/products')
def list_products():
    search = request.args.get('search', '')
    q = Product.query
    if search:
        like = f'%{search}%'
        q = q.filter(db.or_(Product.name.like(like), Product.code.like(like), Product.category.like(like)))
    products = q.order_by(Product.id.desc()).all()
    return jsonify([{
        'id': p.id, 'code': p.code, 'name': p.name, 'category': p.category,
        'unit': p.unit, 'sale_price': p.sale_price, 'purchase_price': p.purchase_price,
        'stock_qty': p.stock_qty, 'min_stock': p.min_stock, 'created_at': str(p.created_at)
    } for p in products])

@products_bp.route('/products', methods=['POST'])
def create_product():
    data = request.json
    try:
        p = Product(
            code=data['code'], name=data['name'],
            category=data.get('category', ''), unit=data.get('unit', '个'),
            sale_price=data['sale_price'], purchase_price=data['purchase_price'],
            stock_qty=data.get('stock_qty', 0), min_stock=data.get('min_stock', 10)
        )
        db.session.add(p)
        db.session.flush()
        if data.get('stock_qty', 0) > 0:
            db.session.add(InventoryLog(
                product_id=p.id, change_type='init', qty=data['stock_qty'],
                before_qty=0, after_qty=data['stock_qty'],
                reference='初始库存', notes='创建商品'
            ))
        db.session.commit()
        return jsonify({'id': p.id, 'message': '创建成功'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@products_bp.route('/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.json
    try:
        p = Product.query.get(product_id)
        if not p:
            return jsonify({'error': '商品不存在'}), 404
        p.code = data['code']
        p.name = data['name']
        p.category = data.get('category', '')
        p.unit = data.get('unit', '个')
        p.sale_price = data['sale_price']
        p.purchase_price = data['purchase_price']
        p.min_stock = data.get('min_stock', 10)
        db.session.commit()
        return jsonify({'message': '更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@products_bp.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    if SalesOrderItem.query.filter_by(product_id=product_id).count() > 0 or \
       PurchaseOrderItem.query.filter_by(product_id=product_id).count() > 0:
        return jsonify({'error': '该商品已在订单中使用，无法删除'}), 400
    try:
        Product.query.filter_by(id=product_id).delete()
        db.session.commit()
        return jsonify({'message': '删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@products_bp.route('/inventory-logs')
def list_inventory_logs():
    logs = InventoryLog.query.order_by(InventoryLog.created_at.desc()).limit(200).all()
    return jsonify([{
        'id': l.id, 'product_id': l.product_id, 'change_type': l.change_type,
        'qty': l.qty, 'before_qty': l.before_qty, 'after_qty': l.after_qty,
        'reference': l.reference, 'notes': l.notes,
        'product_name': l.product.name, 'product_code': l.product.code,
        'created_at': str(l.created_at)
    } for l in logs])

@products_bp.route('/products/<int:product_id>/stock', methods=['PUT'])
def adjust_stock(product_id):
    data = request.json
    change_qty = int(data['qty'])
    change_type = data.get('type', 'adjust')
    notes = data.get('notes', '')

    p = Product.query.get(product_id)
    if not p:
        return jsonify({'error': '商品不存在'}), 404

    before_qty = p.stock_qty
    after_qty = before_qty + change_qty
    if after_qty < 0:
        return jsonify({'error': f'库存不足，当前库存: {before_qty}'}), 400

    try:
        p.stock_qty = after_qty
        db.session.add(InventoryLog(
            product_id=product_id, change_type=change_type, qty=change_qty,
            before_qty=before_qty, after_qty=after_qty,
            reference='手动调整', notes=notes
        ))
        db.session.commit()
        return jsonify({'message': '库存调整成功', 'stock_qty': after_qty})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
