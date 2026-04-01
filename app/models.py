from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

class User(UserMixin, db.Model):
    """
    User model for authentication and profile management.
    Supports roles: 'customer', 'owner', 'admin'.
    """
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True) # Unique email for identity
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    role = db.Column(db.String(20), default='customer', index=True)  # ← ADD INDEX (frequently filtered)
    profile_image = db.Column(db.String(255))
    admin_id = db.Column(db.String(20), unique=True, nullable=True)  # ← ADD FOR ADMINS
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), index=True)
    
    # Password Reset Fields
    reset_token = db.Column(db.String(100), unique=True, nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def generate_reset_token(self):
        import secrets
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.now() + timedelta(hours=1)
        return self.reset_token
    
    def verify_reset_token(self, token):
        if self.reset_token != token:
            return False
        if not self.reset_token_expires or self.reset_token_expires < datetime.now():
            return False
        return True
    
    def clear_reset_token(self):
        self.reset_token = None
        self.reset_token_expires = None

    def is_wishlisted(self, dish_id):
        
        return Wishlist.query.filter_by(user_id=self.id, dish_id=dish_id).first() is not None

class Restaurant(db.Model):
    """
    Restaurant model representing a digital storefront.
    Owned by a User with the 'owner' role.
    """
    __tablename__ = 'restaurants'
    id = db.Column(db.Integer, primary_key=True)
    owner_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True)
    name = db.Column(db.String(100), nullable=False, index=True)  # ← ADD INDEX (searchable)
    address = db.Column(db.Text, nullable=False)
    contact = db.Column(db.String(20))
    description = db.Column(db.Text)
    logo_url = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    owner = db.relationship('User', backref='restaurants')

class RestaurantMedia(db.Model):
    __tablename__ = 'restaurant_media'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    media_type = db.Column(db.String(20), nullable=False) # 'menu', 'video'
    url = db.Column(db.String(255), nullable=False)
    display_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    restaurant = db.relationship('Restaurant', backref='media')

class Coupon(db.Model):
    __tablename__ = 'coupons'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False, index=True)  # ← ADD INDEX
    code = db.Column(db.String(50), nullable=False, index=True)  # ← ADD INDEX (frequently queried)
    discount_type = db.Column(db.String(20), nullable=False)
    discount_value = db.Column(db.Numeric(10,2), nullable=False)
    valid_until = db.Column(db.DateTime, nullable=True, index=True)  # ← ADD INDEX
    is_active = db.Column(db.Boolean, default=True, index=True)  # ← ADD INDEX
    
    restaurant = db.relationship('Restaurant', backref='coupons')
    
    __table_args__ = (
        db.UniqueConstraint('restaurant_id', 'code', name='unique_coupon_code_per_restaurant'),
    )

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

class FoodType(db.Model):
    __tablename__ = 'food_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    is_approved = db.Column(db.Boolean, default=True)
    requested_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    requested_by = db.relationship('User', foreign_keys=[requested_by_id])

class Dish(db.Model):
    """
    Dish model representing food items available in a restaurant.
    Linked to a Category and a FoodType (e.g., Veg/Non-Veg).
    """
    __tablename__ = 'dishes'
    id = db.Column(db.Integer, primary_key=True)
    restaurant_id = db.Column(
        db.Integer, 
        db.ForeignKey('restaurants.id', ondelete='CASCADE'),  # ← DELETE dishes when restaurant deleted
        nullable=False, 
        index=True
    )
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), index=True)
    food_type_id = db.Column(db.Integer, db.ForeignKey('food_types.id'), index=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10,2), nullable=False)
    image_url = db.Column(db.String(255))
    is_available = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    deleted_at = db.Column(db.DateTime, nullable=True, index=True)  # ← ADD THIS
    
    restaurant = db.relationship('Restaurant', backref='dishes')
    category = db.relationship('Category')
    food_type = db.relationship('FoodType')
    
    __table_args__ = (
        db.CheckConstraint('price > 0', name='positive_price'),
    )
    
    @staticmethod
    def active():
        return Dish.query.filter(Dish.deleted_at.is_(None))

