from flask import Blueprint, request, jsonify
from database import db, Supplier, PurchaseOrder

suppliers_bp = Blueprint('suppliers', __name__)

@suppliers_bp.route('/suppliers')
def list_suppliers():
    search = request.args.get('search', '')
    q = Supplier.query
    if search:
        like = f'%{search}%'
        q = q.filter(db.or_(Supplier.name.like(like), Supplier.phone.like(like), Supplier.contact_person.like(like)))
    suppliers = q.order_by(Supplier.id.desc()).all()
    return jsonify([{
        'id': s.id, 'name': s.name, 'contact_person': s.contact_person,
        'phone': s.phone, 'email': s.email, 'address': s.address
    } for s in suppliers])

@suppliers_bp.route('/suppliers', methods=['POST'])
def create_supplier():
    data = request.json
    try:
        s = Supplier(
            name=data['name'], contact_person=data.get('contact_person', ''),
            phone=data.get('phone', ''), email=data.get('email', ''),
            address=data.get('address', '')
        )
        db.session.add(s)
        db.session.commit()
        return jsonify({'id': s.id, 'message': '创建成功'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@suppliers_bp.route('/suppliers/<int:supplier_id>', methods=['PUT'])
def update_supplier(supplier_id):
    data = request.json
    try:
        s = Supplier.query.get(supplier_id)
        if not s:
            return jsonify({'error': '供应商不存在'}), 404
        s.name = data['name']
        s.contact_person = data.get('contact_person', '')
        s.phone = data.get('phone', '')
        s.email = data.get('email', '')
        s.address = data.get('address', '')
        db.session.commit()
        return jsonify({'message': '更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@suppliers_bp.route('/suppliers/<int:supplier_id>', methods=['DELETE'])
def delete_supplier(supplier_id):
    if PurchaseOrder.query.filter_by(supplier_id=supplier_id).count() > 0:
        return jsonify({'error': '该供应商有采购订单，无法删除'}), 400
    try:
        Supplier.query.filter_by(id=supplier_id).delete()
        db.session.commit()
        return jsonify({'message': '删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
