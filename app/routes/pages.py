from flask import Blueprint, render_template, redirect, url_for, session
from flask_login import current_user, login_required

bp = Blueprint('pages', __name__, template_folder='../templates')

# ── Public Pages ─────────────────────────────────────────────────────────────
@bp.route('/')
def index():
    # Serves the landing page (index.html) from the root templates folder
    return render_template('index.html')

@bp.route('/login')
def login():
    # Serves the login page from the /auth subfolder
    return render_template('auth/login.html')

@bp.route('/register')
def register():
    return render_template('auth/register.html')

@bp.route('/forgot-password')
def forgot_password():
    return render_template('auth/forgot-password.html')

@bp.route('/reset-password/<token>')
def reset_password(token):
    # Notice we don't pass the token into the template variables here. 
    # Our JavaScript extracts it directly from the URL path!
    return render_template('auth/reset-password.html')

# ── Customer Pages ───────────────────────────────────────────────────────────
@bp.route('/dashboard')
@bp.route('/customer/dashboard')
@login_required
def dashboard():
    if current_user.role != 'customer':
        return redirect(url_for('pages.index'))
    return render_template('customer/dashboard.html')

@bp.route('/cart')
@bp.route('/customer/cart')
@login_required
def cart():
    if current_user.role != 'customer':
        return redirect(url_for('pages.index'))
    return render_template('customer/cart.html')

@bp.route('/checkout')
@bp.route('/customer/checkout')
@login_required
def checkout():
    if current_user.role != 'customer':
        return redirect(url_for('pages.index'))
    return render_template('customer/checkout.html')

@bp.route('/orders')
@bp.route('/customer/orders')
@login_required
def orders():
    if current_user.role != 'customer':
        return redirect(url_for('pages.index'))
    return render_template('customer/orders.html')

@bp.route('/orders/<int:order_id>/track')
@bp.route('/customer/tracking/<int:order_id>')
@login_required
def track_order(order_id):
    if current_user.role != 'customer':
        return redirect(url_for('pages.index'))
    return render_template('customer/tracking.html')

@bp.route('/customer/tracking') # Added redundant tracking route as per instruction
@login_required
def customer_tracking_overview():
    if current_user.role != 'customer':
        return redirect(url_for('pages.index'))
    return render_template('customer/tracking.html')

@bp.route('/restaurant/<int:restaurant_id>')
@bp.route('/customer/restaurant/<int:restaurant_id>')
def restaurant_detail(restaurant_id):
    return render_template('customer/restaurant.html')

@bp.route('/profile')
@bp.route('/customer/profile')
@login_required
def profile():
    return render_template('customer/profile.html')

# ── Owner Pages ──────────────────────────────────────────────────────────────
@bp.route('/owner/dashboard')
def owner_dashboard():
    return render_template('owner/dashboard.html')

@bp.route('/owner/profile')
def owner_profile():
    return render_template('owner/profile.html')

@bp.route('/owner/dishes')
def owner_dishes():
    return render_template('owner/dishes.html')

@bp.route('/owner/orders')
def owner_orders():
    return render_template('owner/orders.html')

@bp.route('/owner/media')
def owner_media():
    return render_template('owner/media.html')

@bp.route('/owner/coupons')
def owner_coupons():
    return render_template('owner/coupons.html')

@bp.route('/owner/dishes/add')
def owner_add_dish():
    return render_template('owner/add-dish.html')

@bp.route('/owner/dishes/edit/<int:dish_id>')
def owner_edit_dish(dish_id):
    return render_template('owner/edit-dish.html')

# ── Admin Pages ──────────────────────────────────────────────────────────────

@bp.route('/admin/login')
def admin_login():
    return render_template('admin/login.html')

@bp.route('/admin')
@bp.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('pages.index'))
    return render_template('admin/dashboard.html')

@bp.route('/admin/categories')
@login_required
def admin_categories():
    if current_user.role != 'admin':
        return redirect(url_for('pages.index'))
    return render_template('admin/categories.html')

@bp.route('/admin/food-types')
@login_required
def admin_food_types():
    if current_user.role != 'admin':
        return redirect(url_for('pages.index'))
    return render_template('admin/food-types.html')

@bp.route('/admin/customers')
@login_required
def admin_customers():
    if current_user.role != 'admin':
        return redirect(url_for('pages.index'))
    return render_template('admin/customers.html')

@bp.route('/admin/restaurants')
@login_required
def admin_restaurants():
    if current_user.role != 'admin':
        return redirect(url_for('pages.index'))
    return render_template('admin/restaurants.html')

@bp.route('/admin/orders')
@login_required
def admin_orders():
    if current_user.role != 'admin':
        return redirect(url_for('pages.index'))
    return render_template('admin/orders.html')

@bp.route('/admin/reports')
@login_required
def admin_reports():
    if current_user.role != 'admin':
        return redirect(url_for('pages.index'))
    return render_template('admin/reports.html')

@bp.route('/admin/profile')
@login_required
def admin_profile():
    if current_user.role != 'admin':
        return redirect(url_for('pages.index'))
    return render_template('admin/profile.html')