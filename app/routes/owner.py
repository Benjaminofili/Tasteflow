from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, session
from flask_login import login_required, current_user
from app import db
from app.models import Restaurant, Dish, Order, Category, FoodType, Coupon, OrderItem, RestaurantMedia, Review
from app.utils import upload_file_to_cloudinary
from app.utils import serialize_order_event, is_ajax_request
from datetime import datetime, timedelta
from sqlalchemy import func, or_
from sqlalchemy.orm import joinedload
from functools import wraps
from app import db, limiter, csrf
from spellchecker import SpellChecker

bp = Blueprint('owner', __name__, url_prefix='/owner')


spell = SpellChecker()

def check_dish_spelling(name):
    if not name: return None
    words = [w.strip('.,!?"\'') for w in name.split()]
    misspelled = spell.unknown(words)
    if not misspelled:
        return None
        
    suggestions = []
    for word in misspelled:
        if word and not word.isdigit():
            correction = spell.correction(word)
            if correction and correction != word:
                suggestions.append(f"'{word}' -> '{correction}'")
                
    if suggestions:
        return f"Typo warning: Did you mean {', '.join(suggestions)}?"
    return None

def owner_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'owner':
            return jsonify({'success': False, 'error': 'Access denied. Restaurant Owner only.'}), 403
        return func(*args, **kwargs)
    return login_required(wrapper)

