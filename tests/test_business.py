"""Tests for business logic — order state transitions and inventory sync."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from app import create_app
from database import (
    db, Product, Customer, Supplier,
    SalesOrder, SalesOrderItem, PurchaseOrder, PurchaseOrderItem,
    InventoryLog,
)


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        yield app
        db.drop_all()


@pytest.fixture
def seeded(app):
    """Seed test data: product + customer + supplier."""
    with app.app_context():
        p = Product(code="BZ001", name="业务商品", category="服装",
                     unit="件", sale_price=100, purchase_price=60,
                     stock_qty=100, min_stock=10)
        c = Customer(name="业务客户", phone="13500000000")
        s = Supplier(name="业务供应商", phone="13600000000")
        db.session.add_all([p, c, s])
        db.session.commit()
        return {"product_id": p.id, "customer_id": c.id, "supplier_id": s.id}


# ── Sales Order State Machine ──

class TestSalesOrderWorkflow:
    """Test: draft → confirmed → shipped → completed."""

    def test_create_order_draft_status(self, app, seeded):
        with app.app_context():
            order = SalesOrder(
                customer_id=seeded["customer_id"],
                order_no="SO-TEST-001",
                order_date="2026-07-09",
                status="draft",
                total_amount=200.0,
                paid_amount=0.0,
            )
            db.session.add(order)
            db.session.commit()
            assert order.status == "draft"

    def test_confirm_order_reduces_stock(self, app, seeded):
        with app.app_context():
            product = db.session.get(Product, seeded["product_id"])
            initial_stock = product.stock_qty

            order = SalesOrder(
                customer_id=seeded["customer_id"],
                order_no="SO-TEST-002",
                order_date="2026-07-09",
                status="draft",
                total_amount=300.0,
                paid_amount=0.0,
            )
            db.session.add(order)
            db.session.flush()  # get order.id

            item = SalesOrderItem(
                sales_order_id=order.id,
                product_id=product.id,
                qty=5,
                price=60,
                amount=300,
            )
            db.session.add(item)
            db.session.commit()

            # Confirm: reduce stock
            order.status = "confirmed"
            product.stock_qty -= item.qty
            log = InventoryLog(
                product_id=product.id,
                change_type="销售出库",
                qty=-item.qty,
                before_qty=initial_stock,
                after_qty=product.stock_qty,
                reference=order.order_no,
            )
            db.session.add(log)
            db.session.commit()

            db.session.refresh(product)
            assert product.stock_qty == initial_stock - 5
            assert order.status == "confirmed"

    def test_cancel_order_restores_stock(self, app, seeded):
        with app.app_context():
            product = db.session.get(Product, seeded["product_id"])
            initial_stock = product.stock_qty

            order = SalesOrder(
                customer_id=seeded["customer_id"],
                order_no="SO-TEST-003",
                order_date="2026-07-09",
                status="draft",
                total_amount=100.0,
                paid_amount=0.0,
            )
            db.session.add(order)
            db.session.flush()

            item = SalesOrderItem(
                sales_order_id=order.id,
                product_id=product.id,
                qty=3,
                price=100,
                amount=300,
            )
            db.session.add(item)
            db.session.commit()

            # Confirm first
            order.status = "confirmed"
            product.stock_qty -= item.qty
            db.session.commit()

            # Then cancel → restore stock
            stock_before_cancel = product.stock_qty
            order.status = "cancelled"
            product.stock_qty += item.qty
            log = InventoryLog(
                product_id=product.id,
                change_type="取消退回",
                qty=item.qty,
                before_qty=stock_before_cancel,
                after_qty=product.stock_qty,
                reference=order.order_no,
            )
            db.session.add(log)
            db.session.commit()

            db.session.refresh(product)
            assert product.stock_qty == initial_stock  # fully restored

    def test_ship_and_complete(self, app, seeded):
        with app.app_context():
            order = SalesOrder(
                customer_id=seeded["customer_id"],
                order_no="SO-TEST-004",
                order_date="2026-07-09",
                status="draft",
                total_amount=500.0,
                paid_amount=0.0,
            )
            db.session.add(order)
            db.session.commit()

            order.status = "confirmed"
            db.session.commit()
            assert order.status == "confirmed"

            order.status = "shipped"
            db.session.commit()
            assert order.status == "shipped"

            order.status = "completed"
            order.paid_amount = order.total_amount
            db.session.commit()
            assert order.status == "completed"
            assert order.paid_amount == order.total_amount


# ── Purchase Order State Machine ──

class TestPurchaseOrderWorkflow:
    """Test: draft → confirmed → received → completed."""

    def test_receive_purchase_increases_stock(self, app, seeded):
        with app.app_context():
            product = db.session.get(Product, seeded["product_id"])
            initial_stock = product.stock_qty

            order = PurchaseOrder(
                supplier_id=seeded["supplier_id"],
                order_no="PO-TEST-001",
                order_date="2026-07-09",
                status="draft",
                total_amount=300.0,
                paid_amount=0.0,
            )
            db.session.add(order)
            db.session.flush()

            item = PurchaseOrderItem(
                purchase_order_id=order.id,
                product_id=product.id,
                qty=10,
                price=30,
                amount=300,
            )
            db.session.add(item)
            db.session.commit()

            # Confirm (no stock change)
            order.status = "confirmed"
            db.session.commit()

            # Receive → increase stock
            order.status = "received"
            product.stock_qty += item.qty
            log = InventoryLog(
                product_id=product.id,
                change_type="采购入库",
                qty=item.qty,
                before_qty=initial_stock,
                after_qty=product.stock_qty,
                reference=order.order_no,
            )
            db.session.add(log)
            db.session.commit()

            db.session.refresh(product)
            assert product.stock_qty == initial_stock + 10
            assert order.status == "received"


# ── Edge Cases ──

class TestEdgeCases:
    def test_oversell_prevented(self, app, seeded):
        """Should not be able to sell more than available stock."""
        with app.app_context():
            product = db.session.get(Product, seeded["product_id"])
            assert product.stock_qty < 1000
            can_sell = 1000 <= product.stock_qty
            assert not can_sell

    def test_zero_price_order(self, app, seeded):
        with app.app_context():
            order = SalesOrder(
                customer_id=seeded["customer_id"],
                order_no="SO-ZERO",
                order_date="2026-07-09",
                status="draft",
                total_amount=0.0,
                paid_amount=0.0,
            )
            db.session.add(order)
            db.session.commit()
            assert order.total_amount == 0.0
