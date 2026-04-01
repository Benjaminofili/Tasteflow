from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, make_response
from flask_login import login_required, current_user, logout_user
from app import db, csrf
from app.models import User, Restaurant, Order, Category, FoodType, OrderItem, Review, Dish, AdminAuditLog
from sqlalchemy import func, or_, and_
from sqlalchemy.orm import joinedload
from datetime import datetime, timedelta
from functools import wraps
import json
import csv
from io import StringIO
from app.utils import serialize_order_event, is_ajax_request, upload_file_to_cloudinary

bp = Blueprint('admin', __name__, url_prefix='/admin')



def admin_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            return jsonify({'success': False, 'error': 'Access denied. Admin only.'}), 403
        return func(*args, **kwargs)
    return login_required(wrapper)

def log_admin_action(action, target_type=None, target_id=None, details=None):
    """Log an admin action for audit purposes."""
    try:
        log = AdminAuditLog(
            admin_id=current_user.id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            details=json.dumps(details) if details else None,
            ip_address=request.remote_addr
        )
        db.session.add(log)
    except Exception as e:
        print(f"Audit log error: {e}")

@bp.route('/api/dashboard')
@admin_required
def get_dashboard_data():
    try:
        users_count = User.query.filter_by(role='customer').count()
        owners_count = User.query.filter_by(role='owner').count()
        restaurants_count = Restaurant.query.count()
        orders_count = Order.query.count()
        pending_orders = Order.query.filter_by(status='pending').count()
        
        revenue_result = db.session.query(
            func.coalesce(func.sum(Order.total_amount), 0)
        ).filter(Order.status != 'cancelled').scalar()
        total_revenue = float(revenue_result or 0)
        
        today = datetime.now().date()
        today_start = datetime.combine(today, datetime.min.time())
        
        today_orders = Order.query.filter(Order.order_date >= today_start).count()
        today_revenue_result = db.session.query(
            func.coalesce(func.sum(Order.total_amount), 0)
        ).filter(
            Order.order_date >= today_start,
            Order.status != 'cancelled'
        ).scalar()
        today_revenue = float(today_revenue_result or 0)
        
        dates = []
        revenue_data = []
        for i in range(6, -1, -1):
            date = today - timedelta(days=i)
            date_start = datetime.combine(date, datetime.min.time())
            date_end = datetime.combine(date, datetime.max.time())
            
            day_revenue = db.session.query(
                func.coalesce(func.sum(Order.total_amount), 0)
            ).filter(
                Order.order_date >= date_start,
                Order.order_date <= date_end,
                Order.status != 'cancelled'
            ).scalar()
            
            dates.append(date.strftime('%Y-%m-%d'))
            revenue_data.append(float(day_revenue or 0))
        
        top_rests_query = db.session.query(
            Restaurant.id,
            Restaurant.name,
            func.coalesce(func.sum(Order.total_amount), 0).label('total_earned'),
            func.count(Order.id).label('order_count')
        ).outerjoin(Order, and_(
            Order.restaurant_id == Restaurant.id,
            Order.status != 'cancelled'
        )).group_by(Restaurant.id).order_by(
            func.sum(Order.total_amount).desc()
        ).limit(5).all()
        
        recent_orders = Order.query.options(joinedload(Order.customer), joinedload(Order.restaurant))\
                            .order_by(Order.order_date.desc()).limit(10).all()
        recent_users = User.query.order_by(User.created_at.desc()).limit(5).all()
        
        return jsonify({
            'stats': {
                'users_count': users_count,
                'owners_count': owners_count,
                'restaurants_count': restaurants_count,
                'orders_count': orders_count,
                'pending_orders': pending_orders,
                'total_revenue': total_revenue,
                'today_orders': today_orders,
                'today_revenue': today_revenue
            },
            'charts': {
                'weekly_revenue': {
                    'labels': dates,
                    'data': revenue_data
                },
                'top_restaurants': {
                    'labels': [r.name for r in top_rests_query],
                    'data': [float(r.total_earned) for r in top_rests_query]
                }
            },
            'recent_activity': {
                'orders': [serialize_order_event(o) for o in recent_orders],
                'users': [{
                    'id': u.id,
                    'name': u.name,
                    'email': u.email,
                    'role': u.role,
                    'created_at': u.created_at.isoformat() if u.created_at else None
                } for u in recent_users]
            }
        })
    except Exception as e:
        print(f"Dashboard error: {e}")
        return jsonify({'success': False, 'message': 'Error loading dashboard analytics.'}), 500

