"""Tests for data models — SQLAlchemy ORM models."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Force in-memory SQLite for tests BEFORE importing app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from app import create_app
from database import db, Product, Customer, Supplier, SalesOrder, PurchaseOrder, InventoryLog


@pytest.fixture
def app():
    """Create app with test config (in-memory SQLite)."""
    app = create_app()
    with app.app_context():
        yield app
        db.drop_all()


@pytest.fixture
def clean_db(app):
    """Remove seed data before test."""
    with app.app_context():
        # Delete in reverse dependency order
        from database import SalesOrderItem, PurchaseOrderItem
        SalesOrderItem.query.delete()
        PurchaseOrderItem.query.delete()
        InventoryLog.query.delete()
        SalesOrder.query.delete()
        PurchaseOrder.query.delete()
        Product.query.delete()
        Customer.query.delete()
        Supplier.query.delete()
        db.session.commit()


# ── Product Model Tests ──

class TestProductModel:
    def test_create_product(self, app, clean_db):
        with app.app_context():
            product = Product(
                code="T001",
                name="测试商品",
                category="服装",
                unit="件",
                sale_price=99.0,
                purchase_price=50.0,
                stock_qty=100,
                min_stock=10,
            )
            db.session.add(product)
            db.session.commit()

            saved = Product.query.filter_by(code="T001").first()
            assert saved is not None
            assert saved.name == "测试商品"
            assert saved.sale_price == 99.0
            assert saved.stock_qty == 100

    def test_product_stock_update(self, app, clean_db):
        with app.app_context():
            product = Product(
                code="T002", name="库存测试", category="电子",
                unit="台", sale_price=500.0, purchase_price=300.0,
                stock_qty=50, min_stock=5,
            )
            db.session.add(product)
            db.session.commit()

            product.stock_qty -= 10
            db.session.commit()

            updated = db.session.get(Product, product.id)
            assert updated.stock_qty == 40

    def test_product_unique_code(self, app, clean_db):
        with app.app_context():
            p1 = Product(code="T003", name="A", category="X", unit="个",
                         sale_price=10, purchase_price=5, stock_qty=10, min_stock=1)
            p2 = Product(code="T003", name="B", category="Y", unit="个",
                         sale_price=20, purchase_price=10, stock_qty=5, min_stock=1)
            db.session.add(p1)
            db.session.commit()
            db.session.add(p2)
            with pytest.raises(Exception):
                db.session.commit()
            db.session.rollback()


# ── Customer Model Tests ──

class TestCustomerModel:
    def test_create_customer(self, app, clean_db):
        with app.app_context():
            customer = Customer(
                name="测试客户",
                contact_person="张三",
                phone="13800138000",
                email="test@example.com",
                address="测试地址",
            )
            db.session.add(customer)
            db.session.commit()

            saved = Customer.query.filter_by(name="测试客户").first()
            assert saved is not None
            assert saved.email == "test@example.com"

    def test_customer_required_fields(self, app, clean_db):
        with app.app_context():
            customer = Customer()
            db.session.add(customer)
            with pytest.raises(Exception):
                db.session.commit()
            db.session.rollback()


# ── Supplier Model Tests ──

class TestSupplierModel:
    def test_create_supplier(self, app, clean_db):
        with app.app_context():
            supplier = Supplier(
                name="测试供应商",
                contact_person="李四",
                phone="13900139000",
            )
            db.session.add(supplier)
            db.session.commit()

            saved = Supplier.query.filter_by(name="测试供应商").first()
            assert saved is not None
            assert saved.contact_person == "李四"


# ── Sales Order Model Tests ──

class TestSalesOrderModel:
    def test_create_sales_order(self, app, clean_db):
        with app.app_context():
            customer = Customer(name="订单客户", phone="13600136000")
            product = Product(code="T010", name="订单商品", category="服装",
                            unit="件", sale_price=100.0, purchase_price=60.0,
                            stock_qty=50, min_stock=5)
            db.session.add_all([customer, product])
            db.session.commit()

            order = SalesOrder(
                customer_id=customer.id,
                order_no="SO-T-001",
                order_date="2026-07-09",
                status="draft",
                total_amount=200.0,
                paid_amount=0.0,
            )
            db.session.add(order)
            db.session.commit()

            saved = SalesOrder.query.filter_by(order_no="SO-T-001").first()
            assert saved is not None
            assert saved.status == "draft"
            assert saved.total_amount == 200.0


# ── Purchase Order Model Tests ──

class TestPurchaseOrderModel:
    def test_create_purchase_order(self, app, clean_db):
        with app.app_context():
            supplier = Supplier(name="采购供应商", phone="13700137000")
            product = Product(code="T020", name="采购商品", category="电子",
                            unit="台", sale_price=800.0, purchase_price=500.0,
                            stock_qty=20, min_stock=2)
            db.session.add_all([supplier, product])
            db.session.commit()

            order = PurchaseOrder(
                supplier_id=supplier.id,
                order_no="PO-T-001",
                order_date="2026-07-09",
                status="draft",
                total_amount=500.0,
                paid_amount=0.0,
            )
            db.session.add(order)
            db.session.commit()

            saved = PurchaseOrder.query.filter_by(order_no="PO-T-001").first()
            assert saved is not None
            assert saved.status == "draft"


# ── Inventory Log Model Tests ──

class TestInventoryLog:
    def test_create_log(self, app, clean_db):
        with app.app_context():
            product = Product(code="T030", name="流水测试", category="其他",
                            unit="个", sale_price=10, purchase_price=5,
                            stock_qty=100, min_stock=1)
            db.session.add(product)
            db.session.commit()

            log = InventoryLog(
                product_id=product.id,
                change_type="入库",
                qty=10,
                before_qty=100,
                after_qty=110,
                notes="测试入库",
            )
            db.session.add(log)
            db.session.commit()

            saved = InventoryLog.query.filter_by(product_id=product.id).first()
            assert saved is not None
            assert saved.change_type == "入库"
            assert saved.qty == 10
            assert saved.after_qty == 110
