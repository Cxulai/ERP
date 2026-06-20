from flask import Blueprint, request, jsonify
from database import get_db

customers_bp = Blueprint('customers', __name__)

@customers_bp.route('/customers')
def list_customers():
    search = request.args.get('search', '')
    conn = get_db()
    cursor = conn.cursor()
    if search:
        cursor.execute(
            "SELECT * FROM customers WHERE name LIKE ? OR phone LIKE ? OR contact_person LIKE ? ORDER BY id DESC",
            (f'%{search}%', f'%{search}%', f'%{search}%')
        )
    else:
        cursor.execute("SELECT * FROM customers ORDER BY id DESC")
    customers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(customers)

@customers_bp.route('/customers', methods=['POST'])
def create_customer():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO customers (name, contact_person, phone, email, address) VALUES (?,?,?,?,?)",
            (data['name'], data.get('contact_person', ''), data.get('phone', ''),
             data.get('email', ''), data.get('address', ''))
        )
        conn.commit()
        return jsonify({'id': cursor.lastrowid, 'message': '创建成功'}), 201
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()

@customers_bp.route('/customers/<int:customer_id>', methods=['PUT'])
def update_customer(customer_id):
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE customers SET name=?, contact_person=?, phone=?, email=?, address=? WHERE id=?",
            (data['name'], data.get('contact_person', ''), data.get('phone', ''),
             data.get('email', ''), data.get('address', ''), customer_id)
        )
        conn.commit()
        return jsonify({'message': '更新成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()

@customers_bp.route('/customers/<int:customer_id>', methods=['DELETE'])
def delete_customer(customer_id):
    conn = get_db()
    cursor = conn.cursor()
    orders = cursor.execute("SELECT COUNT(*) FROM sales_orders WHERE customer_id=?", (customer_id,)).fetchone()[0]
    if orders > 0:
        conn.close()
        return jsonify({'error': '该客户有销售订单，无法删除'}), 400
    try:
        cursor.execute("DELETE FROM customers WHERE id=?", (customer_id,))
        conn.commit()
        return jsonify({'message': '删除成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()
