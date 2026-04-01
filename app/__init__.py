from flask import Flask, session, request, render_template
from flask_sqlalchemy import SQLAlchemy
import cloudinary
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from flask_cors import CORS
from config import Config
from datetime import datetime

from sqlalchemy import MetaData

naming_convention = {
    "ix": 'ix_%(column_0_label)s',
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}

db = SQLAlchemy(metadata=MetaData(naming_convention=naming_convention))
login_manager = LoginManager()
migrate = Migrate()
limiter = Limiter(key_func=get_remote_address)
csrf = CSRFProtect()
mail = Mail()

def create_app(config_class=Config):
    """
    Application Factory - Configures and initializes the Flask app.
    Sets up SQLAlchemy, LoginManager, Migrations, Rate Limiting, 
    CSRF Protection, and Mail Services.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    
    # Initialize CORS
    import os
    CORS(app, resources={
        r"/api/*": {
            "origins": os.environ.get('FRONTEND_URL', '*'),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"]
        }
    })
    
    # Configure Cloudinary
    if app.config.get('CLOUDINARY_URL'):
        cloudinary.config(cloudinary_url=app.config.get('CLOUDINARY_URL'))
    
    # Configure login
    login_manager.login_view = 'pages.login'
    login_manager.login_message = 'Please log in to access this page.'

    # Register blueprints
    from app.routes import auth, customer, owner, admin, pages
    app.register_blueprint(pages.bp)
    app.register_blueprint(auth.bp)
    app.register_blueprint(customer.bp)
    app.register_blueprint(owner.bp)
    app.register_blueprint(admin.bp)

    # --- Error Handlers ---
    @app.errorhandler(404)
    def not_found_error(error):
        from flask import request
        app.logger.error(f"404 Error: {request.method} {request.path}")
        return {'success': False, 'error': f"Not found: {request.path}"}, 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {'success': False, 'error': 'Internal server error'}, 500

    @app.errorhandler(403)
    def forbidden_error(error):
        return {'success': False, 'error': 'Forbidden'}, 403

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return {'success': False, 'error': 'File too large'}, 413

    @app.errorhandler(429)
    def ratelimit_handler(e):
        return {'success': False, 'error': 'Rate limit exceeded. Please try again later.'}, 429

    # Render Uptime Cron Route
    @app.route('/ping')
    def ping():
        return "pong", 200

    # --- CLI Commands ---
    import click
    @app.cli.command("init-db")
    def init_db():
        """Initialize the database with default data."""
        # Note: In migration flow, tables are created by flask db upgrade.
        # This just runs the seeding logic.
        _auto_seed()
        click.echo("Database initialized with default data.")

    @app.cli.command("create-admin")
    @click.option("--name", prompt="Admin name", help="The name of the admin.")
    @click.option("--email", prompt="Admin email", help="The email of the admin.")
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(name, email, password):
        """Create a new admin user."""
        from app.models import User
        if User.query.filter_by(email=email).first():
            click.echo(f"Error: User with email {email} already exists.")
            return
        
        admin = User(name=name, email=email, role='admin')
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo(f"Admin user {email} created successfully.")

    @app.cli.command("test-db")
    def test_db():
        """Test database connection."""
        try:
            db.session.execute(db.text('SELECT 1'))
            click.echo("✅ Database connection successful!")
        except Exception as e:
            click.echo(f"❌ Database connection failed: {e}")

    @app.shell_context_processor
    def make_shell_context():
        from app import models
        return {
            'db': db,
            'User': models.User,
            'Restaurant': models.Restaurant,
            'Dish': models.Dish,
            'Order': models.Order,
            'Category': models.Category
        }

    return app

def _auto_seed():
    """Seed the database with initial data only if it is empty."""
    from app.models import User, Category, FoodType, Restaurant, Dish
    from werkzeug.security import generate_password_hash
    import logging
    log = logging.getLogger(__name__)

    if Category.query.first():
        return

    log.info("Empty database detected – running auto-seed...")
    for name in ["Biryani", "Burger", "Chicken", "Pizza", "Kebab",
                 "Chinese", "Desserts", "Drinks", "Salads", "Sandwiches",
                 "Sushi", "Seafood", "Pasta", "Breakfast", "Vegan"]:
        db.session.add(Category(name=name))

    for name in ["Veg", "Non-Veg", "Vegan", "Gluten-Free", "Halal", "Kosher"]:
        db.session.add(FoodType(name=name, is_approved=True))

    if not User.query.filter_by(email="admin@regfood.com").first():
        db.session.add(User(
            name="RegFood Admin", email="admin@regfood.com",
            password_hash=generate_password_hash("Admin@12345"),
            role='admin', phone='+1000000000', address='RegFood HQ'
        ))

    owner = User(
        name="RegFood Kitchen", email="owner@regfood.com",
        password_hash=generate_password_hash("Owner@12345"),
        role='owner', phone='+1000000001', address='123 Food Street'
    )
    db.session.add(owner)
    db.session.flush()

    restaurant = Restaurant(
        owner_id=owner.id, name="RegFood Kitchen",
        address="123 Food Street, City Centre", contact="+1000000001",
        description="The flagship RegFood restaurant serving delicious meals.",
        logo_url="/static/regfood/images/breadcrumb_bg.jpg"
    )
    db.session.add(restaurant)
    db.session.flush()

    db.session.add(User(
        name="RegFood Customer", email="customer@regfood.com",
        password_hash=generate_password_hash("Customer@12345"),
        role='customer', phone='+1000000002', address='456 Maple Avenue'
    ))

    db.session.flush()
    biryani = Category.query.filter_by(name="Biryani").first()
    burger  = Category.query.filter_by(name="Burger").first()
    chicken = Category.query.filter_by(name="Chicken").first()
    nonveg  = FoodType.query.filter_by(name="Non-Veg").first()
    veg     = FoodType.query.filter_by(name="Veg").first()

    for name, price, cat, ftype, desc in [
        ("Hyderabadi Biryani", 12.99, biryani, nonveg,
         "Authentic slow-cooked biryani with tender lamb and aromatic spices."),
        ("Chicken Nuggets", 8.99, chicken, nonveg,
         "Crispy golden chicken nuggets served with dipping sauce."),
        ("Spicy Burger", 9.99, burger, nonveg,
         "A juicy double-stacked spicy beef burger with jalapeños."),
        ("Fried Chicken", 10.99, chicken, nonveg,
         "Southern-style crispy fried chicken, golden perfection."),
        ("Mozzarella Sticks", 6.99, chicken, veg,
         "Gooey mozzarella wrapped in a crispy golden crust."),
        ("Popcorn Chicken", 7.99, chicken, nonveg,
         "Bite-sized popcorn chicken, perfectly seasoned."),
    ]:
        db.session.add(Dish(
            restaurant_id=restaurant.id, name=name, price=price,
            description=desc, category=cat, food_type=ftype,
            image_url="/static/regfood/images/menu2_img_1.jpg",
            is_available=True
        ))

    db.session.commit()
    log.info("Auto-seed complete. Admin: admin@regfood.com / Admin@12345")