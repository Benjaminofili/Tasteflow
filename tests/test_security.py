"""
Security Tests - Access Control & Authorization
Tests for "misuse" vectors like cross-role access and ID manipulation.
"""
import pytest
from app.models import User, Order, Restaurant, Dish


def test_unauthorized_guest_redirect(client):
    """Test that guests are redirected from protected routes."""
    protected_urls = [
        '/customer/dashboard',
        '/customer/my-orders',
        '/customer/checkout',
        '/owner/dashboard',
        '/owner/orders',
        '/owner/coupons'
    ]
    for url in protected_urls:
        response = client.get(url, follow_redirects=False)
        assert response.status_code == 302
        assert 'login' in response.headers['Location'].lower()


def test_cross_role_access_blocked(client, init_database):
    """Test that customers cannot access owner routes and vice-versa."""
    # 1. Login as Customer
    with client:
        client.post('/auth/login', data={
            'email': init_database['customer_email'],
            'password': init_database['password']
        })
        
        # Try to access owner dashboard
        response = client.get('/owner/dashboard', follow_redirects=False)
        assert response.status_code == 302
        # Should be redirected to index or login with "Access Denied"
        
        # Try to access owner orders
        response = client.get('/owner/orders', follow_redirects=False)
        assert response.status_code == 302


def test_cross_customer_order_view_blocked(client, init_database, app):
    """Test that Customer A cannot view Customer B's order invoice."""
    # 1. Create a second customer and an order for them
    with app.app_context():
        from app import db
        user_b = User(name="User B", email="userb@test.com", role="customer")
        user_b.set_password("password123")
        db.session.add(user_b)
        db.session.commit()
        
        order_b = Order(
            customer_id=user_b.id,
            restaurant_id=init_database['restaurant_id'],
            total_amount=50.0,
            status='pending',
            delivery_address='Street B'
        )
        db.session.add(order_b)
        db.session.commit()
        order_b_id = order_b.id

    # 2. Login as Customer A (from init_database)
    with client:
        client.post('/auth/login', data={
            'email': init_database['customer_email'],
            'password': init_database['password']
        })
        
        # Try to view User B's order
        response = client.get(f'/customer/order/{order_b_id}', follow_redirects=False)
        # Should redirect to 'my_orders' with a flash message
        assert response.status_code == 302
        assert '/customer/my-orders' in response.headers['Location']


def test_cross_owner_resource_manipulation_blocked(client, init_database, app):
    """Test that Owner A cannot delete or update Owner B's resources."""
    # 1. Create Owner B and a restaurant/dish for them
    with app.app_context():
        from app import db
        owner_b = User(name="Owner B", email="ownerb@test.com", role="owner")
        owner_b.set_password("password123")
        db.session.add(owner_b)
        db.session.commit()
        
        rest_b = Restaurant(owner_id=owner_b.id, name="Rest B", address="Addr B")
        db.session.add(rest_b)
        db.session.commit()
        
        dish_b = Dish(
            restaurant_id=rest_b.id,
            category_id=init_database['category_id'],
            food_type_id=init_database['food_type_id'],
            name="Dish B",
            price=10.0
        )
        db.session.add(dish_b)
        db.session.commit()
        dish_b_id = dish_b.id

    # 2. Login as Owner A (from init_database)
    with client:
        client.post('/auth/login', data={
            'email': init_database['owner_email'],
            'password': init_database['password']
        })
        
        # Try to delete Owner B's dish
        # The route /owner/dishes/delete/<id> is POST only
        response = client.post(f'/owner/dishes/delete/{dish_b_id}', follow_redirects=False)
        # Should stay on dishes page since ownership check fails
        assert response.status_code == 302
        assert '/owner/dishes' in response.headers['Location']
        
        # Verify dish still exists
        with app.app_context():
            assert db.session.get(Dish, dish_b_id) is not None
