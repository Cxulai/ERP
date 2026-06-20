from flask import Blueprint, request, jsonify
from database import get_db

suppliers_bp = Blueprint('suppliers', __name__)

@suppliers_bp.route('/suppliers')
def list_suppliers():
    search = request.args.get('search', '')
    conn = get_db()
    cursor = conn.cursor()
    if search:
        cursor.execute(
            "SELECT * FROM suppliers WHERE name LIKE ? OR phone LIKE ? OR contact_person LIKE ? ORDER BY id DESC",
            (f'%{search}%', f'%{search}%', f'%{search}%')
        )
    else:
        cursor.execute("SELECT * FROM suppliers ORDER BY id DESC")
    suppliers = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(suppliers)

@suppliers_bp.route('/suppliers', methods=['POST'])
def create_supplier():
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO suppliers (name, contact_person, phone, email, address) VALUES (?,?,?,?,?)",
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

@suppliers_bp.route('/suppliers/<int:supplier_id>', methods=['PUT'])
def update_supplier(supplier_id):
    data = request.json
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE suppliers SET name=?, contact_person=?, phone=?, email=?, address=? WHERE id=?",
            (data['name'], data.get('contact_person', ''), data.get('phone', ''),
             data.get('email', ''), data.get('address', ''), supplier_id)
        )
        conn.commit()
        return jsonify({'message': '更新成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()

@suppliers_bp.route('/suppliers/<int:supplier_id>', methods=['DELETE'])
def delete_supplier(supplier_id):
    conn = get_db()
    cursor = conn.cursor()
    orders = cursor.execute("SELECT COUNT(*) FROM purchase_orders WHERE supplier_id=?", (supplier_id,)).fetchone()[0]
    if orders > 0:
        conn.close()
        return jsonify({'error': '该供应商有采购订单，无法删除'}), 400
    try:
        cursor.execute("DELETE FROM suppliers WHERE id=?", (supplier_id,))
        conn.commit()
        return jsonify({'message': '删除成功'})
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 400
    finally:
        conn.close()
