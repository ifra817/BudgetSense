"""
BudgetSense Flask Application
Main application entry point
"""

from flask import Flask, jsonify, send_from_directory, render_template
from flask_cors import CORS
import logging
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config_name=None):
    """
    Application factory function
    Creates and configures the Flask app
    """
    
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    
    # Pointing template_folder to the 'frontend' directory which is outside the 'backend' folder
    template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))
    
    app = Flask(__name__, template_folder=template_dir)
    
    # Load config
    if config_name == 'production':
        from config import ProductionConfig
        app.config.from_object(ProductionConfig)
    elif config_name == 'testing':
        from config import TestingConfig
        app.config.from_object(TestingConfig)
    else:
        from config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)
    
    # Enable CORS for frontend communication
    CORS(app)
    
    # Initialize database
    from db.connection import init_db, get_db
    init_db(app)
    
    # --- Blueprints (API Routes) ---
    from routes.auth import auth_bp
    from routes.expenses import expenses_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(expenses_bp)

    from routes.budgets import budgets_bp
    app.register_blueprint(budgets_bp)

    from routes.analytics import analytics_bp
    app.register_blueprint(analytics_bp)

    # --- Frontend View Routes ---
    @app.route('/')
    def index():
        """Serve the landing page"""
        return render_template('index.html')

    @app.route('/dashboard')
    def dashboard_page():
        """Serve the Dashboard HTML page"""
        return render_template('dashboard.html')

    @app.route('/login')
    def login_page():
        """Serve the Login HTML page"""
        return render_template('login.html')

    @app.route('/register')
    def register_page():
        """Serve the Register HTML page"""
        return render_template('register.html')

    @app.route('/history')
    def history_page():
        """Serve the History HTML page"""
        return render_template('history.html')

    @app.route('/budgets')
    def budget_settings_page():
        """Serve the Budget Settings HTML page"""
        return render_template('budget_settings.html')

    @app.route('/add-expense')
    def add_expense_page():
        """Serve the Add Expense HTML page"""
        return render_template('add_expense.html')
    
    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        """Check if API is running"""
        try:
            db = get_db()
            if db is not None:
                db.command('ping')
                return jsonify({
                    'status': 'healthy',
                    'message': 'API is running and connected to MongoDB'
                }), 200
            else:
                return jsonify({
                    'status': 'unhealthy',
                    'message': 'Database connection is None'
                }), 500
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return jsonify({
                'status': 'unhealthy',
                'message': str(e)
            }), 500
    
    logger.info(f"✅ Flask application initialized with templates at: {template_dir}")
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)