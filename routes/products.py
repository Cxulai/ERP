from flask import Blueprint, request, jsonify
from database import get_db

products_bp = Blueprint('products', __name__)

@products_bp.route('/products')
def list_products():
    search = request.args.get('search', '')
    conn = get_db()
    cursor = conn.cursor()
    if search:
        cursor.execute(
            "SELECT * FROM products WHERE name LIKE ? OR code LIKE ? OR category LIKE ? ORDER BY id DESC",
            (f'%{search}%', f'%{search}%', f'%{search}%')
        )
    else:
        cursor.execute("SELECT * FROM products ORDER BY id DESC")
    products = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(products)

@products_bp.route('/products', methods=['POST'])
def create_product():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """INSERT INTO products (code, name, category, unit, sale_price, purchase_price, stock_qty, min_stock)
               VALUES (?,?,?,?,?,?,?,?)""",
            (data['code'], data['name'], data.get('category', ''),
             data.get('unit', '个'), data['sale_price'], data['purchase_price'],
             data.get('stock_qty', 0), data.get('min_stock', 10))
        )
        conn.commit()
        product_id = cursor.lastrowid
        # Log initial stock
        if data.get('stock_qty', 0) > 0:
            cursor.execute(
                "INSERT INTO inventory_logs (product_id, change_type, qty, before_qty, after_qty, reference, notes) VALUES (?, 'init', ?, 0, ?, '初始库存', '创建商品')",
                (product_id, data['stock_qty'], data['stock_qty'])
            )
            conn.commit()
        return jsonify({'id': product_id, 'message': '创建成功'}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()

@products_bp.route('/products/<int:product_id>', methods=['PUT'])
def update_product(product_id):
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            """UPDATE products SET code=?, name=?, category=?, unit=?, sale_price=?,
               purchase_price=?, min_stock=? WHERE id=?""",
            (data['code'], data['name'], data.get('category', ''),
             data.get('unit', '个'), data['sale_price'], data['purchase_price'],
             data.get('min_stock', 10), product_id)
        )
        conn.commit()
        return jsonify({'message': '更新成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()

@products_bp.route('/products/<int:product_id>', methods=['DELETE'])
def delete_product(product_id):
    conn = get_db()
    cursor = conn.cursor()
    # Check if product is used in orders
    so_items = cursor.execute("SELECT COUNT(*) FROM sales_order_items WHERE product_id=?", (product_id,)).fetchone()[0]
    po_items = cursor.execute("SELECT COUNT(*) FROM purchase_order_items WHERE product_id=?", (product_id,)).fetchone()[0]
    if so_items > 0 or po_items > 0:
        conn.close()
        return jsonify({'error': '该商品已在订单中使用，无法删除'}), 400
    try:
        cursor.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()
        return jsonify({'message': '删除成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()

@products_bp.route('/inventory-logs')
def list_inventory_logs():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        """SELECT il.*, p.name as product_name, p.code as product_code
           FROM inventory_logs il
           JOIN products p ON il.product_id = p.id
           ORDER BY il.created_at DESC LIMIT 200"""
    )
    logs = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(logs)

@products_bp.route('/products/<int:product_id>/stock', methods=['PUT'])
def adjust_stock(product_id):
    data = request.json
    change_qty = int(data['qty'])
    change_type = data.get('type', 'adjust')
    notes = data.get('notes', '')

    conn = get_db()
    cursor = conn.cursor()
    product = cursor.execute("SELECT * FROM products WHERE id=?", (product_id,)).fetchone()
    if not product:
        conn.close()
        return jsonify({'error': '商品不存在'}), 404

    before_qty = product['stock_qty']
    after_qty = before_qty + change_qty
    if after_qty < 0:
        conn.close()
        return jsonify({'error': '库存不足，当前库存: ' + str(before_qty)}), 400

    try:
        cursor.execute("UPDATE products SET stock_qty=? WHERE id=?", (after_qty, product_id))
        cursor.execute(
            "INSERT INTO inventory_logs (product_id, change_type, qty, before_qty, after_qty, reference, notes) VALUES (?,?,?,?,?,?,?)",
            (product_id, change_type, change_qty, before_qty, after_qty, '手动调整', notes)
        )
        conn.commit()
        return jsonify({'message': '库存调整成功', 'stock_qty': after_qty})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()
