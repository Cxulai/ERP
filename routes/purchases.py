from flask import Blueprint, request, jsonify
from database import get_db
from datetime import datetime

purchases_bp = Blueprint('purchases', __name__)

@purchases_bp.route('/purchase-orders')
def list_purchase_orders():
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    conn = get_db()
    cursor = conn.cursor()
    query = """SELECT po.*, s.name as supplier_name
               FROM purchase_orders po
               JOIN suppliers s ON po.supplier_id = s.id WHERE 1=1"""
    params = []
    if search:
        query += " AND (po.order_no LIKE ? OR s.name LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])
    if status:
        query += " AND po.status = ?"
        params.append(status)
    query += " ORDER BY po.created_at DESC"
    cursor.execute(query, params)
    orders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(orders)

@purchases_bp.route('/purchase-orders/<int:order_id>')
def get_purchase_order(order_id):
    conn = get_db()
    cursor = conn.cursor()
    order = cursor.execute(
        """SELECT po.*, s.name as supplier_name
           FROM purchase_orders po JOIN suppliers s ON po.supplier_id = s.id
           WHERE po.id=?""", (order_id,)
    ).fetchone()
    if not order:
        conn.close()
        return jsonify({'error': '订单不存在'}), 404
    items = cursor.execute(
        """SELECT poi.*, p.name as product_name, p.code as product_code, p.unit
           FROM purchase_order_items poi JOIN products p ON poi.product_id = p.id
           WHERE poi.purchase_order_id=?""", (order_id,)
    ).fetchall()
    conn.close()
    return jsonify({
        'order': dict(order),
        'items': [dict(item) for item in items]
    })

@purchases_bp.route('/purchase-orders', methods=['POST'])
def create_purchase_order():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        now = datetime.now()
        count = cursor.execute("SELECT COUNT(*) FROM purchase_orders").fetchone()[0] + 1
        order_no = f'PO-{now.year}{now.month:02d}{now.day:02d}-{count:03d}'

        cursor.execute(
            "INSERT INTO purchase_orders (order_no, supplier_id, order_date, total_amount, paid_amount, status, notes) VALUES (?,?,?,?,?,?,?)",
            (order_no, data['supplier_id'], data['order_date'], 0, data.get('paid_amount', 0), 'draft', data.get('notes', ''))
        )
        order_id = cursor.lastrowid
        total = 0

        for item in data['items']:
            price = item['price']
            qty = int(item['qty'])
            amount = round(price * qty, 2)
            total += amount
            cursor.execute(
                "INSERT INTO purchase_order_items (purchase_order_id, product_id, qty, price, amount) VALUES (?,?,?,?,?)",
                (order_id, item['product_id'], qty, price, amount)
            )

        cursor.execute("UPDATE purchase_orders SET total_amount=? WHERE id=?", (round(total, 2), order_id))
        conn.commit()
        return jsonify({'id': order_id, 'order_no': order_no, 'message': '创建成功'}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()

@purchases_bp.route('/purchase-orders/<int:order_id>', methods=['PUT'])
def update_purchase_order(order_id):
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        order = cursor.execute("SELECT * FROM purchase_orders WHERE id=?", (order_id,)).fetchone()
        if not order:
            conn.close()
            return jsonify({'error': '订单不存在'}), 404

        action = data.get('action', 'update')

        if action == 'confirm':
            if order['status'] != 'draft':
                raise Exception('只能确认草稿状态的订单')
            cursor.execute("UPDATE purchase_orders SET status='confirmed' WHERE id=?", (order_id,))

        elif action == 'receive':
            if order['status'] != 'confirmed':
                raise Exception('只能收货已确认的订单')
            items = cursor.execute("SELECT * FROM purchase_order_items WHERE purchase_order_id=?", (order_id,)).fetchall()
            for item in items:
                product = cursor.execute("SELECT * FROM products WHERE id=?", (item['product_id'],)).fetchone()
                before_qty = product['stock_qty']
                after_qty = before_qty + item['qty']
                cursor.execute("UPDATE products SET stock_qty=? WHERE id=?", (after_qty, item['product_id']))
                cursor.execute(
                    "INSERT INTO inventory_logs (product_id, change_type, qty, before_qty, after_qty, reference) VALUES (?, 'purchase', ?, ?, ?, ?)",
                    (item['product_id'], item['qty'], before_qty, after_qty, order['order_no'])
                )
            cursor.execute("UPDATE purchase_orders SET status='received' WHERE id=?", (order_id,))

        elif action == 'complete':
            if order['status'] != 'received':
                raise Exception('只能完成已收货的订单')
            cursor.execute("UPDATE purchase_orders SET status='completed', paid_amount=total_amount WHERE id=?", (order_id,))

        elif action == 'cancel':
            if order['status'] in ('received', 'completed'):
                raise Exception('已收货或已完成的订单不能取消')
            cursor.execute("UPDATE purchase_orders SET status='cancelled' WHERE id=?", (order_id,))

        elif action == 'update':
            if order['status'] != 'draft':
                raise Exception('只能编辑草稿状态的订单')
            cursor.execute("UPDATE purchase_orders SET supplier_id=?, order_date=?, paid_amount=?, notes=? WHERE id=?",
                         (data.get('supplier_id', order['supplier_id']),
                          data.get('order_date', order['order_date']),
                          data.get('paid_amount', order['paid_amount']),
                          data.get('notes', order['notes']), order_id))
            if 'items' in data:
                cursor.execute("DELETE FROM purchase_order_items WHERE purchase_order_id=?", (order_id,))
                total = 0
                for item in data['items']:
                    amount = round(item['price'] * item['qty'], 2)
                    total += amount
                    cursor.execute(
                        "INSERT INTO purchase_order_items (purchase_order_id, product_id, qty, price, amount) VALUES (?,?,?,?,?)",
                        (order_id, item['product_id'], item['qty'], item['price'], amount)
                    )
                cursor.execute("UPDATE purchase_orders SET total_amount=? WHERE id=?", (round(total, 2), order_id))

        conn.commit()
        return jsonify({'message': '操作成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()

@purchases_bp.route('/purchase-orders/<int:order_id>', methods=['DELETE'])
def delete_purchase_order(order_id):
    conn = get_db()
    cursor = conn.cursor()
    order = cursor.execute("SELECT * FROM purchase_orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        conn.close()
        return jsonify({'error': '订单不存在'}), 404
    if order['status'] not in ('draft', 'cancelled'):
        conn.close()
        return jsonify({'error': '只能删除草稿或已取消的订单'}), 400
    try:
        cursor.execute("DELETE FROM purchase_order_items WHERE purchase_order_id=?", (order_id,))
        cursor.execute("DELETE FROM purchase_orders WHERE id=?", (order_id,))
        conn.commit()
        return jsonify({'message': '删除成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()