class Order(db.Model):
    """
    Order model for tracking food purchases.
    Maintains status lifecycle: pending -> accepted -> preparing -> en_route -> delivered.
    """
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)  # ← ADD INDEX
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False, index=True)  # ← ADD INDEX
    order_date = db.Column(db.DateTime, default=db.func.current_timestamp(), index=True)  # ← ADD INDEX
    total_amount = db.Column(db.Numeric(10,2), nullable=False)
    status = db.Column(db.String(20), default='pending', index=True)  # ← ADD INDEX (frequently filtered)
    delivery_address = db.Column(db.Text, nullable=False)
    delivery_time = db.Column(db.DateTime)
    payment_method = db.Column(db.String(20), default='cash')
    coupon_id = db.Column(db.Integer, db.ForeignKey('coupons.id'), nullable=True)
    discount_amount = db.Column(db.Numeric(10,2), default=0)
    
    customer = db.relationship('User', foreign_keys=[customer_id], backref='orders')
    restaurant = db.relationship('Restaurant', backref='orders')
    coupon = db.relationship('Coupon')
    
    # ← ADD COMPOSITE INDEX for common queries
    __table_args__ = (
        db.Index('idx_customer_status', 'customer_id', 'status'),
        db.Index('idx_restaurant_status', 'restaurant_id', 'status'),
        db.Index('idx_restaurant_date', 'restaurant_id', 'order_date'),
        db.CheckConstraint('total_amount >= 0', name='non_negative_total'),  # ← ADD CHECK
        db.CheckConstraint('discount_amount >= 0', name='non_negative_discount'),  # ← ADD CHECK
    )

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False, index=True)  # ← ADD INDEX
    dish_id = db.Column(db.Integer, db.ForeignKey('dishes.id'), nullable=False, index=True)  # ← ADD INDEX
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Numeric(10,2), nullable=False)
    
    order = db.relationship('Order', backref='items')
    dish = db.relationship('Dish')
    
    __table_args__ = (
        db.CheckConstraint('quantity > 0', name='positive_quantity'),  # ← ADD CHECK
        db.CheckConstraint('price >= 0', name='non_negative_price'),  # ← ADD CHECK
    )

class Review(db.Model):
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)  # ← Make NOT NULL
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), index=True)
    
    customer = db.relationship('User', foreign_keys=[customer_id], backref='reviews')
    restaurant = db.relationship('Restaurant', backref='reviews')
    
    __table_args__ = (
        db.UniqueConstraint('customer_id', 'restaurant_id', name='unique_customer_restaurant'),
        db.CheckConstraint('rating >= 1 AND rating <= 5', name='valid_rating'),  # ← ADD CHECK
    )

class Wishlist(db.Model):
    __tablename__ = 'wishlists'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)  # ← ADD INDEX
    dish_id = db.Column(db.Integer, db.ForeignKey('dishes.id'), nullable=False, index=True)  # ← ADD INDEX
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp())
    
    user = db.relationship('User', backref='wishlists')
    dish = db.relationship('Dish', backref='wishlisted_by')
    
    __table_args__ = (
        db.UniqueConstraint('user_id', 'dish_id', name='unique_user_dish_wishlist'),
    )

class AdminAuditLog(db.Model):
    __tablename__ = 'admin_audit_logs'
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    action = db.Column(db.String(100), nullable=False, index=True)  # e.g., 'delete_category', 'approve_food_type'
    target_type = db.Column(db.String(50), index=True)  # e.g., 'Category', 'FoodType', 'User'
    target_id = db.Column(db.Integer, index=True)
    details = db.Column(db.Text)  # JSON string with details
    ip_address = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=db.func.current_timestamp(), index=True)
    
    admin = db.relationship('User', foreign_keys=[admin_id])


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))