@bp.route('/api/categories', methods=['GET', 'POST'])
@admin_required
@csrf.exempt
def manage_categories():
    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form
        name = (data.get('name') or '').strip()
        if not name or len(name) < 2 or len(name) > 50:
            return jsonify({'success': False, 'message': 'Category name must be between 2 and 50 characters.'}), 400
        
        if Category.query.filter(func.lower(Category.name) == name.lower()).first():
            return jsonify({'success': False, 'message': f'Category "{name}" already exists.'}), 400
        
        try:
            new_cat = Category(name=name)
            db.session.add(new_cat)
            log_admin_action('create_category', 'Category', None, {'name': name})
            db.session.commit()
            return jsonify({'success': True, 'message': f'Category "{name}" added.', 'category': {'id': new_cat.id, 'name': new_cat.name}})
        except Exception:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Error adding category.'}), 500
    
    categories = db.session.query(Category, func.count(Dish.id).label('dish_count'))\
                           .outerjoin(Dish).group_by(Category.id).order_by(Category.name).all()
    results = []
    for cat, count in categories:
        results.append({
            'id': cat.id,
            'name': cat.name,
            'dish_count': count
        })
    return jsonify({'categories': results})

@bp.route('/api/categories/delete/<int:id>', methods=['POST'])
@admin_required
@csrf.exempt
def delete_category(id):
    cat = db.get_or_404(Category, id)
    dish_count = Dish.query.filter_by(category_id=id).count()
    if dish_count > 0:
        return jsonify({'success': False, 'message': f'Cannot delete category "{cat.name}". It has {dish_count} associated dishes.'}), 400
    
    try:
        name = cat.name
        log_admin_action('delete_category', 'Category', id, {'name': name})
        db.session.delete(cat)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Category "{name}" deleted.'})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error deleting category.'}), 500

@bp.route('/api/food-types', methods=['GET', 'POST'])
@admin_required
@csrf.exempt
def manage_food_types():
    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form
        name = (data.get('name') or '').strip()
        if not name or len(name) < 2 or len(name) > 30:
            return jsonify({'success': False, 'message': 'Food type name must be between 2 and 30 characters.'}), 400
        
        if FoodType.query.filter(func.lower(FoodType.name) == name.lower()).first():
            return jsonify({'success': False, 'message': f'Food type "{name}" already exists.'}), 400
        
        try:
            new_ft = FoodType(name=name, is_approved=True)
            db.session.add(new_ft)
            log_admin_action('create_food_type', 'FoodType', None, {'name': name})
            db.session.commit()
            return jsonify({'success': True, 'message': f'Food type "{name}" added.', 'food_type': {'id': new_ft.id, 'name': new_ft.name}})
        except Exception:
            db.session.rollback()
            return jsonify({'success': False, 'message': 'Error adding food type.'}), 500
    
    food_types_list = FoodType.query.order_by(FoodType.name).all()
    results = []
    for ft in food_types_list:
        results.append({
            'id': ft.id,
            'name': ft.name,
            'is_approved': ft.is_approved,
            'dish_count': Dish.query.filter_by(food_type_id=ft.id).count()
        })
    return jsonify({'food_types': results})

@bp.route('/api/food-types/delete/<int:id>', methods=['POST'])
@admin_required
@csrf.exempt
def delete_food_type(id):
    ft = db.get_or_404(FoodType, id)
    dish_count = Dish.query.filter_by(food_type_id=id).count()
    if dish_count > 0:
        return jsonify({'success': False, 'message': f'Cannot delete food type "{ft.name}". It is used by {dish_count} dishes.'}), 400
    
    try:
        name = ft.name
        log_admin_action('delete_food_type', 'FoodType', id, {'name': name})
        db.session.delete(ft)
        db.session.commit()
        return jsonify({'success': True, 'message': f'Food type "{name}" deleted.'})
    except Exception:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Error deleting food type.'}), 500

