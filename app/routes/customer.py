from flask import Blueprint, render_template, flash, redirect, url_for, request, session, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Restaurant, Dish, Order, OrderItem, Review, Coupon, Category, FoodType, Wishlist, RestaurantMedia
from app.utils import upload_file_to_cloudinary
from app.utils import serialize_order_event, is_ajax_request
from datetime import datetime, timedelta
from sqlalchemy import func, select, or_
from sqlalchemy.orm import joinedload
from functools import wraps
from app import db, limiter, csrf

bp = Blueprint('customer', __name__, url_prefix='/customer')


# ── Public JSON API (no auth required) ──────────────────────────────────────

@bp.route('/api/restaurants/search')
@limiter.limit("60 per minute")
def api_search_restaurants():
    """Public search API with eager loading to prevent N+1 queries."""
    q            = request.args.get('q', '').strip()
    category_id  = request.args.get('category_id', type=int)
    food_type_id = request.args.get('food_type_id', type=int)
    min_rating   = request.args.get('min_rating', type=int)
    page         = request.args.get('page', 1, type=int)
    per_page     = 12

    # Base query with eager loading
    rest_query = Restaurant.query.options(
        joinedload(Restaurant.dishes),
        joinedload(Restaurant.reviews)
    )

    if category_id or food_type_id:
        rest_query = rest_query.join(Dish)
        if category_id:
            rest_query = rest_query.filter(Dish.category_id == category_id)
        if food_type_id:
            rest_query = rest_query.filter(Dish.food_type_id == food_type_id)

    if q:
        rest_query = rest_query.filter(
            or_(
                Restaurant.name.ilike(f'%{q}%'),
                Restaurant.address.ilike(f'%{q}%')
            )
        )

    # Apply min_rating filter if present
    # (Note: In a pure SQL way this is better, but since we use joinedload, 
    # we can filter in Python or use a subquery/having. Keeping it distinct for now.)
    restaurants_all = rest_query.distinct().all()
    
    if min_rating:
        restaurants_all = [
            r for r in restaurants_all 
            if (sum(rv.rating for rv in r.reviews) / len(r.reviews) if r.reviews else 0) >= min_rating
        ]

    # Simple pagination on the filtered list
    total = len(restaurants_all)
    start = (page - 1) * per_page
    end = start + per_page
    items = restaurants_all[start:end]

    results = []
    for r in items:
        avg = round(sum(rv.rating for rv in r.reviews) / len(r.reviews), 1) if r.reviews else None
        num_dish = len([d for d in r.dishes if d.is_available])
        results.append({
            'id':          r.id,
            'name':        r.name,
            'address':     r.address,
            'description': r.description,
            'logo_url':    r.logo_url,
            'avg_rating':  avg,
            'review_count': len(r.reviews),
            'dish_count':  num_dish,
        })

    return jsonify({
        'restaurants': results,
        'total':       total,
        'pages':       (total + per_page - 1) // per_page,
        'page':        page,
        'has_next':    (page * per_page) < total,
    })


@bp.route('/api/restaurants', methods=['GET'])
# Note: We don't use @login_required here so even guests can browse the dashboard!
def get_all_restaurants():
    """Fetch all registered restaurants for the customer dashboard."""
    try:
        restaurants = Restaurant.query.all()
        
        restaurant_list = []
        for r in restaurants:
            restaurant_list.append({
                'id': r.id,
                'name': r.name,
                'address': r.address,
                'logo_url': r.logo_url,
                'rating': "4.5" # You can make this dynamic later if you add a Reviews table!
            })
            
        return jsonify({'success': True, 'restaurants': restaurant_list}), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': 'Failed to fetch restaurants.'}), 500


@bp.route('/api/restaurant/<int:restaurant_id>', methods=['GET'])
def get_restaurant_menu(restaurant_id):
    try:
        restaurant = Restaurant.query.get_or_404(restaurant_id)
        
        # Get all available dishes for this restaurant
        dishes = Dish.query.filter_by(restaurant_id=restaurant_id, is_available=True).all()
        
        dish_list = []
        for d in dishes:
            dish_list.append({
                'id': d.id,
                'restaurant_id': d.restaurant_id,
                'name': d.name,
                'description': d.description,
                'price': float(d.price),
                'image_url': d.image_url,
                'is_available': d.is_available
            })
            
        return jsonify({
            'success': True,
            'restaurant': {
                'id': restaurant.id,
                'name': restaurant.name,
                'address': restaurant.address,
                'logo_url': restaurant.logo_url
            },
            'dishes': dish_list
        }), 200
        
    except Exception as e:
        return jsonify({'success': False, 'error': 'Failed to fetch menu.'}), 500


