from flask import Flask, render_template
from routes.dashboard import dashboard_bp
from routes.products import products_bp
from routes.customers import customers_bp
from routes.suppliers import suppliers_bp
from routes.sales import sales_bp
from routes.purchases import purchases_bp
from routes.reports import reports_bp
import os

def create_app():
    app = Flask(__name__)

    # Database config: PostgreSQL when DATABASE_URL set (Vercel), SQLite otherwise (local)
    raw_url = os.environ.get('DATABASE_URL', 'sqlite:///erp.db')

    # Vercel Postgres uses 'postgres://' which SQLAlchemy 1.4+ rejects
    if raw_url.startswith('postgres://'):
        raw_url = raw_url.replace('postgres://', 'postgresql://', 1)

    # Add SSL for cloud PostgreSQL
    if 'postgresql://' in raw_url and 'sslmode=' not in raw_url:
        separator = '&' if '?' in raw_url else '?'
        raw_url += f'{separator}sslmode=require'

    app.config['SQLALCHEMY_DATABASE_URI'] = raw_url
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

    # Init DB inside app context
    from database import db, init_db
    db.init_app(app)
    with app.app_context():
        try:
            db.create_all()
            from database import Product
            if Product.query.count() == 0:
                from database import _seed_data
                _seed_data()
        except Exception as e:
            app.logger.error(f"DB init failed: {e}")

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
