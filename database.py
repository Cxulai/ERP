from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import random
import os

db = SQLAlchemy()

# ── Models ──────────────────────────────────────────────

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(100), default='')
    unit = db.Column(db.String(20), default='个')
    sale_price = db.Column(db.Float, nullable=False, default=0)
    purchase_price = db.Column(db.Float, nullable=False, default=0)
    stock_qty = db.Column(db.Integer, nullable=False, default=0)
    min_stock = db.Column(db.Integer, nullable=False, default=10)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(100), default='')
    phone = db.Column(db.String(50), default='')
    email = db.Column(db.String(100), default='')
    address = db.Column(db.String(500), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Supplier(db.Model):
    __tablename__ = 'suppliers'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(200), nullable=False)
    contact_person = db.Column(db.String(100), default='')
    phone = db.Column(db.String(50), default='')
    email = db.Column(db.String(100), default='')
    address = db.Column(db.String(500), default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SalesOrder(db.Model):
    __tablename__ = 'sales_orders'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_no = db.Column(db.String(50), unique=True, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    order_date = db.Column(db.String(20), nullable=False)
    total_amount = db.Column(db.Float, nullable=False, default=0)
    paid_amount = db.Column(db.Float, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default='draft')
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    customer = db.relationship('Customer', backref='sales_orders')
    items = db.relationship('SalesOrderItem', backref='sales_order', cascade='all, delete-orphan')

class SalesOrderItem(db.Model):
    __tablename__ = 'sales_order_items'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    sales_order_id = db.Column(db.Integer, db.ForeignKey('sales_orders.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    product = db.relationship('Product')

class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    order_no = db.Column(db.String(50), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.id'), nullable=False)
    order_date = db.Column(db.String(20), nullable=False)
    total_amount = db.Column(db.Float, nullable=False, default=0)
    paid_amount = db.Column(db.Float, nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default='draft')
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    supplier = db.relationship('Supplier', backref='purchase_orders')
    items = db.relationship('PurchaseOrderItem', backref='purchase_order', cascade='all, delete-orphan')

class PurchaseOrderItem(db.Model):
    __tablename__ = 'purchase_order_items'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    purchase_order_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.id', ondelete='CASCADE'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    amount = db.Column(db.Float, nullable=False)
    product = db.relationship('Product')

class InventoryLog(db.Model):
    __tablename__ = 'inventory_logs'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    change_type = db.Column(db.String(30), nullable=False)
    qty = db.Column(db.Integer, nullable=False)
    before_qty = db.Column(db.Integer, nullable=False)
    after_qty = db.Column(db.Integer, nullable=False)
    reference = db.Column(db.String(100), default='')
    notes = db.Column(db.Text, default='')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    product = db.relationship('Product')

# ── Init ────────────────────────────────────────────────

def init_db(app):
    """Initialize database: create tables + seed if empty."""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        if Product.query.count() == 0:
            _seed_data()

def _seed_data():
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')

    products = [
        Product(code='P001', name='螺丝刀套装', category='工具', unit='套', sale_price=45.00, purchase_price=28.00, stock_qty=150, min_stock=20),
        Product(code='P002', name='不锈钢螺栓 M8', category='紧固件', unit='个', sale_price=2.50, purchase_price=1.20, stock_qty=2000, min_stock=200),
        Product(code='P003', name='LED灯泡 12W', category='电器', unit='个', sale_price=18.00, purchase_price=10.00, stock_qty=300, min_stock=30),
        Product(code='P004', name='钢板 2mm', category='原材料', unit='张', sale_price=120.00, purchase_price=85.00, stock_qty=200, min_stock=10),
        Product(code='P005', name='橡胶密封圈', category='密封件', unit='个', sale_price=3.50, purchase_price=1.80, stock_qty=800, min_stock=100),
        Product(code='P006', name='电钻 D-100', category='工具', unit='台', sale_price=380.00, purchase_price=250.00, stock_qty=100, min_stock=5),
        Product(code='P007', name='角铁 40x40', category='原材料', unit='根', sale_price=35.00, purchase_price=22.00, stock_qty=200, min_stock=30),
        Product(code='P008', name='工业手套', category='劳保', unit='双', sale_price=8.00, purchase_price=4.50, stock_qty=500, min_stock=50),
    ]
    db.session.add_all(products)
    db.session.flush()

    customers = [
        Customer(name='深圳华强电子有限公司', contact_person='张伟', phone='13800138001', email='zhangwei@huaqiang.cn', address='深圳市福田区华强北路1001号'),
        Customer(name='上海建工集团', contact_person='李明', phone='13900139002', email='liming@shjg.com', address='上海市浦东新区世纪大道200号'),
        Customer(name='广州天河机械设备公司', contact_person='王芳', phone='13700137003', email='wangfang@gzth.com', address='广州市天河区中山大道西88号'),
        Customer(name='北京中关村科技有限公司', contact_person='赵强', phone='13600136004', email='zhaoq@zgctech.cn', address='北京市海淀区中关村大街1号'),
    ]
    db.session.add_all(customers)
    db.session.flush()

    suppliers = [
        Supplier(name='东莞永固五金制品厂', contact_person='陈志明', phone='13500135001', email='chenzm@yonggu.cn', address='东莞市长安镇振安路168号'),
        Supplier(name='佛山顺德钢材贸易公司', contact_person='刘建国', phone='13400134002', email='liujg@sdsteel.com', address='佛山市顺德区乐从镇钢铁市场A区'),
        Supplier(name='浙江温州电器批发城', contact_person='林小红', phone='13300133003', email='linxh@wzdq.cn', address='温州市鹿城区车站大道99号'),
    ]
    db.session.add_all(suppliers)
    db.session.flush()

    # Sales orders with seed data
    for i in range(1, 6):
        order_no = f'SO-{now.year}{now.month:02d}{now.day:02d}-{i:03d}'
        order_date = (now - timedelta(days=random.randint(0, 30))).strftime('%Y-%m-%d')
        customer_id = random.randint(1, 4)
        status = random.choice(['confirmed', 'shipped', 'completed'])
        so = SalesOrder(order_no=order_no, customer_id=customer_id, order_date=order_date, total_amount=0, paid_amount=0, status=status)
        db.session.add(so)
        db.session.flush()
        total = 0
        for _ in range(random.randint(1, 4)):
            pid = random.randint(1, 8)
            qty = random.randint(2, 20)
            product = Product.query.get(pid)
            price = product.sale_price
            amount = round(qty * price, 2)
            total += amount
            db.session.add(SalesOrderItem(sales_order_id=so.id, product_id=pid, qty=qty, price=price, amount=amount))
            if status in ('confirmed', 'shipped', 'completed'):
                before_qty = product.stock_qty
                after_qty = before_qty - qty
                product.stock_qty = after_qty
                db.session.add(InventoryLog(product_id=pid, change_type='sale', qty=qty, before_qty=before_qty, after_qty=after_qty, reference=order_no))
        so.total_amount = round(total, 2)
        if status == 'completed':
            so.paid_amount = round(total, 2)
        elif status in ('confirmed', 'shipped'):
            so.paid_amount = round(total * random.uniform(0.3, 0.8), 2)

    db.session.commit()
