from flask import Blueprint, request, jsonify
from database import get_db
from datetime import datetime

sales_bp = Blueprint('sales', __name__)

@sales_bp.route('/sales-orders')
def list_sales_orders():
    search = request.args.get('search', '')
    status = request.args.get('status', '')
    conn = get_db()
    cursor = conn.cursor()
    query = """SELECT so.*, c.name as customer_name
               FROM sales_orders so
               JOIN customers c ON so.customer_id = c.id WHERE 1=1"""
    params = []
    if search:
        query += " AND (so.order_no LIKE ? OR c.name LIKE ?)"
        params.extend([f'%{search}%', f'%{search}%'])
    if status:
        query += " AND so.status = ?"
        params.append(status)
    query += " ORDER BY so.created_at DESC"
    cursor.execute(query, params)
    orders = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(orders)

@sales_bp.route('/sales-orders/<int:order_id>')
def get_sales_order(order_id):
    conn = get_db()
    cursor = conn.cursor()
    order = cursor.execute(
        """SELECT so.*, c.name as customer_name
           FROM sales_orders so JOIN customers c ON so.customer_id = c.id
           WHERE so.id=?""", (order_id,)
    ).fetchone()
    if not order:
        conn.close()
        return jsonify({'error': '订单不存在'}), 404
    items = cursor.execute(
        """SELECT soi.*, p.name as product_name, p.code as product_code, p.unit
           FROM sales_order_items soi JOIN products p ON soi.product_id = p.id
           WHERE soi.sales_order_id=?""", (order_id,)
    ).fetchall()
    conn.close()
    return jsonify({
        'order': dict(order),
        'items': [dict(item) for item in items]
    })

