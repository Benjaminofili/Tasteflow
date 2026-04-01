# app/routes/auth.py
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify, current_app
from flask_login import login_user, logout_user, login_required, current_user
from itsdangerous import URLSafeTimedSerializer
from flask_mail import Message
from app import db, limiter, csrf, mail
from app.models import User, Restaurant
from app.forms import LoginForm, RegistrationForm, ChangePasswordForm
import re
from werkzeug.security import generate_password_hash

bp = Blueprint('auth', __name__, url_prefix='/auth')

# Email validation regex
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

def validate_email(email):
    """Validate email format."""
    return bool(EMAIL_REGEX.match(email))

# ── JSON APIs for React Frontend ─────────────────────────────────────────────

@bp.route('/api/auth/me', methods=['GET'])
def api_me():
    """Get current user info."""
    if not current_user.is_authenticated:
        return jsonify({'user': None, 'authenticated': False}), 200
    
    user_data = {
        'id': current_user.id,
        'name': current_user.name,
        'email': current_user.email,
        'role': current_user.role,
        'phone': current_user.phone,
        'address': current_user.address,
        'profile_image': current_user.profile_image
    }
    
    restaurant_data = None
    if current_user.role == 'owner' and current_user.restaurants:
        restaurant = current_user.restaurants[0]
        restaurant_data = {
            'id': restaurant.id,
            'name': restaurant.name,
            'address': restaurant.address,
            'description': restaurant.description,
            'logo_url': restaurant.logo_url
        }
    
    return jsonify({
        'authenticated': True,
        'user': user_data,
        'restaurant': restaurant_data
    })

@bp.route('/api/auth/login', methods=['POST'])
@csrf.exempt
@limiter.limit("5 per minute")
def api_login():
    """API login endpoint."""
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    remember = data.get('remember_me', False)
    
    # Validation
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
    
    # Find user (case-insensitive email)
    user = User.query.filter(db.func.lower(User.email) == email).first()
    
    if user and user.check_password(password):
        login_user(user, remember=remember)
        return jsonify({
            'message': 'Logged in successfully',
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'role': user.role
            }
        }), 200
    
    return jsonify({'error': 'Invalid email or password'}), 401
    
@bp.route('/api/auth/admin-login', methods=['POST'])
@csrf.exempt
@limiter.limit("5 per minute")
def api_admin_login():
    """Secure administration login endpoint."""
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    
    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400
        
    user = User.query.filter(db.func.lower(User.email) == email).first()
    
    # Check credentials AND enforce admin role
    if user and user.check_password(password):
        if user.role != 'admin':
            return jsonify({'error': 'Access denied. Administrator privileges required.'}), 403
            
        login_user(user, remember=True)
        return jsonify({
            'message': 'Admin authenticated successfully',
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'role': user.role
            }
        }), 200
        
    return jsonify({'error': 'Invalid credentials'}), 401