@bp.route('/api/food-types/approve/<int:id>', methods=['POST'])
@admin_required
@csrf.exempt
def approve_food_type(id):
    ft = db.get_or_404(FoodType, id)
    if ft.is_approved:
        return jsonify({'success': True, 'message': 'Already approved.'})
    
    ft.is_approved = True
    log_admin_action('approve_food_type', 'FoodType', id, {'name': ft.name})
    db.session.commit()
    return jsonify({'success': True, 'message': f'Food type "{ft.name}" approved.'})

@bp.route('/api/food-types/reject/<int:id>', methods=['POST'])
@admin_required
@csrf.exempt
def reject_food_type(id):
    ft = db.get_or_404(FoodType, id)
    name = ft.name
    log_admin_action('reject_food_type', 'FoodType', id, {'name': name})
    db.session.delete(ft)
    db.session.commit()
    return jsonify({'success': True, 'message': f'Food type "{name}" rejected.'})

@bp.route('/api/profile', methods=['GET', 'POST'])
@admin_required
@csrf.exempt
def manage_profile():
    if request.method == 'POST':
        data = request.get_json(silent=True) or request.form
        action = data.get('action')
        
        if action == 'update_info':
            name = (data.get('name') or '').strip()
            phone = (data.get('phone') or '').strip()
            address = (data.get('address') or '').strip()
            
            if not name or len(name) < 2:
                return jsonify({'success': False, 'message': 'Name must be at least 2 characters.'}), 400
            
            try:
                current_user.name = name
                current_user.phone = phone if phone else None
                current_user.address = address if address else None
                
                # Profile Image Upload
                image_file = request.files.get('profile_image')
                if image_file and image_file.filename != '':
                    image_url = upload_file_to_cloudinary(image_file)
                    if image_url:
                        current_user.profile_image = image_url
                
                log_admin_action('update_profile_info', 'User', current_user.id)
                db.session.commit()
                return jsonify({
                    'success': True, 
                    'message': 'Profile updated successfully.',
                    'profile_image': current_user.profile_image
                })
            except Exception:
                db.session.rollback()
                return jsonify({'success': False, 'message': 'Error updating profile.'}), 500
                
        elif action == 'update_password':
            current_password = data.get('current_password', '')
            new_password = data.get('new_password', '')
            confirm_password = data.get('confirm_password', '')
            
            if not current_user.check_password(current_password):
                return jsonify({'success': False, 'message': 'Current password is incorrect.'}), 400
            elif not new_password or len(new_password) < 6:
                return jsonify({'success': False, 'message': 'New password must be at least 6 characters.'}), 400
            elif new_password != confirm_password:
                return jsonify({'success': False, 'message': 'New passwords do not match.'}), 400
            else:
                try:
                    current_user.set_password(new_password)
                    log_admin_action('update_profile_password', 'User', current_user.id)
                    db.session.commit()
                    return jsonify({'success': True, 'message': 'Password updated.'})
                except Exception:
                    db.session.rollback()
                    return jsonify({'success': False, 'message': 'Error updating password.'}), 500
        
        return jsonify({'success': False, 'message': 'Invalid action.'}), 400
    
    return jsonify({
        'name': current_user.name,
        'email': current_user.email,
        'phone': current_user.phone,
        'address': current_user.address,
        'profile_image': current_user.profile_image
    })

@bp.route('/api/reports/customers')
@admin_required
def customers_report():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    
    query = User.query.filter_by(role='customer')
    if search:
        query = query.filter(or_(User.name.ilike(f'%{search}%'), User.email.ilike(f'%{search}%')))
    
    pagination = query.order_by(User.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    
    customer_stats = []
    for customer in pagination.items:
        order_count = Order.query.filter_by(customer_id=customer.id).count()
        total_spent = db.session.query(func.coalesce(func.sum(Order.total_amount), 0))\
                                .filter(Order.customer_id == customer.id, Order.status != 'cancelled').scalar()
        customer_stats.append({
            'user': {
                'id': customer.id,
                'name': customer.name,
                'email': customer.email,
                'phone': customer.phone,
                'is_active': customer.is_active,
                'created_at': customer.created_at.isoformat() if customer.created_at else None
            },
            'order_count': order_count,
            'total_spent': float(total_spent or 0)
        })
    
    return jsonify({
        'customers': customer_stats,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total_pages': pagination.pages,
            'total_items': pagination.total
        }
    })