@sales_bp.route('/sales-orders', methods=['POST'])
def create_sales_order():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        # Generate order number
        now = datetime.now()
        count = cursor.execute("SELECT COUNT(*) FROM sales_orders").fetchone()[0] + 1
        order_no = f'SO-{now.year}{now.month:02d}{now.day:02d}-{count:03d}'

        cursor.execute(
            "INSERT INTO sales_orders (order_no, customer_id, order_date, total_amount, paid_amount, status, notes) VALUES (?,?,?,?,?,?,?)",
            (order_no, data['customer_id'], data['order_date'], 0, data.get('paid_amount', 0), 'draft', data.get('notes', ''))
        )
        order_id = cursor.lastrowid
        total = 0

        for item in data['items']:
            product = cursor.execute("SELECT * FROM products WHERE id=?", (item['product_id'],)).fetchone()
            if not product:
                raise Exception(f"商品 {item['product_id']} 不存在")
            price = item['price']
            qty = int(item['qty'])
            amount = round(price * qty, 2)
            total += amount
            cursor.execute(
                "INSERT INTO sales_order_items (sales_order_id, product_id, qty, price, amount) VALUES (?,?,?,?,?)",
                (order_id, item['product_id'], qty, price, amount)
            )

        cursor.execute("UPDATE sales_orders SET total_amount=? WHERE id=?", (round(total, 2), order_id))
        conn.commit()

        return jsonify({'id': order_id, 'order_no': order_no, 'message': '创建成功'}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()

@sales_bp.route('/sales-orders/<int:order_id>', methods=['PUT'])
def update_sales_order(order_id):
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        order = cursor.execute("SELECT * FROM sales_orders WHERE id=?", (order_id,)).fetchone()
        if not order:
            conn.close()
            return jsonify({'error': '订单不存在'}), 404

        action = data.get('action', 'update')

        if action == 'confirm':
            # Confirm order: reduce stock
            if order['status'] != 'draft':
                raise Exception('只能确认草稿状态的订单')
            items = cursor.execute("SELECT * FROM sales_order_items WHERE sales_order_id=?", (order_id,)).fetchall()
            for item in items:
                product = cursor.execute("SELECT * FROM products WHERE id=?", (item['product_id'],)).fetchone()
                if product['stock_qty'] < item['qty']:
                    raise Exception(f"商品 {product['name']} 库存不足 (当前: {product['stock_qty']}, 需要: {item['qty']})")
                before_qty = product['stock_qty']
                after_qty = before_qty - item['qty']
                cursor.execute("UPDATE products SET stock_qty=? WHERE id=?", (after_qty, item['product_id']))
                cursor.execute(
                    "INSERT INTO inventory_logs (product_id, change_type, qty, before_qty, after_qty, reference) VALUES (?, 'sale', ?, ?, ?, ?)",
                    (item['product_id'], item['qty'], before_qty, after_qty, order['order_no'])
                )
            cursor.execute("UPDATE sales_orders SET status='confirmed' WHERE id=?", (order_id,))

        elif action == 'ship':
            if order['status'] != 'confirmed':
                raise Exception('只能发货已确认的订单')
            cursor.execute("UPDATE sales_orders SET status='shipped' WHERE id=?", (order_id,))

        elif action == 'complete':
            if order['status'] not in ('confirmed', 'shipped'):
                raise Exception('只能完成已确认或已发货的订单')
            cursor.execute("UPDATE sales_orders SET status='completed', paid_amount=total_amount WHERE id=?", (order_id,))

        elif action == 'cancel':
            if order['status'] in ('completed',):
                raise Exception('已完成的订单不能取消')
            # Restore stock if was confirmed
            if order['status'] in ('confirmed', 'shipped'):
                items = cursor.execute("SELECT * FROM sales_order_items WHERE sales_order_id=?", (order_id,)).fetchall()
                for item in items:
                    product = cursor.execute("SELECT * FROM products WHERE id=?", (item['product_id'],)).fetchone()
                    before_qty = product['stock_qty']
                    after_qty = before_qty + item['qty']
                    cursor.execute("UPDATE products SET stock_qty=? WHERE id=?", (after_qty, item['product_id']))
                    cursor.execute(
                        "INSERT INTO inventory_logs (product_id, change_type, qty, before_qty, after_qty, reference) VALUES (?, 'cancel_return', ?, ?, ?, ?)",
                        (item['product_id'], item['qty'], before_qty, after_qty, order['order_no'])
                    )
            cursor.execute("UPDATE sales_orders SET status='cancelled' WHERE id=?", (order_id,))

        elif action == 'update':
            # Update order info (for draft orders only)
            if order['status'] != 'draft':
                raise Exception('只能编辑草稿状态的订单')
            cursor.execute("UPDATE sales_orders SET customer_id=?, order_date=?, paid_amount=?, notes=? WHERE id=?",
                         (data.get('customer_id', order['customer_id']),
                          data.get('order_date', order['order_date']),
                          data.get('paid_amount', order['paid_amount']),
                          data.get('notes', order['notes']), order_id))
            if 'items' in data:
                # Remove old items
                cursor.execute("DELETE FROM sales_order_items WHERE sales_order_id=?", (order_id,))
                total = 0
                for item in data['items']:
                    amount = round(item['price'] * item['qty'], 2)
                    total += amount
                    cursor.execute(
                        "INSERT INTO sales_order_items (sales_order_id, product_id, qty, price, amount) VALUES (?,?,?,?,?)",
                        (order_id, item['product_id'], item['qty'], item['price'], amount)
                    )
                cursor.execute("UPDATE sales_orders SET total_amount=? WHERE id=?", (round(total, 2), order_id))

        conn.commit()
        return jsonify({'message': '操作成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()

@sales_bp.route('/sales-orders/<int:order_id>', methods=['DELETE'])
def delete_sales_order(order_id):
    conn = get_db()
    cursor = conn.cursor()
    order = cursor.execute("SELECT * FROM sales_orders WHERE id=?", (order_id,)).fetchone()
    if not order:
        conn.close()
        return jsonify({'error': '订单不存在'}), 404
    if order['status'] not in ('draft', 'cancelled'):
        conn.close()
        return jsonify({'error': '只能删除草稿或已取消的订单'}), 400
    try:
        cursor.execute("DELETE FROM sales_order_items WHERE sales_order_id=?", (order_id,))
        cursor.execute("DELETE FROM sales_orders WHERE id=?", (order_id,))
        conn.commit()
        return jsonify({'message': '删除成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()
