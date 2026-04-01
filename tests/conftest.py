import pytest
from app import create_app, db as _db
from app.models import User, Restaurant, Category, Dish, FoodType


class TestConfig:
    """Minimal config for testing using in-memory SQLite."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False
    SECRET_KEY = 'test-secret-key'
    LOGIN_DISABLED = False
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    CLOUDINARY_URL = None
    DEBUG = False


@pytest.fixture(scope='function')
def app():
    """Create and configure a new Flask app instance for each test."""
    application = create_app(TestConfig)

    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """A test runner for the app's click commands."""
    return app.test_cli_runner()


@pytest.fixture
def init_database(app):
    """Seed the DB and return a dict of integer IDs (not model objects
    which become detached after the session commit).
    """
    with app.app_context():
        owner = User(name="Test Owner", email="owner@test.com", phone="1234567890", role="owner")
        owner.set_password("password123")

        customer = User(name="Test Customer", email="customer@test.com", phone="0987654321", role="customer")
        customer.set_password("password123")

        _db.session.add_all([owner, customer])
        _db.session.commit()

        restaurant = Restaurant(
            owner_id=owner.id,
            name="Test Restaurant",
            description="A great place to test food.",
            address="123 Test Ave"
        )
        _db.session.add(restaurant)

        category = Category(name="Test Category")
        food_type = FoodType(name="Test Type", is_approved=True)
        _db.session.add_all([category, food_type])
        _db.session.commit()

        dish = Dish(
            restaurant_id=restaurant.id,
            category_id=category.id,
            food_type_id=food_type.id,
            name="Test Dish",
            description="Delicious test dish",
            price=9.99,
            is_available=True
        )
        _db.session.add(dish)
        _db.session.commit()

        # Return IDs only - objects become detached when session is committed
        # Tests should re-query by ID within the app_context if needed
        return {
            'owner_id': owner.id,
            'customer_id': customer.id,
            'restaurant_id': restaurant.id,
            'category_id': category.id,
            'food_type_id': food_type.id,
            'dish_id': dish.id,
            # Keep email/name as plain strings for login
            'owner_email': 'owner@test.com',
            'customer_email': 'customer@test.com',
            'password': 'password123',
        }
