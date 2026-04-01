"""
Integration Tests - Authentication Routes
Tests login, register, and session management.
"""
import pytest


def test_login_page_renders(client):
    """Test that the login page loads correctly."""
    response = client.get('/auth/login')
    assert response.status_code == 200


def test_register_page_renders(client):
    """Test that the registration page loads correctly."""
    response = client.get('/auth/register')
    assert response.status_code == 200


def test_successful_login(client, init_database):
    """Test login with correct credentials redirects away from login page."""
    response = client.post('/auth/login', data={
        'email': init_database['customer_email'],
        'password': init_database['password']
    }, follow_redirects=False)
    # Successful login should redirect (302) away
    assert response.status_code == 302
    assert '/auth/login' not in response.headers.get('Location', '')


def test_failed_login(client, init_database):
    """Test login with incorrect password stays on login page (200, no redirect)."""
    response = client.post('/auth/login', data={
        'email': init_database['customer_email'],
        'password': 'wrongpassword'
    }, follow_redirects=False)
    # Failed login should NOT redirect — it re-renders the form (200) 
    # OR redirect back to login (302 to /auth/login)
    if response.status_code == 302:
        assert 'login' in response.headers.get('Location', '').lower()
    else:
        assert response.status_code == 200