@bp.route('/api/restaurants/meta')
def api_restaurant_meta():
    """Return categories and food types for filter dropdowns."""
    categories  = [{'id': c.id, 'name': c.name} for c in Category.query.order_by(Category.name).all()]
    food_types  = [{'id': f.id, 'name': f.name} for f in FoodType.query.order_by(FoodType.name).all()]
    return jsonify({'categories': categories, 'food_types': food_types})

@bp.route('/api/newsletter', methods=['POST'])
def api_newsletter():
    data = request.get_json() or {}
    email = (data.get('email') or '').strip()

    if not email or '@' not in email or '.' not in email:
        return jsonify({'success': False, 'error': 'Please provide a valid email address.'}), 400

    # In this simple app sample, we do not persist subscriptions.
    # Replace with DB or mailing service integration as needed.
    print(f'Newsletter signup: {email}')
    return jsonify({'success': True, 'message': 'Subscribed successfully'}), 200


@bp.route('/api/feedback', methods=['POST'])
def api_feedback():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    rating = data.get('rating')
    comments = (data.get('comments') or '').strip()

    try:
        rating = int(rating)
    except (TypeError, ValueError):
        rating = None

    if rating is None or rating < 1 or rating > 5 or not comments:
        return jsonify({'success': False, 'error': 'Rating (1-5) and comments are required.'}), 400

    print(f'Feedback received ({rating}/5) from {name or "Anonymous"}: {comments}')
    return jsonify({'success': True, 'message': 'Feedback received'}), 200

# ── End Public API ───────────────────────────────────────────────────────────

def customer_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({'success': False, 'error': 'Authentication required'}), 401
        if current_user.role != 'customer':
            return jsonify({'success': False, 'error': 'Customer access only'}), 403
        return func(*args, **kwargs)
    return login_required(wrapper)

# ── Customer Actions API ─────────────────────────────────────────────────────

@bp.route('/wishlist/add/<int:dish_id>', methods=['POST'])
@customer_required
def add_to_wishlist(dish_id):
    dish = db.get_or_404(Dish, dish_id)
    existing = Wishlist.query.filter_by(user_id=current_user.id, dish_id=dish_id).first()
    
    if existing:
        return jsonify({'success': False, 'message': 'Already in wishlist'}), 200
    
    entry = Wishlist(user_id=current_user.id, dish_id=dish_id)
    db.session.add(entry)
    db.session.commit()
    return jsonify({'success': True, 'message': 'Added to wishlist'}), 200

@bp.route('/wishlist/remove/<int:dish_id>', methods=['POST'])
@customer_required
def remove_from_wishlist(dish_id):
    entry = Wishlist.query.filter_by(user_id=current_user.id, dish_id=dish_id).first()
    if entry:
        db.session.delete(entry)
        db.session.commit()
        return jsonify({'success': True, 'message': 'Removed from wishlist'}), 200
    return jsonify({'success': False, 'message': 'Item not found in wishlist'}), 404

@bp.route('/wishlist', methods=['GET'])
@customer_required
def get_wishlist():
    wish_items = Wishlist.query.filter_by(user_id=current_user.id).all()
    results = []
    for item in wish_items:
        d = item.dish
        results.append({
            'id': d.id,
            'name': d.name,
            'price': float(d.price),
            'image_url': d.image_url,
            'restaurant_name': d.restaurant.name if d.restaurant else 'Unknown'
        })
    return jsonify({'wishlist': results})

@bp.route('/cart/add/<int:dish_id>', methods=['POST'])
def add_to_cart(dish_id):
    dish = db.session.get(Dish, dish_id)
    if not dish or not dish.is_available:
        return jsonify({'success': False, 'message': 'Dish not found or unavailable.'}), 404
    
    cart = session.get('cart', {})
    data = request.get_json() or {}
    qty = data.get('quantity', 1)
    
    try:
        qty = int(qty)
    except (ValueError, TypeError):
        qty = 1
    
    dish_id_str = str(dish_id)
    if dish_id_str in cart:
        cart[dish_id_str] += qty
    else:
        cart[dish_id_str] = qty
        
    session['cart'] = cart
    session.modified = True
    
    return jsonify({
        'success': True, 
        'count': sum(cart.values()), 
        'message': f'{dish.name} added to cart.'
    })

