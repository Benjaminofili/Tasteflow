"""
Integration Tests - Owner Routes
Tests owner dashboard access, coupon management and order updates.
"""
import pytest


def test_owner_dashboard_access(client, init_database):
    """Test that authenticated owners can access their dashboard."""
    client.post('/auth/login', data={
        'email': init_database['owner_email'],
        'password': init_database['password']
    }, follow_redirects=True)

    response = client.get('/owner/dashboard')
    assert response.status_code == 200
    assert b'Test Restaurant' in response.data


def test_customer_cannot_access_owner_routes(client, init_database):
    """Test that standard users are blocked from owner routes."""
    client.post('/auth/login', data={
        'email': init_database['customer_email'],
        'password': init_database['password']
    }, follow_redirects=True)

    response = client.get('/owner/dashboard', follow_redirects=False)
    # Should be redirected away (302) or forbidden
    assert response.status_code in (302, 403)
    if response.status_code == 302:
        location = response.headers.get('Location', '')
        # Should not land on the owner dashboard
        assert 'owner/dashboard' not in location


def test_add_coupon(client, init_database, app):
    """Test owner adding a coupon."""
    client.post('/auth/login', data={
        'email': init_database['owner_email'],
        'password': init_database['password']
    }, follow_redirects=True)

    response = client.post('/owner/coupons/add', data={
        'code': 'HALFOFF',
        'discount_type': 'percent',
        'discount_value': '50',
        'is_active': 'on'
    }, follow_redirects=True)

    assert response.status_code == 200

    with app.app_context():
        from app.models import Coupon
        coupon = Coupon.query.filter_by(code='HALFOFF').first()
        assert coupon is not None
        assert float(coupon.discount_value) == 50.0


def test_accept_order(client, init_database, app):
    """Test owner updating an order status to accepted."""
    with app.app_context():
        from app import db
        from app.models import Order
        order = Order(
            customer_id=init_database['customer_id'],
            restaurant_id=init_database['restaurant_id'],
            total_amount=10.0,
            status='pending',
            delivery_address='123 St'
        )
        db.session.add(order)
        db.session.commit()
        order_id = order.id

    client.post('/auth/login', data={
        'email': init_database['owner_email'],
        'password': init_database['password']
    })

    response = client.post(f'/owner/orders/update/{order_id}', data={
        'status': 'accepted',
        'estimated_time': '45'
    }, follow_redirects=True)

    assert response.status_code == 200

    with app.app_context():
        order = app.extensions['sqlalchemy'].session.get(
            __import__('app.models', fromlist=['Order']).Order, order_id
        )
        assert order.status == 'accepted'
