from flask import Flask, render_template
from database import init_db
from routes.dashboard import dashboard_bp
from routes.products import products_bp
from routes.customers import customers_bp
from routes.suppliers import suppliers_bp
from routes.sales import sales_bp
from routes.purchases import purchases_bp
from routes.reports import reports_bp

app = Flask(__name__)

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

if __name__ == '__main__':
    init_db()
    app.run(debug=True, host='0.0.0.0', port=5000)
