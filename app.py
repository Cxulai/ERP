from flask import Flask, render_template, jsonify
from routes.dashboard import dashboard_bp
from routes.products import products_bp
from routes.customers import customers_bp
from routes.suppliers import suppliers_bp
from routes.sales import sales_bp
from routes.purchases import purchases_bp
from routes.reports import reports_bp
import os
import re

_is_vercel = bool(os.environ.get('VERCEL'))

def create_app():
    app = Flask(__name__)

    # Database config: PostgreSQL when DATABASE_URL set (Vercel), SQLite otherwise (local)
    raw_url = os.environ.get('DATABASE_URL', '')
    if not raw_url:
        # Vercel: use /tmp for SQLite (only writable path on serverless)
        # Local: use erp.db in project root
        db_path = '/tmp/erp.db' if _is_vercel else os.path.join(
            os.path.dirname(os.path.abspath(__file__)), 'erp.db')
        raw_url = f'sqlite:///{db_path}'

    # Vercel Postgres uses 'postgres://' which SQLAlchemy 1.4+ rejects.
    # pg8000 must be specified as the driver, else SQLAlchemy defaults to psycopg2.
    if raw_url.startswith('postgres://'):
        raw_url = raw_url.replace('postgres://', 'postgresql+pg8000://', 1)
    elif 'postgresql://' in raw_url and '+pg8000' not in raw_url:
        raw_url = raw_url.replace('postgresql://', 'postgresql+pg8000://', 1)

    # Strip sslmode= param — pg8000 doesn't understand it (libpq-only convention)
    raw_url = re.sub(r'[?&]sslmode=[^&]*', '', raw_url)
    # Clean up trailing ? or dangling & from sslmode removal
    raw_url = re.sub(r'\?&', '?', raw_url)
    raw_url = re.sub(r'\?$', '', raw_url)

    app.config['SQLALCHEMY_DATABASE_URI'] = raw_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # pg8000 SSL: use ssl_context=True, not sslmode=require (libpq-only)
    if 'postgresql' in raw_url:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'connect_args': {'ssl_context': True}
        }

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

    @app.route('/api/health')
    def health():
        """Health check — no DB required, for Vercel cold-start detection."""
        return jsonify({
            'status': 'ok',
            'vercel': _is_vercel,
            'db_type': 'postgresql' if 'postgresql' in raw_url else 'sqlite',
        })

    # Init DB inside app context
    from database import db, init_db
    with app.app_context():
        try:
            init_db(app)
        except Exception as e:
            app.logger.error(f"DB init failed: {e}")
            # App still serves: health check, static pages, index page
            # API routes will return 500 with descriptive error

    return app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
