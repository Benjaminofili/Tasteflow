"""
Unit Tests - Database Models
Tests instantiation, relationships, and core logic for each model.
"""
import pytest
from app import db
from app.models import User, Restaurant, Category, FoodType, Dish, Order


def test_user_creation(init_database, app):
    """Test user creation and password hashing."""
    with app.app_context():
        owner = db.session.get(User, init_database['owner_id'])
        customer = db.session.get(User, init_database['customer_id'])

        assert User.query.count() == 2
        assert owner.email == "owner@test.com"
        assert owner.role == "owner"
        assert customer.role == "customer"

        # Test password hashing
        assert owner.password_hash != "password123"
        assert owner.check_password("password123") is True
        assert owner.check_password("wrongpassword") is False


def test_restaurant_creation(init_database, app):
    """Test restaurant and its relationship to owner."""
    with app.app_context():
        restaurant = db.session.get(Restaurant, init_database['restaurant_id'])
        owner = db.session.get(User, init_database['owner_id'])

        assert Restaurant.query.count() == 1
        assert restaurant.name == "Test Restaurant"
        assert restaurant.owner.id == owner.id
        assert restaurant.owner.name == "Test Owner"


def test_dish_creation(init_database, app):
    """Test dish creation and its FK relationships."""
    with app.app_context():
        dish = db.session.get(Dish, init_database['dish_id'])
        category = db.session.get(Category, init_database['category_id'])

        assert Dish.query.count() == 1
        assert dish.name == "Test Dish"
        assert float(dish.price) == 9.99
        assert dish.is_available is True
        assert dish.category.name == category.name


def test_order_creation(init_database, app):
    """Test order defaults and customer/restaurant FK relationships."""
    with app.app_context():
        from app import db
        order = Order(
            customer_id=init_database['customer_id'],
            restaurant_id=init_database['restaurant_id'],
            total_amount=15.99,
            delivery_address='456 Ave',
        )
        db.session.add(order)
        db.session.commit()

        saved = Order.query.first()
        assert saved is not None
        assert saved.status == 'pending'  # default value
        assert float(saved.total_amount) == 15.99
        assert saved.customer.email == "customer@test.com"
        assert saved.restaurant.name == "Test Restaurant"


def test_coupon_creation(init_database, app):
    """Test coupon model instantiation with correct field names."""
    with app.app_context():
        from app import db
        from app.models import Coupon
        coupon = Coupon(
            restaurant_id=init_database['restaurant_id'],
            code="SAVE20",
            discount_type="percent",   # 'percent' or 'fixed'
            discount_value=20.0,
            is_active=True
        )
        db.session.add(coupon)
        db.session.commit()

        saved = Coupon.query.filter_by(code="SAVE20").first()
        assert saved is not None
        assert saved.is_active is True
        assert float(saved.discount_value) == 20.0