@bp.route('/api/auth/register', methods=['POST'])
@csrf.exempt
@limiter.limit("3 per minute")
def api_register():
    """API registration endpoint."""
    data = request.get_json() or {}
    
    # Extract and sanitize fields
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    phone = (data.get('phone') or '').strip()
    address = (data.get('address') or '').strip()
    password = data.get('password') or ''
    role = data.get('role', 'customer')
    
    # Owner-specific fields
    restaurant_name = (data.get('restaurant_name') or '').strip()
    restaurant_address = (data.get('restaurant_address') or '').strip()
    
    errors = []
    
    # Validate name
    if not name or len(name) < 2:
        errors.append('Name must be at least 2 characters.')
    elif len(name) > 100:
        errors.append('Name cannot exceed 100 characters.')
    
    # Validate email
    if not email:
        errors.append('Email is required.')
    elif not validate_email(email):
        errors.append('Invalid email format.')
    elif len(email) > 100:
        errors.append('Email cannot exceed 100 characters.')
    
    # Validate password
    if not password or len(password) < 6:
        errors.append('Password must be at least 6 characters.')
    elif len(password) > 128:
        errors.append('Password cannot exceed 128 characters.')
    
    # Validate role - CRITICAL: Prevent admin registration!
    ALLOWED_ROLES = ['customer', 'owner']
    if role not in ALLOWED_ROLES:
        role = 'customer'
    
    # Validate phone
    if phone:
        cleaned_phone = ''.join(filter(str.isdigit, phone))
        if len(cleaned_phone) < 10:
            errors.append('Phone number must have at least 10 digits.')
    
    # Owner-specific validations
    if role == 'owner':
        if not restaurant_name:
            errors.append('Restaurant name is required for owners.')
        if not restaurant_address:
            errors.append('Restaurant address is required for owners.')
    
    if errors:
        return jsonify({'error': errors[0], 'errors': errors}), 400
    
    # Check duplicate email
    if User.query.filter(db.func.lower(User.email) == email).first():
        return jsonify({'error': 'This email is already registered.'}), 400
    
    try:
        user = User(
            name=name,
            email=email,
            phone=phone,
            address=address,
            role=role
        )
        user.set_password(password)
        db.session.add(user)
        db.session.commit()  # Commit user first to get ID
        
        # If owner, create restaurant record
        if role == 'owner':
            restaurant = Restaurant(
                owner_id=user.id,  # Now user.id is available
                name=restaurant_name,
                address=restaurant_address,
                contact=phone  # Use owner's phone as restaurant contact
            )
            db.session.add(restaurant)
            db.session.commit()  # Commit restaurant
        
        # Auto-login after registration
        login_user(user)
        
        return jsonify({
            'message': 'Registration successful',
            'user': {
                'id': user.id,
                'name': user.name,
                'email': user.email,
                'role': user.role
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        print(f"Registration error: {e}")
        return jsonify({'error': 'An error occurred during registration.'}), 500

@bp.route('/api/auth/logout', methods=['POST'])
@csrf.exempt
def api_logout():
    """API logout endpoint."""
    if current_user.is_authenticated:
        logout_user()
    return jsonify({'message': 'Logged out successfully'}), 200

# ── Password Recovery Logic ──────────────────────────────────────────────────

def get_reset_token(user_id):
    """Generate a secure, signed token for password reset."""
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps({'user_id': user_id}, salt='password-reset-salt')

def verify_reset_token(token, expires_sec=900):
    """Verify the reset token and return the user."""
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        user_id = s.loads(token, salt='password-reset-salt', max_age=expires_sec)['user_id']
    except Exception:
        return None
    return db.session.get(User, user_id)

@bp.route('/api/auth/forgot-password', methods=['POST'])
@csrf.exempt
def api_forgot_password():
    """Forgot password API endpoint (Development Mode - No Email Required)."""
    data = request.get_json() or {}
    email = (data.get('email') or '').strip().lower()
    
    user = User.query.filter(db.func.lower(User.email) == email).first()
    
    if user:
        # 1. Generate the secure token
        token = get_reset_token(user.id)
        
        # 2. Construct the exact reset URL
        reset_link = url_for('pages.reset_password', token=token, _external=True)
        
        # 3. DEVELOPMENT BYPASS: Print to terminal so you can click it
        print(f"\n{'='*50}")
        print(f"🔒 PASSWORD RESET LINK GENERATED FOR: {user.email}")
        print(f"👉 CLICK HERE: {reset_link}")
        print(f"{'='*50}\n")
        
        # 4. Return it in the JSON so the frontend can alert the user
        return jsonify({
            'success': True, 
            'message': 'Development Mode: Check your terminal or click OK to see your reset link.',
            'dev_reset_link': reset_link
        }), 200
            
    # Always return success even if user not found (security best practice)
    return jsonify({
        'success': True, 
        'message': 'If an account exists, a recovery link has been generated.'
    }), 200

@bp.route('/api/auth/change-password', methods=['POST'])
@login_required
@csrf.exempt
def api_change_password():
    """Change password API endpoint for authenticated users."""
    data = request.get_json() or {}
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({'success': False, 'error': 'Current password and new password are required.'}), 400
    
    if len(new_password) < 6:
        return jsonify({'success': False, 'error': 'Password must be at least 6 characters.'}), 400
    
    # Verify current password
    if not current_user.check_password(current_password):
        return jsonify({'success': False, 'error': 'Current password is incorrect.'}), 400
    
    # Update password
    current_user.set_password(new_password)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Password has been successfully updated.'}), 200

@bp.route('/api/auth/reset-password/<token>', methods=['POST'])
@csrf.exempt
def api_reset_password(token):
    """Reset password API endpoint."""
    user = verify_reset_token(token)
    if not user:
        return jsonify({'success': False, 'message': 'Invalid or expired token.'}), 400
        
    data = request.get_json() or {}
    new_password = data.get('password')
    
    if not new_password or len(new_password) < 8:
        return jsonify({'success': False, 'message': 'Password must be at least 8 characters.'}), 400
        
    user.set_password(new_password)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Password has been successfully updated.'}), 200