"""Tests for RESTful API endpoints."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest
from app import create_app
from database import db, Product, Customer, Supplier


@pytest.fixture
def app():
    app = create_app()
    with app.app_context():
        # Seed already done by create_app(), add extra test data
        p = Product(code="API001", name="API商品", category="测试",
                     unit="件", sale_price=100, purchase_price=50,
                     stock_qty=50, min_stock=5)
        c = Customer(name="API客户", phone="13800000000")
        s = Supplier(name="API供应商", phone="13900000000")
        db.session.add_all([p, c, s])
        db.session.commit()
        yield app
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


# ── Dashboard API ──

class TestDashboardAPI:
    def test_get_dashboard(self, client):
        resp = client.get("/api/dashboard")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "product_count" in data
        assert "customer_count" in data
        assert "supplier_count" in data

    def test_dashboard_returns_json(self, client):
        resp = client.get("/api/dashboard")
        assert "application/json" in resp.content_type

    def test_dashboard_has_low_stock(self, client):
        resp = client.get("/api/dashboard")
        data = resp.get_json()
        assert "low_stock" in data
        assert isinstance(data["low_stock"], list)


# ── Products API ──

class TestProductsAPI:
    def test_list_products(self, client):
        resp = client.get("/api/products")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) >= 1

    def test_create_product(self, client):
        resp = client.post("/api/products", json={
            "code": "API002",
            "name": "新商品",
            "category": "测试",
            "unit": "件",
            "sale_price": 200,
            "purchase_price": 100,
            "stock_qty": 30,
            "min_stock": 3,
        })
        assert resp.status_code == 201

    def test_update_product(self, client):
        resp = client.put("/api/products/1", json={
            "code": "P001",
            "name": "改名商品",
            "sale_price": 150,
            "purchase_price": 28,
        })
        assert resp.status_code == 200

    def test_delete_product(self, client):
        # Product with code "API001" is id=9 (after 8 seed products)
        # Use the list endpoint to find the ID
        list_resp = client.get("/api/products")
        products = list_resp.get_json()
        api_product = next((p for p in products if p["code"] == "API001"), None)
        if api_product:
            resp = client.delete(f"/api/products/{api_product['id']}")
            assert resp.status_code == 200


# ── Customers API ──

class TestCustomersAPI:
    def test_list_customers(self, client):
        resp = client.get("/api/customers")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) >= 1

    def test_create_customer(self, client):
        resp = client.post("/api/customers", json={
            "name": "新客户",
            "phone": "13700000000",
            "email": "new@example.com",
        })
        assert resp.status_code == 201


# ── Suppliers API ──

class TestSuppliersAPI:
    def test_list_suppliers(self, client):
        resp = client.get("/api/suppliers")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data) >= 1


# ── Sales Orders API ──

class TestSalesOrdersAPI:
    def test_list_orders(self, client):
        resp = client.get("/api/sales-orders")
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), list)

    def test_create_order(self, client):
        resp = client.post("/api/sales-orders", json={
            "customer_id": 1,
            "order_date": "2026-07-09",
            "items": [{"product_id": 1, "qty": 2, "price": 100}],
        })
        assert resp.status_code == 201


# ── Reports API ──

class TestReportsAPI:
    def test_get_reports(self, client):
        resp = client.get("/api/reports")
        assert resp.status_code == 200
        assert isinstance(resp.get_json(), dict)