def restaurant_required(func):
    """Ensure the owner has a restaurant profile set up."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        rest = Restaurant.query.filter_by(owner_id=current_user.id).first()
        if not rest:
            return jsonify({'success': False, 'error': 'Please set up your restaurant profile first.', 'needs_profile': True}), 400
        kwargs['restaurant'] = rest
        return func(*args, **kwargs)
    return owner_required(wrapper)

def get_restaurant():
    # Helper to get the current owner's restaurant
    return Restaurant.query.filter_by(owner_id=current_user.id).first()

@bp.route('/api/dashboard')
@restaurant_required
def get_dashboard_data(restaurant):
    """Owner dashboard analytics API."""
    dishes_count = Dish.query.filter_by(restaurant_id=restaurant.id, deleted_at=None).count()
    
    recent_orders = Order.query.filter_by(restaurant_id=restaurant.id)\
        .options(joinedload(Order.customer))\
        .order_by(Order.order_date.desc()).limit(5).all()
    
    thirty_days_ago = datetime.now() - timedelta(days=30)
    completed_orders = Order.query.filter(
        Order.restaurant_id == restaurant.id,
        Order.status.in_(['delivered', 'completed']),
        Order.order_date >= thirty_days_ago
    ).all()
    
    total_revenue = sum(float(o.total_amount) for o in completed_orders)
    
    today = datetime.now().date()
    dates = [(today - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(6, -1, -1)]
    revenue_by_date = {d: 0.0 for d in dates}
    for o in completed_orders:
        o_date = o.order_date.strftime('%Y-%m-%d')
        if o_date in revenue_by_date:
            revenue_by_date[o_date] += float(o.total_amount)
            
    top_dishes_query = db.session.query(
        Dish.name, func.sum(OrderItem.quantity).label('total_sold')
    ).join(OrderItem).join(Order).filter(
        Order.restaurant_id == restaurant.id,
        Order.status != 'cancelled'
    ).group_by(Dish.id).order_by(func.sum(OrderItem.quantity).desc()).limit(5).all()
    
    return jsonify({
        'restaurant': {
            'id': restaurant.id,
            'name': restaurant.name,
            'logo_url': restaurant.logo_url
        },
        'stats': {
            'dishes_count': dishes_count,
            'total_revenue': total_revenue,
            'recent_orders': [serialize_order_event(o) for o in recent_orders]
        },
        'charts': {
            'revenue_trend': {
                'labels': list(revenue_by_date.keys()),
                'data': list(revenue_by_date.values())
            },
            'top_dishes': {
                'labels': [d[0] for d in top_dishes_query],
                'data': [d[1] for d in top_dishes_query]
            }
        }
    })

@bp.route('/api/profile', methods=['GET', 'POST'])
@owner_required
def profile():
    restaurant = get_restaurant()
    if request.method == 'POST':
        # multipart/form-data for logo
        name = (request.form.get('name') or '').strip()
        address = (request.form.get('address') or '').strip()
        contact = (request.form.get('contact') or '').strip()
        description = (request.form.get('description') or '').strip()

        if not name or not address or not contact:
            return jsonify({'success': False, 'message': 'Restaurant name, contact, and address are required.'}), 400
        
        logo_file = request.files.get('logo')
        logo_url = None
        if logo_file and logo_file.filename != '':
            logo_url = upload_file_to_cloudinary(logo_file)
        
        if not restaurant:
            restaurant = Restaurant(owner_id=current_user.id)
            db.session.add(restaurant)
            
        restaurant.name = name
        restaurant.address = address
        restaurant.contact = contact
        restaurant.description = description
        if logo_url:
            restaurant.logo_url = logo_url
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Restaurant profile updated.', 'restaurant': {'id': restaurant.id, 'name': restaurant.name}})
        
    return jsonify({
        'restaurant': {
            'id': restaurant.id,
            'name': restaurant.name,
            'address': restaurant.address,
            'contact': restaurant.contact,
            'description': restaurant.description,
            'logo_url': restaurant.logo_url
        } if restaurant else None
    })

@bp.route('/api/profile/edit', methods=['POST'])
@owner_required
@csrf.exempt
def edit_profile():
    # 1. Get the current user's restaurant
    restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
    
    if not restaurant:
        return jsonify({'success': False, 'error': 'Restaurant profile not found.'}), 404

    # 2. Update User data (Phone)
    if 'phone' in request.form:
        current_user.phone = request.form.get('phone')
        
    # 3. Update Restaurant data (Name, Address, Description/Cuisine)
    if 'name' in request.form:
        restaurant.name = request.form.get('name')
    if 'address' in request.form:
        restaurant.address = request.form.get('address')
    if 'description' in request.form:
        restaurant.description = request.form.get('description')
        
    # 4. Handle Logo Upload (if a new file was selected)
    logo_file = request.files.get('logo')
    if logo_file and logo_file.filename != '':
        logo_url = upload_file_to_cloudinary(logo_file, resource_type='image')
        if logo_url:
            restaurant.logo_url = logo_url
        else:
            return jsonify({'success': False, 'error': 'Failed to upload logo image.'}), 400

    # 5. Save everything to the database
    try:
        db.session.commit()
        return jsonify({
            'success': True, 
            'message': 'Profile updated successfully!',
            'logo_url': restaurant.logo_url
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Database error occurred while saving.'}), 500

@bp.route('/api/dishes', methods=['GET'])
@restaurant_required
def get_dishes(restaurant):
    dishes = Dish.query.filter_by(restaurant_id=restaurant.id, deleted_at=None).all()
    results = []
    for d in dishes:
        results.append({
            'id': d.id,
            'name': d.name,
            'price': float(d.price),
            'description': d.description,
            'image_url': d.image_url,
            'is_available': d.is_available,
            'category_name': d.category.name if d.category else None,
            'food_type_name': d.food_type.name if d.food_type else None
        })
    return jsonify({'dishes': results})

@bp.route('/api/dishes/<int:id>', methods=['GET'])
@restaurant_required
def get_single_dish(id, restaurant):
    dish = Dish.query.get_or_404(id)
    if dish.restaurant_id != restaurant.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
    
    return jsonify({
        'id': dish.id,
        'name': dish.name,
        'price': float(dish.price),
        'description': dish.description,
        'category_id': dish.category_id,
        'food_type_id': dish.food_type_id,
        'image_url': dish.image_url,
        'is_available': dish.is_available
    })


@bp.route('/api/dishes/add', methods=['POST'])
@restaurant_required
@csrf.exempt
def add_dish(restaurant):
    # Form data because of file upload
    name = (request.form.get('name') or '').strip()
    price = request.form.get('price', type=float)
    
    if not name or price is None or price < 0:
        return jsonify({'success': False, 'message': 'Valid name and price are required.'}), 400

    image_file = request.files.get('image')
    image_url = None
    if image_file and image_file.filename != '':
        image_url = upload_file_to_cloudinary(image_file)
        
    food_type_id = request.form.get('food_type_id')
    new_food_type_name = (request.form.get('new_food_type') or '').strip()
    if new_food_type_name:
        existing = FoodType.query.filter(func.lower(FoodType.name) == new_food_type_name.lower()).first()
        if existing:
            food_type_id = existing.id
        else:
            new_ft = FoodType(name=new_food_type_name, is_approved=False, requested_by_id=current_user.id)
            db.session.add(new_ft)
            db.session.flush()
            food_type_id = new_ft.id
        
    dish = Dish(
        restaurant_id=restaurant.id,
        category_id=request.form.get('category_id'),
        food_type_id=food_type_id,
        name=name,
        description=(request.form.get('description') or '').strip(),
        price=price,
        image_url=image_url,
        is_available=request.form.get('is_available') == 'true' or request.form.get('is_available') == 'on'
    )
    db.session.add(dish)
    db.session.commit()
    
    warning = check_dish_spelling(dish.name)
    return jsonify({
        'success': True, 
        'message': 'Dish added successfully.', 
        'spelling_warning': warning,
        'dish': {'id': dish.id, 'name': dish.name}
    }), 201

@bp.route('/api/dishes/edit/<int:id>', methods=['POST'])
@restaurant_required
@csrf.exempt
def edit_dish(id, restaurant):
    dish = db.get_or_404(Dish, id)
    if dish.restaurant_id != restaurant.id:
        return jsonify({'success': False, 'message': 'Ownership verification failed.'}), 403
        
    name = (request.form.get('name') or '').strip()
    price = request.form.get('price', type=float)
    
    if not name or price is None or price < 0:
        return jsonify({'success': False, 'message': 'Valid name and price are required.'}), 400

    image_file = request.files.get('image')
    if image_file and image_file.filename != '':
        image_url = upload_file_to_cloudinary(image_file)
        if image_url:
            dish.image_url = image_url
            
    food_type_id = request.form.get('food_type_id')
    new_food_type_name = (request.form.get('new_food_type') or '').strip()
    if new_food_type_name:
        existing = FoodType.query.filter(func.lower(FoodType.name) == new_food_type_name.lower()).first()
        if existing:
            food_type_id = existing.id
        else:
            new_ft = FoodType(name=new_food_type_name, is_approved=False, requested_by_id=current_user.id)
            db.session.add(new_ft)
            db.session.flush()
            food_type_id = new_ft.id

    dish.name = name
    dish.category_id = request.form.get('category_id')
    dish.food_type_id = food_type_id
    dish.description = (request.form.get('description') or '').strip()
    dish.price = price
    dish.is_available = request.form.get('is_available') == 'true' or request.form.get('is_available') == 'on'
    
    db.session.commit()
    
    warning = check_dish_spelling(dish.name)
    return jsonify({
        'success': True, 
        'message': 'Dish updated successfully.', 
        'spelling_warning': warning
    })

@bp.route('/api/dishes/delete/<int:id>', methods=['POST'])
@owner_required
@csrf.exempt
def delete_dish(id):
    restaurant = get_restaurant()
    if not restaurant:
        return jsonify({'success': False, 'message': 'Please set up your restaurant profile first.'}), 400
    
    dish = db.get_or_404(Dish, id)
    
    if dish.restaurant_id != restaurant.id:
        return jsonify({'success': False, 'message': 'Unauthorized action.'}), 403
    
    try:
        dish.deleted_at = datetime.now()
        dish.is_available = False
        db.session.commit()
        return jsonify({'success': True, 'message': 'Dish deleted successfully.'})
    except Exception as e:
        db.session.rollback()
        print(f"Delete dish error: {e}")
        return jsonify({'success': False, 'message': 'Error deleting dish.'}), 500

@bp.route('/api/orders', methods=['GET'])
@restaurant_required
def get_orders(restaurant):
    status_filter = request.args.get('status')
    query = Order.query.filter_by(restaurant_id=restaurant.id)
    if status_filter:
        query = query.filter_by(status=status_filter)
        
    restaurant_orders = query.options(joinedload(Order.customer))\
                             .order_by(Order.order_date.desc()).all()
    
    return jsonify({'orders': [serialize_order_event(o) for o in restaurant_orders]})

@bp.route('/api/orders/notifications')
@owner_required
def order_notifications():
    """Lightweight polling endpoint for near real-time owner order updates."""
    restaurant = get_restaurant()
    if not restaurant:
        return {'pending_count': 0, 'latest_order': None}

    pending_count = Order.query.filter_by(
        restaurant_id=restaurant.id,
        status='pending'
    ).count()

    latest_pending = Order.query.filter_by(
        restaurant_id=restaurant.id,
        status='pending'
    ).order_by(Order.order_date.desc()).first()

    latest_order = serialize_order_event(latest_pending) if latest_pending else None

    return {
        'pending_count': pending_count,
        'latest_order': latest_order
    }

@bp.route('/api/orders/feed')
@owner_required
def orders_feed():
    """Return recent owner orders for in-page lifecycle synchronization."""
    restaurant = get_restaurant()
    if not restaurant:
        return {'orders': []}

    orders = Order.query.filter_by(restaurant_id=restaurant.id).order_by(Order.order_date.desc()).limit(30).all()
    return {'orders': [serialize_order_event(o) for o in orders]}

@bp.route('/api/media/feed')
@owner_required
def media_feed():
    restaurant = get_restaurant()
    if not restaurant:
        return {'menu_count': 0, 'promo_count': 0, 'video_count': 0}
    menu_count = RestaurantMedia.query.filter_by(restaurant_id=restaurant.id, media_type='menu_image').count()
    promo_count = RestaurantMedia.query.filter_by(restaurant_id=restaurant.id, media_type='promo_image').count()
    video_count = RestaurantMedia.query.filter_by(restaurant_id=restaurant.id, media_type='video').count()
    return {'menu_count': menu_count, 'promo_count': promo_count, 'video_count': video_count}

@bp.route('/api/dishes/feed')
@owner_required
def dishes_feed():
    restaurant = get_restaurant()
    if not restaurant:
        return {'dishes': []}
    dishes = Dish.query.filter_by(restaurant_id=restaurant.id).all()
    return {
        'dishes': [{
            'id': d.id,
            'name': d.name,
            'price': float(d.price),
            'is_available': bool(d.is_available)
        } for d in dishes]
    }

@bp.route('/api/reviews/notifications')
@owner_required
def reviews_notifications():
    restaurant = get_restaurant()
    if not restaurant:
        return {'latest_review': None, 'review_count': 0}
    review_count = Review.query.filter_by(restaurant_id=restaurant.id).count()
    latest = Review.query.filter_by(restaurant_id=restaurant.id).order_by(Review.created_at.desc()).first()
    latest_review = None
    if latest:
        latest_review = {
            'id': latest.id,
            'rating': latest.rating,
            'comment': latest.comment,
            'customer_name': latest.customer.name if latest.customer else 'Customer',
            'created_at': latest.created_at.isoformat() if latest.created_at else None
        }
    return {'latest_review': latest_review, 'review_count': review_count}

@bp.route('/api/orders/update/<int:id>', methods=['POST'])
@restaurant_required
@csrf.exempt
def update_order(id, restaurant):
    order = db.get_or_404(Order, id)
    if order.restaurant_id != restaurant.id:
        return jsonify({'success': False, 'message': 'Unauthorized'}), 403
        
    data = request.get_json() or request.form
    new_status = data.get('status')
    
    VALID_TRANSITIONS = {
        'pending': ['accepted', 'cancelled'],
        'accepted': ['preparing', 'cancelled'],
        'preparing': ['out for delivery', 'cancelled'],
        'out for delivery': ['delivered', 'cancelled'],
        'delivered': ['completed'],
        'cancelled': [],
        'completed': []
    }
    
    if new_status not in VALID_TRANSITIONS.get(order.status, []):
        return jsonify({'success': False, 'message': f'Invalid status transition from {order.status} to {new_status}.'}), 400

    try:
        order.status = new_status
        if new_status == 'accepted':
            est = data.get('estimated_time')
            if est:
                try:
                    order.delivery_time = datetime.now() + timedelta(minutes=int(est))
                except (ValueError, TypeError):
                    pass
        
        db.session.commit()
        return jsonify({'success': True, 'message': f'Order #{order.id} is now {new_status}.', 'status': new_status})
        
    except Exception as e:
        db.session.rollback()
        print(f"Update order error: {e}")
        return jsonify({'success': False, 'message': 'Failed to update order status.'}), 500


@bp.route('/api/reviews', methods=['GET'])
@owner_required
def get_reviews():
    restaurant = get_restaurant()
    if not restaurant:
        return jsonify({'success': False, 'message': 'Restaurant profile required.'}), 400
        
    reviews = Review.query.filter_by(restaurant_id=restaurant.id).order_by(Review.created_at.desc()).all()
    avg_rating = sum(r.rating for r in reviews) / len(reviews) if reviews else 0
    
    results = []
    for r in reviews:
        results.append({
            'id': r.id,
            'rating': r.rating,
            'comment': r.comment,
            'customer_name': r.customer.name if r.customer else 'Anonymous',
            'created_at': r.created_at.isoformat()
        })
    return jsonify({'reviews': results, 'avg_rating': round(avg_rating, 1)})

@bp.route('/api/coupons', methods=['GET'])
@owner_required
def get_coupons():
    """Retrieve all coupons for the restaurant with optional search."""
    restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
    if not restaurant:
        return jsonify({'success': False, 'message': 'Restaurant profile required.'}), 400
    
    search_query = request.args.get('search', '').strip().upper()
    query = Coupon.query.filter_by(restaurant_id=restaurant.id)
    
    if search_query:
        query = query.filter(Coupon.code.contains(search_query))
        
    coupons = query.order_by(Coupon.id.desc()).all()
    
    results = []
    for c in coupons:
        results.append({
            'id': c.id,
            'code': c.code,
            'discount_type': c.discount_type,
            'discount_value': float(c.discount_value),
            'valid_until': c.valid_until.isoformat() if c.valid_until else None,
            'is_active': c.is_active
        })
    return jsonify({'coupons': results})


@bp.route('/api/coupons/add', methods=['POST'])
@owner_required
@csrf.exempt
def add_coupon():
    """Create a new discount coupon."""
    restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
    data = request.get_json()
    
    code = data.get('code', '').strip().upper()
    if not code:
        return jsonify({'success': False, 'message': 'Coupon code is required.'}), 400
        
    # Prevent duplicate codes for the same restaurant
    existing_coupon = Coupon.query.filter_by(restaurant_id=restaurant.id, code=code).first()
    if existing_coupon:
        return jsonify({'success': False, 'message': f'Coupon code "{code}" already exists.'}), 400
        
    # Handle the optional expiration date
    valid_until_str = data.get('valid_until')
    valid_until = None
    if valid_until_str:
        try:
            # Convert HTML datetime-local string to Python datetime object
            valid_until = datetime.fromisoformat(valid_until_str)
        except ValueError:
            pass
            
    new_coupon = Coupon(
        restaurant_id=restaurant.id,
        code=code,
        discount_type=data.get('discount_type', 'percent'),
        discount_value=data.get('discount_value', 0.0),
        valid_until=valid_until,
        is_active=data.get('is_active') == 'true'
    )
    
    try:
        db.session.add(new_coupon)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Coupon created successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Database error while saving coupon.'}), 500
    

@bp.route('/api/coupons/delete/<int:id>', methods=['POST'])
@owner_required
@csrf.exempt
def delete_coupon(id):
    """Delete an existing coupon."""
    restaurant = Restaurant.query.filter_by(owner_id=current_user.id).first()
    coupon = Coupon.query.get_or_404(id)
    
    # Ensure the owner can only delete their own coupons
    if coupon.restaurant_id != restaurant.id:
        return jsonify({'success': False, 'message': 'Unauthorized action.'}), 403
        
    try:
        db.session.delete(coupon)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Coupon deleted successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': 'Database error while deleting.'}), 500

@bp.route('/api/media', methods=['GET', 'POST'])
@restaurant_required
@csrf.exempt
def manage_media(restaurant):
    if request.method == 'POST':
        media_type = request.form.get('media_type') 
        url = None
        
        if media_type in ['menu_image', 'promo_image']:
            image_file = request.files.get('image')
            if image_file and image_file.filename != '':
                url = upload_file_to_cloudinary(image_file)
        elif media_type == 'video':
            video_file = request.files.get('video_file')
            if video_file and video_file.filename != '':
                url = upload_file_to_cloudinary(video_file, resource_type="auto")
            else:
                url = (request.form.get('video_url') or '').strip()
                if url and not (url.startswith('http://') or url.startswith('https://')):
                    return jsonify({'success': False, 'message': 'Invalid video URL.'}), 400
            
        if url:
            new_media = RestaurantMedia(
                restaurant_id=restaurant.id,
                media_type=media_type,
                url=url,
                display_order=request.form.get('display_order', 0, type=int)
            )
            db.session.add(new_media)
            db.session.commit()
            return jsonify({'success': True, 'message': 'Media added.', 'media': {'id': new_media.id, 'url': new_media.url}})
        else:
            return jsonify({'success': False, 'message': 'No file or URL provided.'}), 400

    # GET: Load all media
    media_items = RestaurantMedia.query.filter_by(restaurant_id=restaurant.id).order_by(RestaurantMedia.display_order).all()
    results = []
    for m in media_items:
        results.append({
            'id': m.id,
            'media_type': m.media_type,
            'url': m.url,
            'display_order': m.display_order
        })
    return jsonify({'media': results})

@bp.route('/api/media/delete/<int:id>', methods=['POST'])
@owner_required
@csrf.exempt
def delete_media(id):
    restaurant = get_restaurant()
    media_item = db.get_or_404(RestaurantMedia, id)
    if media_item.restaurant_id == restaurant.id:
        db.session.delete(media_item)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Media deleted.'})
    return jsonify({'success': False, 'message': 'Unauthorized'}), 403

@bp.route('/api/media/reorder', methods=['POST'])
@owner_required
@csrf.exempt
def reorder_media():
    restaurant = get_restaurant()
    data = request.get_json()
    if data and 'items' in data:
        for item in data['items']:
            media_item = db.session.get(RestaurantMedia, item['id'])
            if media_item and media_item.restaurant_id == restaurant.id:
                media_item.display_order = item['display_order']
        db.session.commit()
        return {'success': True}
    return {'success': False}, 400