@bp.route('/cart/clear', methods=['POST'])
def clear_cart():
    session.pop('cart', None)
    session.pop('applied_coupon_id', None)
    return jsonify({'success': True, 'message': 'Cart cleared.'})

@bp.route('/cart/update/<int:dish_id>/<action>', methods=['POST'])
def update_cart(dish_id, action):
    cart = session.get('cart', {})
    dish_id_str = str(dish_id)
    
    if dish_id_str in cart:
        if action in ['increment', 'add']:
            cart[dish_id_str] += 1
        elif action == 'decrement':
            if cart[dish_id_str] > 1:
                cart[dish_id_str] -= 1
            else:
                del cart[dish_id_str]
        elif action == 'remove':
            del cart[dish_id_str]
            
        session['cart'] = cart
        session.modified = True
        if not cart:
            session.pop('applied_coupon_id', None)
            
    # Return updated JSON
    total = 0.0
    item_qty = 0
    item_subtotal = 0.0
    for did_str, qty in cart.items():
        dish = db.session.get(Dish, int(did_str))
        if dish:
            total += float(dish.price) * qty
            if str(did_str) == dish_id_str:
                item_qty = qty
                item_subtotal = float(dish.price) * qty
    
    return jsonify({
        'success': True, 
        'item_quantity': item_qty, 
        'item_subtotal': item_subtotal, 
        'new_total': total, 
        'count': sum(cart.values()) if cart else 0, 
        'action': action
    })

@bp.route('/cart/remove/<int:dish_id>', methods=['POST'])
def remove_from_cart(dish_id):
    """Explicit remove endpoint for the cart page."""
    return update_cart(dish_id, 'remove')

@bp.route('/api/reorder/<int:order_id>', methods=['POST'])
@customer_required
def api_reorder(order_id):
    """Add all items from a previous order into the current cart."""
    order = db.session.get(Order, order_id)
    if not order or order.customer_id != current_user.id:
        return jsonify({'success': False, 'message': 'Order not found.'}), 404
        
    cart = session.get('cart', {})
    added_count = 0
    for item in order.order_items:
        if item.dish and item.dish.is_available:
            did_str = str(item.dish_id)
            cart[did_str] = cart.get(did_str, 0) + item.quantity
            added_count += 1
        
    if added_count == 0:
        return jsonify({'success': False, 'message': 'None of the items from this order are currently available.'}), 400

    session['cart'] = cart
    session.modified = True
    return jsonify({
        'success': True, 
        'message': f'Added {added_count} items to cart', 
        'count': sum(cart.values())
    })

@bp.route('/cart/apply_coupon', methods=['POST'])
def apply_coupon():
    data = request.get_json() or {}
    code = data.get('coupon_code')
    cart = session.get('cart', {})
    
    if not cart:
        return jsonify({'success': False, 'message': 'Add items to your cart first.'}), 400
        
    coupon = Coupon.query.filter_by(code=code, is_active=True).first()
    
    if not coupon:
        session.pop('applied_coupon_id', None)
        return jsonify({'success': False, 'message': 'Invalid or inactive promo code.'}), 400
        
    if coupon.valid_until and coupon.valid_until < datetime.now():
        session.pop('applied_coupon_id', None)
        return jsonify({'success': False, 'message': 'This promo code has expired.'}), 400

    # Check if coupon applies to any restaurant in the cart
    cart_items = [db.session.get(Dish, int(did)) for did in cart.keys() if db.session.get(Dish, int(did))]
    rest_ids = {dish.restaurant_id for dish in cart_items if dish}
    if coupon.restaurant_id not in rest_ids:
        session.pop('applied_coupon_id', None)
        return jsonify({'success': False, 'message': f'Promo code {code} is only valid for a specific restaurant.'}), 400
        
    session['applied_coupon_id'] = coupon.id
    
    # Calculate discount
    total = 0.0
    for did_str, qty in cart.items():
        dish = db.session.get(Dish, int(did_str))
        if dish:
            total += float(dish.price) * qty
    
    rest_total = sum(
        float(db.session.get(Dish, int(did)).price) * qty
        for did, qty in cart.items()
        if db.session.get(Dish, int(did)) and db.session.get(Dish, int(did)).restaurant_id == coupon.restaurant_id
    )
    
    if coupon.discount_type in ['percent', 'percentage']:
        discount_amount = rest_total * (float(coupon.discount_value) / 100.0)
    else:
        discount_amount = float(coupon.discount_value)
    
    discount_amount = min(discount_amount, rest_total)
    final_total = max(0.0, total - discount_amount)
    
    return jsonify({
        'success': True, 
        'message': f'Promo code {code} applied!', 
        'discount_amount': round(discount_amount, 2), 
        'final_total': round(final_total, 2), 
        'total': round(total, 2)
    })