@bp.route('/api/reports/restaurants')
@admin_required
def restaurants_report():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('q', '').strip()
    
    query = Restaurant.query.options(joinedload(Restaurant.owner))
    if search:
        query = query.filter(Restaurant.name.ilike(f'%{search}%'))
    
    pagination = query.order_by(Restaurant.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    
    restaurant_stats = []
    for restaurant in pagination.items:
        dish_count = Dish.query.filter_by(restaurant_id=restaurant.id).count()
        order_count = Order.query.filter_by(restaurant_id=restaurant.id).count()
        total_revenue = db.session.query(func.coalesce(func.sum(Order.total_amount), 0))\
                                  .filter(Order.restaurant_id == restaurant.id, Order.status != 'cancelled').scalar()
        
        restaurant_stats.append({
            'id': restaurant.id,
            'name': restaurant.name,
            'owner_name': restaurant.owner.name if restaurant.owner else 'N/A',
            'is_active': restaurant.is_active,
            'dish_count': dish_count,
            'order_count': order_count,
            'total_revenue': float(total_revenue or 0),
            'created_at': restaurant.created_at.isoformat() if restaurant.created_at else None
        })
    
    return jsonify({
        'restaurants': restaurant_stats,
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total_pages': pagination.pages,
            'total_items': pagination.total
        }
    })

