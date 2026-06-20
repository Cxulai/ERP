from flask import Flask, render_template
from database import db, init_db
from routes.dashboard import dashboard_bp
from routes.products import products_bp
from routes.customers import customers_bp
from routes.suppliers import suppliers_bp
from routes.sales import sales_bp
from routes.purchases import purchases_bp
from routes.reports import reports_bp
import os

app = Flask(__name__)

# Database config: PostgreSQL when DATABASE_URL set (Vercel), SQLite otherwise (local)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'sqlite:///erp.db'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Register blueprints
app.register_blueprint(dashboard_bp, url_prefix='/api')
app.register_blueprint(products_bp, url_prefix='/api')
app.register_blueprint(customers_bp, url_prefix='/api')
app.register_blueprint(suppliers_bp, url_prefix='/api')
app.register_blueprint(sales_bp, url_prefix='/api')
app.register_blueprint(purchases_bp, url_prefix='/api')
app.register_blueprint(reports_bp, url_prefix='/api')

@app.route('/')
def index():
    return render_template('index.html')

# Init DB
init_db(app)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
