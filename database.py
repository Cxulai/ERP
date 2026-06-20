import sqlite3
from datetime import datetime, timedelta
import random

DB_PATH = 'erp.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            category TEXT DEFAULT '',
            unit TEXT DEFAULT '个',
            sale_price REAL NOT NULL DEFAULT 0,
            purchase_price REAL NOT NULL DEFAULT 0,
            stock_qty INTEGER NOT NULL DEFAULT 0,
            min_stock INTEGER NOT NULL DEFAULT 10,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_person TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            address TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_person TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            email TEXT DEFAULT '',
            address TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS sales_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT NOT NULL UNIQUE,
            customer_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            total_amount REAL NOT NULL DEFAULT 0,
            paid_amount REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'draft',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(id)
        );

        CREATE TABLE IF NOT EXISTS sales_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sales_order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            qty INTEGER NOT NULL,
            price REAL NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (sales_order_id) REFERENCES sales_orders(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS purchase_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_no TEXT NOT NULL UNIQUE,
            supplier_id INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            total_amount REAL NOT NULL DEFAULT 0,
            paid_amount REAL NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'draft',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (supplier_id) REFERENCES suppliers(id)
        );

        CREATE TABLE IF NOT EXISTS purchase_order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purchase_order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            qty INTEGER NOT NULL,
            price REAL NOT NULL,
            amount REAL NOT NULL,
            FOREIGN KEY (purchase_order_id) REFERENCES purchase_orders(id) ON DELETE CASCADE,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS inventory_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            change_type TEXT NOT NULL,
            qty INTEGER NOT NULL,
            before_qty INTEGER NOT NULL,
            after_qty INTEGER NOT NULL,
            reference TEXT DEFAULT '',
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id)
        );
    ''')

    # Seed data if empty
    if cursor.execute("SELECT COUNT(*) FROM products").fetchone()[0] == 0:
        _seed_data(conn)

    conn.commit()
    conn.close()

def _seed_data(conn):
    cursor = conn.cursor()
    now = datetime.now()
    date_str = now.strftime('%Y-%m-%d')

    # Products
    products = [
        ('P001', '螺丝刀套装', '工具', '套', 45.00, 28.00, 150, 20),
        ('P002', '不锈钢螺栓 M8', '紧固件', '个', 2.50, 1.20, 2000, 200),
        ('P003', 'LED灯泡 12W', '电器', '个', 18.00, 10.00, 300, 30),
        ('P004', '钢板 2mm', '原材料', '张', 120.00, 85.00, 200, 10),
        ('P005', '橡胶密封圈', '密封件', '个', 3.50, 1.80, 800, 100),
        ('P006', '电钻 D-100', '工具', '台', 380.00, 250.00, 100, 5),
        ('P007', '角铁 40x40', '原材料', '根', 35.00, 22.00, 200, 30),
        ('P008', '工业手套', '劳保', '双', 8.00, 4.50, 500, 50),
    ]
    cursor.executemany(
        "INSERT INTO products (code, name, category, unit, sale_price, purchase_price, stock_qty, min_stock) VALUES (?,?,?,?,?,?,?,?)",
        products
    )

    # Customers
    customers = [
        ('深圳华强电子有限公司', '张伟', '13800138001', 'zhangwei@huaqiang.cn', '深圳市福田区华强北路1001号'),
        ('上海建工集团', '李明', '13900139002', 'liming@shjg.com', '上海市浦东新区世纪大道200号'),
        ('广州天河机械设备公司', '王芳', '13700137003', 'wangfang@gzth.com', '广州市天河区中山大道西88号'),
        ('北京中关村科技有限公司', '赵强', '13600136004', 'zhaoq@zgctech.cn', '北京市海淀区中关村大街1号'),
    ]
    cursor.executemany(
        "INSERT INTO customers (name, contact_person, phone, email, address) VALUES (?,?,?,?,?)",
        customers
    )

    # Suppliers
    suppliers = [
        ('东莞永固五金制品厂', '陈志明', '13500135001', 'chenzm@yonggu.cn', '东莞市长安镇振安路168号'),
        ('佛山顺德钢材贸易公司', '刘建国', '13400134002', 'liujg@sdsteel.com', '佛山市顺德区乐从镇钢铁市场A区'),
        ('浙江温州电器批发城', '林小红', '13300133003', 'linxh@wzdq.cn', '温州市鹿城区车站大道99号'),
    ]
    cursor.executemany(
        "INSERT INTO suppliers (name, contact_person, phone, email, address) VALUES (?,?,?,?,?)",
        suppliers
    )

    # Sales Orders
    for i in range(1, 6):
        order_no = f'SO-{now.year}{now.month:02d}{now.day:02d}-{i:03d}'
        order_date = (now - timedelta(days=random.randint(0, 30))).strftime('%Y-%m-%d')
        customer_id = random.randint(1, 4)
        status = random.choice(['confirmed', 'shipped', 'completed'])
        cursor.execute(
            "INSERT INTO sales_orders (order_no, customer_id, order_date, total_amount, paid_amount, status, notes) VALUES (?,?,?,0,0,?,'')",
            (order_no, customer_id, order_date, status)
        )
        so_id = cursor.lastrowid
        total = 0
        for _ in range(random.randint(1, 4)):
            pid = random.randint(1, 8)
            qty = random.randint(2, 20)
            price = cursor.execute("SELECT sale_price FROM products WHERE id=?", (pid,)).fetchone()[0]
            amount = round(qty * price, 2)
            total += amount
            cursor.execute(
                "INSERT INTO sales_order_items (sales_order_id, product_id, qty, price, amount) VALUES (?,?,?,?,?)",
                (so_id, pid, qty, price, amount)
            )
            if status in ('confirmed', 'shipped', 'completed'):
                cursor.execute("UPDATE products SET stock_qty = stock_qty - ? WHERE id=?", (qty, pid))
                cursor.execute(
                    "INSERT INTO inventory_logs (product_id, change_type, qty, before_qty, after_qty, reference) VALUES (?, 'sale', ?, (SELECT stock_qty FROM products WHERE id=?) + ?, (SELECT stock_qty FROM products WHERE id=?), ?)",
                    (pid, qty, pid, qty, pid, order_no)
                )
        cursor.execute("UPDATE sales_orders SET total_amount=? WHERE id=?", (round(total, 2), so_id))
        # Set paid equal to total for completed orders
        if status == 'completed':
            cursor.execute("UPDATE sales_orders SET paid_amount=? WHERE id=?", (round(total, 2), so_id))
        elif status in ('confirmed', 'shipped'):
            cursor.execute("UPDATE sales_orders SET paid_amount=? WHERE id=?", (round(total * random.uniform(0.3, 0.8), 2), so_id))

    conn.commit()