@bp.route('/checkout', methods=['POST'])
@csrf.exempt
@customer_required
def checkout():
    data = request.get_json() or {}
    
    # Read items from JSON payload (sent by localStorage-based frontend) or session
    items_raw = data.get('items')
    if items_raw:
        # Convert list of items back to a dict/map {dish_id: quantity}
        cart = {str(item['dish_id']): item['quantity'] for item in items_raw}
    else:
        cart = session.get('cart', {})

    if not cart:
        return jsonify({'success': False, 'message': 'Your cart is empty.'}), 400

    address = (data.get('address') or current_user.address or '').strip()
    payment_method = data.get('payment_method', 'cash')
    notes = (data.get('notes') or '').strip()
    
    if not address:
        return jsonify({'success': False, 'message': 'Delivery address is required.'}), 400
        
    try:
        orders_data = {}
        for dish_id_str, qty in cart.items():
            dish = db.session.get(Dish, int(dish_id_str))
            if not dish or not dish.is_available:
                return jsonify({'success': False, 'message': f'Dish {dish_id_str} is no longer available.'}), 400
            
            if dish.restaurant_id not in orders_data:
                orders_data[dish.restaurant_id] = {'total': 0.0, 'items': []}
            
            price = float(dish.price)
            orders_data[dish.restaurant_id]['total'] += price * qty
            orders_data[dish.restaurant_id]['items'].append((dish, qty, price))

        coupon_id = session.get('applied_coupon_id')
        applied_coupon = None
        if coupon_id:
            coupon = db.session.get(Coupon, coupon_id)
            if coupon and coupon.is_active and (not coupon.valid_until or coupon.valid_until >= datetime.now()):
                if coupon.restaurant_id in orders_data:
                    applied_coupon = coupon

        orders_created = []
        for rest_id, o_data in orders_data.items():
            rest_discount = 0.0
            if applied_coupon and applied_coupon.restaurant_id == rest_id:
                rest_total = o_data['total']
                if applied_coupon.discount_type in ['percent', 'percentage']:
                    rest_discount = rest_total * (float(applied_coupon.discount_value) / 100.0)
                else:
                    rest_discount = float(applied_coupon.discount_value)
                
                if hasattr(applied_coupon, 'max_discount') and applied_coupon.max_discount:
                    rest_discount = min(rest_discount, float(applied_coupon.max_discount))
                rest_discount = min(rest_discount, rest_total)

            order = Order(
                customer_id=current_user.id,
                restaurant_id=rest_id,
                total_amount=max(0.0, o_data['total'] - rest_discount),
                discount_amount=rest_discount,
                coupon_id=coupon_id if (applied_coupon and applied_coupon.restaurant_id == rest_id) else None,
                status='pending',
                delivery_address=address,
                payment_method=payment_method
            )
            db.session.add(order)
            db.session.flush()
            
            for dish, qty, price_at_order in o_data['items']:
                db.session.add(OrderItem(
                    order_id=order.id, dish_id=dish.id, 
                    quantity=qty, price=price_at_order
                ))
            orders_created.append(order.id)
            
        db.session.commit()
        session.pop('cart', None)
        session.pop('applied_coupon_id', None)
        session.modified = True
        
        return jsonify({'success': True, 'message': f'Success! {len(orders_created)} order(s) placed.', 'order_ids': orders_created}), 201
        
    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = f"Checkout error: {str(e)}\n{traceback.format_exc()}"
        print(error_details)
        return jsonify({'success': False, 'message': f'Checkout failed: {str(e)}'}), 500

