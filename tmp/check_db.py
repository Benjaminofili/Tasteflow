from app import create_app, db
from app.models import Coupon, Restaurant

app = create_app()
with app.app_context():
    coupons = Coupon.query.all()
    print(f"Total coupons: {len(coupons)}")
    for c in coupons:
        print(f"ID: {c.id}, Code: {c.code}, RestaurantID: {c.restaurant_id}, Active: {c.is_active}, ValidUntil: {c.valid_until}")
    
    restaurants = Restaurant.query.all()
    print(f"\nTotal restaurants: {len(restaurants)}")
    for r in restaurants:
        print(f"ID: {r.id}, Name: {r.name}, OwnerID: {r.owner_id}")
