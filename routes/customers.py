from flask import Blueprint, request, jsonify
from database import db, Customer, SalesOrder

customers_bp = Blueprint('customers', __name__)

@customers_bp.route('/customers')
def list_customers():
    search = request.args.get('search', '')
    q = Customer.query
    if search:
        like = f'%{search}%'
        q = q.filter(db.or_(Customer.name.like(like), Customer.phone.like(like), Customer.contact_person.like(like)))
    customers = q.order_by(Customer.id.desc()).all()
    return jsonify([{
        'id': c.id, 'name': c.name, 'contact_person': c.contact_person,
        'phone': c.phone, 'email': c.email, 'address': c.address
    } for c in customers])

@customers_bp.route('/customers', methods=['POST'])
def create_customer():
    data = request.json
    try:
        c = Customer(
            name=data['name'], contact_person=data.get('contact_person', ''),
            phone=data.get('phone', ''), email=data.get('email', ''),
            address=data.get('address', '')
        )
        db.session.add(c)
        db.session.commit()
        return jsonify({'id': c.id, 'message': '创建成功'}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@customers_bp.route('/customers/<int:customer_id>', methods=['PUT'])
def update_customer(customer_id):
    data = request.json
    try:
        c = Customer.query.get(customer_id)
        if not c:
            return jsonify({'error': '客户不存在'}), 404
        c.name = data['name']
        c.contact_person = data.get('contact_person', '')
        c.phone = data.get('phone', '')
        c.email = data.get('email', '')
        c.address = data.get('address', '')
        db.session.commit()
        return jsonify({'message': '更新成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400

@customers_bp.route('/customers/<int:customer_id>', methods=['DELETE'])
def delete_customer(customer_id):
    if SalesOrder.query.filter_by(customer_id=customer_id).count() > 0:
        return jsonify({'error': '该客户有销售订单，无法删除'}), 400
    try:
        Customer.query.filter_by(id=customer_id).delete()
        db.session.commit()
        return jsonify({'message': '删除成功'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 400