@bp.route('/api/orders', methods=['GET'])
@login_required
def get_customer_orders():
    """Fetch all orders for the current customer with item details."""
    try:
        # Fetch orders sorted by newest first
        orders = Order.query.filter_by(customer_id=current_user.id).order_by(Order.order_date.desc()).all()
        
        order_list = []
        for order in orders:
            # Get restaurant details
            restaurant = Restaurant.query.get(order.restaurant_id)
            
            # Get items for this order
            items = OrderItem.query.filter_by(order_id=order.id).all()
            item_list = []
            for item in items:
                dish = Dish.query.get(item.dish_id)
                item_list.append({
                    'name': dish.name if dish else 'Unknown Item',
                    'quantity': item.quantity,
                    'price': float(item.price)  # Use price from OrderItem (price_at_order)
                })
                
            order_list.append({
                'id': order.id,
                'status': order.status,
                'total_amount': float(order.total_amount),
                'order_date': order.order_date.isoformat(),
                'restaurant_name': restaurant.name if restaurant else 'Unknown Restaurant',
                'restaurant_logo': restaurant.logo_url if restaurant else None,
                'items': item_list
            })
            
        return jsonify({'success': True, 'orders': order_list}), 200
        
    except Exception as e:
        import traceback
        print(f"Error fetching orders: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': 'Failed to fetch orders.'}), 500

@bp.route('/api/order/<int:order_id>', methods=['GET'])
@login_required
def get_single_order(order_id):
    """Fetch details for a specific order to populate the tracking page."""
    try:
        order = Order.query.filter_by(id=order_id, customer_id=current_user.id).first()
        
        if not order:
            return jsonify({'success': False, 'error': 'Order not found.'}), 404
            
        restaurant = Restaurant.query.get(order.restaurant_id)
        
        # Get items
        items = OrderItem.query.filter_by(order_id=order.id).all()
        item_list = []
        for item in items:
            dish = Dish.query.get(item.dish_id)
            item_list.append({
                'name': dish.name if dish else 'Unknown Item',
                'quantity': item.quantity,
                'price': float(item.price)  # Use price from OrderItem
            })
            
        return jsonify({
            'success': True, 
            'order': {
                'id': order.id,
                'status': order.status,
                'total_amount': float(order.total_amount),
                'order_date': order.order_date.isoformat(),
                'restaurant_name': restaurant.name if restaurant else 'Unknown Restaurant',
                'items': item_list
            }
        }), 200
        
    except Exception as e:
        import traceback
        print(f"Error fetching single order: {str(e)}\n{traceback.format_exc()}")
        return jsonify({'success': False, 'error': 'Server error.'}), 500

@bp.route('/my-orders', methods=['GET'])
@customer_required
def get_my_orders():
    orders = Order.query.filter_by(customer_id=current_user.id).order_by(Order.order_date.desc()).all()
    results = []
    for o in orders:
        results.append({
            'id': o.id,
            'restaurant_name': o.restaurant.name if o.restaurant else 'Unknown',
            'total_amount': float(o.total_amount),
            'status': o.status,
            'order_date': o.order_date.isoformat()
        })
    return jsonify({'orders': results})

@bp.route('/order/<int:id>', methods=['GET'])
@customer_required
def get_order_details(id):
    order = db.get_or_404(Order, id)
    if order.customer_id != current_user.id:
        return jsonify({'success': False, 'message': 'Unauthorized access to order.'}), 403
    
    items = []
    for item in order.items:
        items.append({
            'dish_name': item.dish.name if item.dish else 'Unknown',
            'quantity': item.quantity,
            'price': float(item.price),
            'subtotal': float(item.price * item.quantity)
        })
        
    return jsonify({
        'id': order.id,
        'restaurant_name': order.restaurant.name if order.restaurant else 'Unknown',
        'total_amount': float(order.total_amount),
        'discount_amount': float(order.discount_amount),
        'status': order.status,
        'order_date': order.order_date.isoformat(),
        'delivery_address': order.delivery_address,
        'payment_method': order.payment_method,
        'items': items
    })

@bp.route('/restaurant/<int:id>/review', methods=['POST'])
@customer_required
@limiter.limit("5 per minute")
def leave_review(id):
    restaurant = db.get_or_404(Restaurant, id)
    data = request.get_json() or {}
    rating = data.get('rating')
    comment = (data.get('comment') or '').strip()
    
    if not rating or not (1 <= int(rating) <= 5):
        return jsonify({'success': False, 'message': 'Valid rating (1-5) is required.'}), 400

    # Check if they have a delivered or completed order from this restaurant
    has_ordered = Order.query.filter(
        Order.customer_id == current_user.id,
        Order.restaurant_id == id,
        Order.status.in_(['delivered', 'completed'])
    ).first()
    
    if not has_ordered:
        return jsonify({'success': False, 'message': 'You can only review restaurants you have received a delivered order from.'}), 403
        
    review = Review.query.filter_by(customer_id=current_user.id, restaurant_id=id).first()
    
    if review:
        review.rating = int(rating)
        review.comment = comment
        message = 'Review updated successfully!'
    else:
        review = Review(customer_id=current_user.id, restaurant_id=id, rating=int(rating), comment=comment)
        db.session.add(review)
        message = 'Review submitted! Thank you.'
        
    db.session.commit()
    return jsonify({'success': True, 'message': message})

@bp.route('/api/my-active-orders')
@customer_required
def api_active_orders():
    orders = Order.query.filter(
        Order.customer_id == current_user.id,
        Order.status.in_(['pending', 'accepted', 'preparing', 'out for delivery'])
    ).all()
    
    return {'orders': [serialize_order_event(o) for o in orders]}

@bp.route('/api/my-orders/feed')
@customer_required
def api_orders_feed():
    """Return recent customer orders for lifecycle synchronization."""
    orders = Order.query.filter_by(customer_id=current_user.id).order_by(Order.order_date.desc()).limit(20).all()
    return {'orders': [serialize_order_event(o) for o in orders]}

@bp.route('/api/sync-state')
@customer_required
def api_sync_state():
    """Unified customer UI sync payload for cart, wishlist, and coupon panels."""
    cart = session.get('cart', {})
    cart_count = sum(cart.values()) if cart else 0

    wishlist_rows = Wishlist.query.filter_by(user_id=current_user.id).all()
    wishlist_ids = [w.dish_id for w in wishlist_rows]

    cart_items = []
    total = 0.0
    for dish_id_str, qty in cart.items():
        dish = db.session.get(Dish, int(dish_id_str))
        if dish:
            subtotal = float(dish.price) * qty
            total += subtotal
            cart_items.append({'dish': dish, 'quantity': qty, 'subtotal': subtotal})

    coupon_status = None
    discount_amount = 0.0
    coupon_id = session.get('applied_coupon_id')
    if coupon_id:
        coupon = db.session.get(Coupon, coupon_id)
        if not coupon:
            coupon_status = {'state': 'invalid', 'message': 'Coupon no longer exists.'}
        elif not coupon.is_active:
            coupon_status = {'state': 'invalid', 'message': 'Coupon is inactive.'}
        elif coupon.valid_until and coupon.valid_until < datetime.now():
            coupon_status = {'state': 'expired', 'message': 'Coupon has expired.'}
        else:
            rest_total = sum(item['subtotal'] for item in cart_items if item['dish'].restaurant_id == coupon.restaurant_id)
            if rest_total <= 0:
                coupon_status = {'state': 'invalid', 'message': 'Coupon does not match current cart restaurants.'}
            else:
                if coupon.discount_type in ['percent', 'percentage']:
                    discount_amount = rest_total * (float(coupon.discount_value) / 100.0)
                else:
                    discount_amount = float(coupon.discount_value)
                discount_amount = min(discount_amount, rest_total)
                coupon_status = {
                    'state': 'applied',
                    'message': f'Coupon {coupon.code} applied.',
                    'code': coupon.code
                }

    final_total = max(0.0, total - discount_amount)
    return {
        'cart_count': cart_count,
        'wishlist_count': len(wishlist_ids),
        'wishlist_ids': wishlist_ids,
        'coupon_status': coupon_status,
        'discount_amount': round(discount_amount, 2),
        'total': round(total, 2),
        'final_total': round(final_total, 2)
    }

@bp.route('/profile', methods=['GET'])
@customer_required
def get_profile():
    return jsonify({
        'name': current_user.name,
        'email': current_user.email,
        'phone': current_user.phone,
        'address': current_user.address,
        'profile_image': current_user.profile_image
    })

@bp.route('/profile/edit', methods=['POST'])
@csrf.exempt
@customer_required
def edit_profile():
    """Update customer profile details."""
    try:
        data = request.form
        if 'name' in data:
            current_user.name = data.get('name')
        if 'phone' in data:
            current_user.phone = data.get('phone')
        if 'address' in data:
            current_user.address = data.get('address')
        
        # Handle profile image upload
        image_file = request.files.get('profile_image')
        if image_file and image_file.filename != '':
            image_url = upload_file_to_cloudinary(image_file)
            if image_url:
                current_user.profile_image = image_url
        
        db.session.commit()
        return jsonify({'success': True, 'message': 'Profile updated successfully!'}), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'error': 'Database error occurred.'}), 500

