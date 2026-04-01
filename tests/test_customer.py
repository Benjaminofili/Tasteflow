"""
Integration Tests - Customer Routes
Tests dashboard access, cart, checkout, and access control.
"""
import pytest


def test_customer_dashboard_access(client, init_database):
    """Test that authenticated customers can access their dashboard."""
    with client:
        # Login
        client.post('/auth/login', data={
            'email': init_database['customer_email'],
            'password': init_database['password']
        }, follow_redirects=True)

        # Access dashboard
        response = client.get('/customer/dashboard')
        assert response.status_code == 200
        # Check for some generic dashboard content rather than specific restaurant name
        assert b'RegFood' in response.data or b'menu' in response.data.lower()


def test_unauthenticated_dashboard_redirect(client):
    """Test that unauthenticated users are redirected from the dashboard."""
    response = client.get('/customer/dashboard', follow_redirects=False)
    assert response.status_code == 302
    assert 'login' in response.headers['Location'].lower()


def test_dashboard_filters(client, init_database, app):
    """Test that dashboard filtering by category returns 200."""
    with app.app_context():
        from app import db
        from app.models import Restaurant, Category, Dish, User

        owner = db.session.get(User, init_database['owner_id'])
        
        # Add a second restaurant and category
        rest2 = Restaurant(owner_id=owner.id, name='Rest Two', address='456 Ave')
        cat2 = Category(name='Mexican')
        db.session.add_all([rest2, cat2])
        db.session.commit()
        
        cat1_id = init_database['category_id']

    with client:
        client.post('/auth/login', data={
            'email': init_database['customer_email'],
            'password': init_database['password']
        }, follow_redirects=True)

        # No filter
        res = client.get('/customer/dashboard')
        assert res.status_code == 200

        # Category filter
        res = client.get(f'/customer/dashboard?category_id={cat1_id}')
        assert res.status_code == 200


def test_add_to_cart(client, init_database):
    """Test the cart addition endpoint."""
    with client:
        # No login required for cart in this app's logic (session based)
        dish_id = init_database['dish_id']
        response = client.post(f'/customer/cart/add/{dish_id}', follow_redirects=True)
        assert response.status_code == 200

        response = client.get('/customer/cart')
        assert response.status_code == 200
        # The cart view should show the dish
        assert b'Test Dish' in response.data


def test_place_order(client, init_database, app):
    """Test the full checkout flow."""
    with client:
        # 1. Login
        client.post('/auth/login', data={
            'email': init_database['customer_email'],
            'password': init_database['password']
        }, follow_redirects=True)

        # 2. Add item to cart
        client.post(f'/customer/cart/add/{init_database["dish_id"]}', follow_redirects=True)

        # 3. Checkout (POST to checkout creates the order)
        # Note: the form field in customer.py is 'address' (optional, falls back to user's)
        response = client.post('/customer/checkout', data={
            'address': '123 Test Delivery St'
        }, follow_redirects=True)

        # Should be redirected to 'my-orders' (or checkout if it re-renders, but follow_redirects handles it)
        assert response.status_code == 200
        assert b'Order' in response.data or b'successfully' in response.data.lower()

    # 4. Verify order exists in DB
    with app.app_context():
        from app.models import Order
        order = Order.query.filter_by(customer_id=init_database['customer_id']).first()
        assert order is not None
        assert order.delivery_address == '123 Test Delivery St'


def test_newsletter_api(client):
    response = client.post('/customer/api/newsletter', json={'email': 'test@example.com'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True


def test_feedback_api(client):
    response = client.post('/customer/api/feedback', json={'name': 'Jane', 'rating': 5, 'comments': 'Great app!'})
    assert response.status_code == 200
    data = response.get_json()
    assert data['success'] is True