@bp.route('/api/orders')
@admin_required
def get_orders():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '').strip().lower()
    search = request.args.get('q', '').strip()
    
    query = Order.query.options(joinedload(Order.customer), joinedload(Order.restaurant))
    
    if status:
        query = query.filter(Order.status == status)
    if search:
        query = query.join(User, Order.customer_id == User.id).filter(
            or_(Order.id == int(search) if search.isdigit() else False,
                User.name.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'))
        )
    
    pagination = query.order_by(Order.order_date.desc()).paginate(page=page, per_page=25, error_out=False)
    return jsonify({
        'orders': [serialize_order_event(o) for o in pagination.items],
        'pagination': {
            'page': pagination.page,
            'per_page': pagination.per_page,
            'total_pages': pagination.pages,
            'total_items': pagination.total
        }
    })

@bp.route('/api/orders/feed')
@admin_required
def orders_feed():
    try:
        limit = min(request.args.get('limit', 50, type=int), 100)
        orders = Order.query.options(joinedload(Order.customer), joinedload(Order.restaurant))\
                            .order_by(Order.order_date.desc()).limit(limit).all()
        return jsonify({'success': True, 'orders': [serialize_order_event(o) for o in orders]})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/orders/notifications')
@admin_required
def order_notifications():
    try:
        pending_count = Order.query.filter_by(status='pending').count()
        latest = Order.query.options(joinedload(Order.customer), joinedload(Order.restaurant))\
                            .order_by(Order.order_date.desc()).first()
        return jsonify({
            'success': True,
            'pending_count': pending_count,
            'latest_order': serialize_order_event(latest) if latest else None
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/food-types/pending-count')
@admin_required
def pending_food_types_count():
    try:
        return jsonify({'success': True, 'count': FoodType.query.filter_by(is_approved=False).count()})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/catalog/snapshot')
@admin_required
def catalog_snapshot():
    try:
        return jsonify({
            'success': True,
            'categories_count': Category.query.count(),
            'food_types_count': FoodType.query.filter_by(is_approved=True).count(),
            'pending_food_types_count': FoodType.query.filter_by(is_approved=False).count(),
            'total_dishes': Dish.query.count()
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/platform/health')
@admin_required
def platform_health():
    now = datetime.now()
    window = now - timedelta(minutes=30)
    return jsonify({
        'success': True,
        'new_users': User.query.filter(User.created_at >= window).count(),
        'new_orders': Order.query.filter(Order.order_date >= window).count(),
        'generated_at': now.isoformat()
    })

# ── Additional Admin Features ────────────────────────────────────────────────

@bp.route('/users/<int:id>/toggle-status', methods=['POST'])
@admin_required
@csrf.exempt
def toggle_user_status(id):
    user = db.get_or_404(User, id)
    if user.role == 'admin':
        return jsonify({'success': False, 'message': 'Cannot deactivate admins.'}), 403
    
    user.is_active = not user.is_active
    log_admin_action('toggle_user_status', 'User', id, {'new_state': user.is_active})
    db.session.commit()
    return jsonify({
        'success': True, 
        'message': f'User "{user.name}" {"activated" if user.is_active else "deactivated"}.',
        'is_active': user.is_active
    })

@bp.route('/restaurants/<int:id>/toggle-status', methods=['POST'])
@admin_required
@csrf.exempt
def toggle_restaurant_status(id):
    rest = db.get_or_404(Restaurant, id)
    rest.is_active = not rest.is_active
    log_admin_action('toggle_restaurant_status', 'Restaurant', id, {'new_state': rest.is_active})
    db.session.commit()
    return jsonify({
        'success': True, 
        'message': f'Restaurant "{rest.name}" {"activated" if rest.is_active else "deactivated"}.',
        'is_active': rest.is_active
    })

@bp.route('/orders/<int:id>/cancel', methods=['POST'])
@admin_required
@csrf.exempt
def admin_cancel_order(id):
    order = db.get_or_404(Order, id)
    if order.status in ['delivered', 'completed', 'cancelled']:
        return jsonify({'success': False, 'message': 'Cannot cancel finished orders.'}), 400
    
    order.status = 'cancelled'
    log_admin_action('cancel_order', 'Order', id)
    db.session.commit()
    return jsonify({'success': True, 'message': f'Order #{id} cancelled.'})

@bp.route('/export/orders')
@admin_required
def export_orders():
    orders = Order.query.options(joinedload(Order.customer), joinedload(Order.restaurant))\
                        .order_by(Order.order_date.desc()).all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['Order ID', 'Date', 'Customer', 'Restaurant', 'Status', 'Total Amount'])
    for o in orders:
        cw.writerow([o.id, o.order_date.isoformat(), o.customer.name, o.restaurant.name, o.status, float(o.total_amount)])
    
    response = make_response(si.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=orders_{datetime.now().strftime('%Y%m%d')}.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@bp.route('/export/customers')
@admin_required
def export_customers():
    customers = User.query.filter_by(role='customer').order_by(User.created_at.desc()).all()
    si = StringIO()
    cw = csv.writer(si)
    cw.writerow(['ID', 'Name', 'Email', 'Phone', 'Address', 'Registered On'])
    for c in customers:
        cw.writerow([c.id, c.name, c.email, c.phone or 'N/A', c.address or 'N/A', c.created_at.isoformat() if c.created_at else 'N/A'])
    
    response = make_response(si.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=customers_{datetime.now().strftime('%Y%m%d')}.csv"
    response.headers["Content-type"] = "text/csv"
    return response

@bp.route('/audit-logs')
@admin_required
def audit_logs():
    page = request.args.get('page', 1, type=int)
    logs = AdminAuditLog.query.options(joinedload(AdminAuditLog.admin))\
                              .order_by(AdminAuditLog.created_at.desc())\
                              .paginate(page=page, per_page=50, error_out=False)
    return jsonify({
        'logs': [{
            'id': l.id,
            'admin_name': l.admin.name if l.admin else 'System',
            'action': l.action,
            'target_type': l.target_type,
            'target_id': l.target_id,
            'details': l.details,
            'ip_address': l.ip_address,
            'created_at': l.created_at.isoformat()
        } for l in logs.items],
        'pagination': {
            'page': logs.page,
            'per_page': logs.per_page,
            'total_pages': logs.pages,
            'total_items': logs.total
        }
    })
