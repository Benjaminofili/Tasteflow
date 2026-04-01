"""
TasteFlow Seed Data Script
Populates the database with realistic sample data based on original templates
"""

from app import create_app, db
from app.models import User, Restaurant, Category, FoodType, Dish, Coupon, Order, OrderItem, Review, Wishlist
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random

def seed_database():
    """Seed the database with sample data"""
    app = create_app()
    
    with app.app_context():
        print("🌱 Starting database seeding...")
        
        # Create tables if not exist
        db.create_all()
        
        # Clear existing data (optional - comment out if you want to preserve data)
        print("🗑️  Clearing existing data...")
        OrderItem.query.delete()
        Order.query.delete()
        Review.query.delete()
        Wishlist.query.delete()
        Coupon.query.delete()
        Dish.query.delete()
        Restaurant.query.delete()
        Category.query.delete()
        FoodType.query.delete()
        User.query.delete()
        
        # Create Food Types
        print("🍽️  Creating food types...")
        food_types = [
            FoodType(name='vegetarian'),
            FoodType(name='non-vegetarian'),
            FoodType(name='vegan'),
            FoodType(name='gluten-free')
        ]
        db.session.add_all(food_types)
        db.session.commit()
        
        # Create Categories
        print("📂 Creating categories...")
        categories = [
            Category(name='Appetizers'),
            Category(name='Main Course'),
            Category(name='Desserts'),
            Category(name='Beverages'),
            Category(name='Soups'),
            Category(name='Salads'),
            Category(name='Rice Dishes'),
            Category(name='Grilled Items'),
            Category(name='Breads'),
            Category(name='Seafood')
        ]
        db.session.add_all(categories)
        db.session.commit()
        
        # Create Users
        print("👥 Creating users...")
        
        # Restaurant Owners
        owner_password = generate_password_hash('owner123')
        owners = [
            User(name='Chef Ada Eze', email='ada@gardenofspice.com', phone='+2348012345678', 
                 address='Victoria Island, Lagos', role='restaurant_owner', password_hash=owner_password),
            User(name='Mama Tolu', email='tolu@matolus.com', phone='+2348023456789', 
                 address='Yaba, Lagos', role='restaurant_owner', password_hash=owner_password),
            User(name='Suya Master', email='suya@thesuyaspot.com', phone='+2348034567890', 
                 address='Lekki Phase 1, Lagos', role='restaurant_owner', password_hash=owner_password),
            User(name='Tokyo Chef', email='chef@tokyonoodle.com', phone='+2348045678901', 
                 address='Ikeja GRA, Lagos', role='restaurant_owner', password_hash=owner_password),
            User(name='Burger King', email='king@lagosburger.com', phone='+2348056789012', 
                 address='Surulere, Lagos', role='restaurant_owner', password_hash=owner_password)
        ]
        db.session.add_all(owners)
        db.session.commit()
        
        # Customers
        customer_password = generate_password_hash('customer123')
        customers = [
            User(name='Adaeze Okonkwo', email='adaeze@example.com', phone='+2348098765432', 
                 address='14 Adeola Odeku Street, Victoria Island, Lagos', role='customer', password_hash=customer_password,
                 profile_image='https://i.pravatar.cc/150?img=12'),
            User(name='Chidi Nwosu', email='chidi@example.com', phone='+2348087654321', 
                 address='Ikoyi, Lagos', role='customer', password_hash=customer_password,
                 profile_image='https://i.pravatar.cc/150?img=45'),
            User(name='Funke Akindele', email='funke@example.com', phone='+2348076543210', 
                 address='Lekki Phase 1, Lagos', role='customer', password_hash=customer_password,
                 profile_image='https://i.pravatar.cc/150?img=67'),
            User(name='Tunde Adeyemi', email='tunde@example.com', phone='+2348065432109', 
                 address='Victoria Island, Lagos', role='customer', password_hash=customer_password,
                 profile_image='https://i.pravatar.cc/150?img=23')
        ]
        db.session.add_all(customers)
        db.session.commit()
        
        # Create Restaurants
        print("🏪 Creating restaurants...")
        restaurants = [
            Restaurant(
                owner_id=owners[0].id,
                name='Garden of Spice',
                address='Victoria Island, Lagos',
                contact='+2348012345678',
                description='Authentic Indian cuisine with a modern twist. Experience the rich flavors of India in the heart of Lagos.',
                logo_url='https://images.unsplash.com/photo-1555126634-323283e090fa?w=300&q=80'
            ),
            Restaurant(
                owner_id=owners[1].id,
                name="Mama Tolu's Kitchen",
                address='Yaba, Lagos',
                contact='+2348023456789',
                description='Traditional Nigerian dishes made with love and authentic recipes passed down through generations.',
                logo_url='https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=300&q=80'
            ),
            Restaurant(
                owner_id=owners[2].id,
                name='The Suya Spot',
                address='Lekki Phase 1, Lagos',
                contact='+2348034567890',
                description='The best suya in Lagos! Premium beef suya, chicken suya, and more with our secret spice blend.',
                logo_url='https://images.unsplash.com/photo-1563379926898-05f4575a45d8?w=300&q=80'
            ),
            Restaurant(
                owner_id=owners[3].id,
                name='Tokyo Noodle House',
                address='Ikeja GRA, Lagos',
                contact='+2348045678901',
                description='Authentic Japanese cuisine specializing in ramen, sushi, and traditional noodle dishes.',
                logo_url='https://images.unsplash.com/photo-1569050467447-ce54b3bbc37d?w=300&q=80'
            ),
            Restaurant(
                owner_id=owners[4].id,
                name='Lagos Burger Co.',
                address='Surulere, Lagos',
                contact='+2348056789012',
                description='Gourmet burgers and American comfort food with a Lagos twist. Fresh ingredients, bold flavors!',
                logo_url='https://images.unsplash.com/photo-1571091718767-18b5b1457add?w=300&q=80'
            )
        ]
        db.session.add_all(restaurants)
        db.session.commit()
        
        # Create Dishes
        print("🍲 Creating dishes...")
        dishes = []
        
        # Garden of Spice dishes
        veg_type = next(ft for ft in food_types if ft.name == 'vegetarian')
        non_veg_type = next(ft for ft in food_types if ft.name == 'non-vegetarian')
        appetizer_cat = next(cat for cat in categories if cat.name == 'Appetizers')
        main_cat = next(cat for cat in categories if cat.name == 'Main Course')
        dessert_cat = next(cat for cat in categories if cat.name == 'Desserts')
        beverage_cat = next(cat for cat in categories if cat.name == 'Beverages')
        bread_cat = next(cat for cat in categories if cat.name == 'Breads')
        
        garden_dishes = [
            Dish(restaurant_id=restaurants[0].id, category_id=appetizer_cat.id, food_type_id=veg_type.id,
                 name='Paneer Tikka', description='Soft cottage cheese marinated in spices and grilled to perfection',
                 price=2800, image_url='https://images.unsplash.com/photo-1586190848861-99aa4a171e90?w=300&q=80'),
            Dish(restaurant_id=restaurants[0].id, category_id=main_cat.id, food_type_id=non_veg_type.id,
                 name='Hyderabadi Biryani', description='Aromatic basmati rice with tender meat and exotic spices',
                 price=4200, image_url='https://images.unsplash.com/photo-1563379091339-03246922d869?w=300&q=80'),
            Dish(restaurant_id=restaurants[0].id, category_id=bread_cat.id, food_type_id=veg_type.id,
                 name='Garlic Butter Naan', description='Soft Indian bread with garlic butter',
                 price=600, image_url='https://images.unsplash.com/photo-1586190848861-99aa4a171e90?w=300&q=80'),
            Dish(restaurant_id=restaurants[0].id, category_id=beverage_cat.id, food_type_id=veg_type.id,
                 name='Mango Lassi', description='Sweet yogurt drink with mango flavor',
                 price=1000, image_url='https://images.unsplash.com/photo-1505252585461-04db1eb84625?w=300&q=80'),
            Dish(restaurant_id=restaurants[0].id, category_id=main_cat.id, food_type_id=veg_type.id,
                 name='Palak Paneer', description='Spinach curry with soft cottage cheese cubes',
                 price=3200, image_url='https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=300&q=80'),
            Dish(restaurant_id=restaurants[0].id, category_id=main_cat.id, food_type_id=non_veg_type.id,
                 name='Butter Chicken', description='Tender chicken in creamy tomato butter sauce',
                 price=3800, image_url='https://images.unsplash.com/photo-1603363833777-ad85367a8308?w=300&q=80')
        ]
        dishes.extend(garden_dishes)
        
        # Mama Tolu's Kitchen dishes
        soup_cat = next(cat for cat in categories if cat.name == 'Soups')
        rice_cat = next(cat for cat in categories if cat.name == 'Rice Dishes')
        
        mama_dishes = [
            Dish(restaurant_id=restaurants[1].id, category_id=soup_cat.id, food_type_id=non_veg_type.id,
                 name='Egusi Soup', description='Melon seed soup with assorted meat and fish',
                 price=2500, image_url='https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=300&q=80'),
            Dish(restaurant_id=restaurants[1].id, category_id=main_cat.id, food_type_id=veg_type.id,
                 name='Pounded Yam', description='Traditional pounded yam served with soup',
                 price=2000, image_url='https://images.unsplash.com/photo-1604503768984-5bc2262a5b4c?w=300&q=80'),
            Dish(restaurant_id=restaurants[1].id, category_id=rice_cat.id, food_type_id=veg_type.id,
                 name='Jollof Rice', description='Flavorful rice cooked in tomato and pepper sauce',
                 price=2800, image_url='https://images.unsplash.com/photo-1604503768984-5bc2262a5b4c?w=300&q=80'),
            Dish(restaurant_id=restaurants[1].id, category_id=beverage_cat.id, food_type_id=veg_type.id,
                 name='Zobo Drink', description='Traditional hibiscus drink',
                 price=450, image_url='https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=300&q=80'),
            Dish(restaurant_id=restaurants[1].id, category_id=main_cat.id, food_type_id=non_veg_type.id,
                 name='Afang Soup', description='Vegetable soup with assorted meat and fish',
                 price=3000, image_url='https://images.unsplash.com/photo-1567620905732-2d1ec7ab7445?w=300&q=80')
        ]
        dishes.extend(mama_dishes)
        
        # The Suya Spot dishes
        suya_dishes = [
            Dish(restaurant_id=restaurants[2].id, category_id=main_cat.id, food_type_id=non_veg_type.id,
                 name='Beef Suya (Large)', description='Premium beef suya with our secret spice blend',
                 price=3500, image_url='https://images.unsplash.com/photo-1563379926898-05f4575a45d8?w=300&q=80'),
            Dish(restaurant_id=restaurants[2].id, category_id=main_cat.id, food_type_id=non_veg_type.id,
                 name='Chicken Suya', description='Tender chicken spiced and grilled to perfection',
                 price=2800, image_url='https://images.unsplash.com/photo-1563379091339-03246922d869?w=300&q=80'),
            Dish(restaurant_id=restaurants[2].id, category_id=beverage_cat.id, food_type_id=veg_type.id,
                 name='Chapman Drink', description='Refreshing mixed fruit drink',
                 price=1000, image_url='https://images.unsplash.com/photo-1544787219-7f47ccb76574?w=300&q=80'),
            Dish(restaurant_id=restaurants[2].id, category_id=main_cat.id, food_type_id=non_veg_type.id,
                 name='Ram Suya', description='Spicy ram meat suya with extra pepper',
                 price=3200, image_url='https://images.unsplash.com/photo-1563379926898-05f4575a45d8?w=300&q=80')
        ]
        dishes.extend(suya_dishes)
        
        # Tokyo Noodle House dishes
        seafood_cat = next(cat for cat in categories if cat.name == 'Seafood')
        grilled_cat = next(cat for cat in categories if cat.name == 'Grilled Items')
        
        tokyo_dishes = [
            Dish(restaurant_id=restaurants[3].id, category_id=main_cat.id, food_type_id=non_veg_type.id,
                 name='Tonkotsu Ramen', description='Rich pork bone broth with noodles and toppings',
                 price=3600, image_url='https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=300&q=80'),
            Dish(restaurant_id=restaurants[3].id, category_id=appetizer_cat.id, food_type_id=non_veg_type.id,
                 name='Gyoza (6 pcs)', description='Japanese dumplings filled with pork and vegetables',
                 price=1800, image_url='https://images.unsplash.com/photo-1555126634-323283e090fa?w=300&q=80'),
            Dish(restaurant_id=restaurants[3].id, category_id=beverage_cat.id, food_type_id=veg_type.id,
                 name='Green Tea', description='Traditional Japanese green tea',
                 price=800, image_url='https://images.unsplash.com/photo-1576092768241-dec231879fc3?w=300&q=80'),
            Dish(restaurant_id=restaurants[3].id, category_id=seafood_cat.id, food_type_id=non_veg_type.id,
                 name='Salmon Sashimi', description='Fresh salmon slices with wasabi and soy sauce',
                 price=4800, image_url='https://images.unsplash.com/photo-1569718212165-3a8278d5f624?w=300&q=80'),
            Dish(restaurant_id=restaurants[3].id, category_id=grilled_cat.id, food_type_id=non_veg_type.id,
                 name='Teriyaki Chicken', description='Grilled chicken with teriyaki glaze',
                 price=3200, image_url='https://images.unsplash.com/photo-1603363833777-ad85367a8308?w=300&q=80')
        ]
        dishes.extend(tokyo_dishes)
        
        # Lagos Burger Co. dishes
        salad_cat = next(cat for cat in categories if cat.name == 'Salads')
        
        burger_dishes = [
            Dish(restaurant_id=restaurants[4].id, category_id=main_cat.id, food_type_id=non_veg_type.id,
                 name='Double Smash Burger', description='Two beef patties with cheese, lettuce, and special sauce',
                 price=4000, image_url='https://images.unsplash.com/photo-1571091718767-18b5b1457add?w=300&q=80'),
            Dish(restaurant_id=restaurants[4].id, category_id=main_cat.id, food_type_id=veg_type.id,
                 name='Veggie Burger', description='Plant-based patty with fresh vegetables',
                 price=3200, image_url='https://images.unsplash.com/photo-1565299624946-b28f40a0ca4b?w=300&q=80'),
            Dish(restaurant_id=restaurants[4].id, category_id=main_cat.id, food_type_id=non_veg_type.id,
                 name='Loaded Fries', description='Crispy fries with cheese, bacon, and sour cream',
                 price=1100, image_url='https://images.unsplash.com/photo-1632763026476-43798ab9b8c4?w=300&q=80'),
            Dish(restaurant_id=restaurants[4].id, category_id=salad_cat.id, food_type_id=veg_type.id,
                 name='Caesar Salad', description='Fresh romaine lettuce with caesar dressing and croutons',
                 price=1800, image_url='https://images.unsplash.com/photo-1525373612132-b3e820b87cea?w=300&q=80'),
            Dish(restaurant_id=restaurants[4].id, category_id=beverage_cat.id, food_type_id=veg_type.id,
                 name='Milkshake', description='Thick creamy milkshake with various flavors',
                 price=1200, image_url='https://images.unsplash.com/photo-1565900899078-3a273613c926?w=300&q=80')
        ]
        dishes.extend(burger_dishes)
        
        db.session.add_all(dishes)
        db.session.commit()
        
        # Create Coupons
        print("🎟️  Creating coupons...")
        coupons = [
            Coupon(restaurant_id=restaurants[0].id, code='TASTE20', discount_type='percent', 
                   discount_value=20, valid_until=datetime.now() + timedelta(days=30)),
            Coupon(restaurant_id=restaurants[1].id, code='MAMA10', discount_type='percent', 
                   discount_value=10, valid_until=datetime.now() + timedelta(days=15)),
            Coupon(restaurant_id=restaurants[2].id, code='SUYA15', discount_type='percent', 
                   discount_value=15, valid_until=datetime.now() + timedelta(days=20)),
            Coupon(restaurant_id=restaurants[3].id, code='TOKYO500', discount_type='fixed', 
                   discount_value=500, valid_until=datetime.now() + timedelta(days=25)),
            Coupon(restaurant_id=restaurants[4].id, code='BURGER250', discount_type='fixed', 
                   discount_value=250, valid_until=datetime.now() + timedelta(days=10))
        ]
        db.session.add_all(coupons)
        db.session.commit()
        
        # Create Orders
        print("📦 Creating orders...")
        orders = []
        
        # Sample orders with different statuses
        order_data = [
            {
                'customer': customers[0],
                'restaurant': restaurants[0],
                'status': 'delivered',
                'items': [
                    {'dish': garden_dishes[0], 'quantity': 1, 'price': 2800},  # Paneer Tikka
                    {'dish': garden_dishes[1], 'quantity': 2, 'price': 4200},  # Hyderabadi Biryani
                    {'dish': garden_dishes[2], 'quantity': 3, 'price': 600},   # Garlic Butter Naan
                    {'dish': garden_dishes[3], 'quantity': 1, 'price': 1000},  # Mango Lassi
                ],
                'date': datetime.now() - timedelta(days=5)
            },
            {
                'customer': customers[0],
                'restaurant': restaurants[2],
                'status': 'preparing',
                'items': [
                    {'dish': suya_dishes[0], 'quantity': 1, 'price': 3500},  # Beef Suya
                    {'dish': suya_dishes[3], 'quantity': 1, 'price': 1000},  # Chapman Drink
                ],
                'date': datetime.now() - timedelta(hours=1)
            },
            {
                'customer': customers[1],
                'restaurant': restaurants[1],
                'status': 'pending',
                'items': [
                    {'dish': mama_dishes[0], 'quantity': 1, 'price': 2500},  # Egusi Soup
                    {'dish': mama_dishes[1], 'quantity': 1, 'price': 2000},  # Pounded Yam
                    {'dish': mama_dishes[2], 'quantity': 1, 'price': 2800},  # Jollof Rice
                    {'dish': mama_dishes[3], 'quantity': 2, 'price': 450},   # Zobo Drink
                ],
                'date': datetime.now() - timedelta(minutes=30)
            },
            {
                'customer': customers[2],
                'restaurant': restaurants[3],
                'status': 'delivered',
                'items': [
                    {'dish': tokyo_dishes[0], 'quantity': 2, 'price': 3600},  # Tonkotsu Ramen
                    {'dish': tokyo_dishes[1], 'quantity': 1, 'price': 1800},  # Gyoza
                    {'dish': tokyo_dishes[2], 'quantity': 1, 'price': 800},   # Green Tea
                ],
                'date': datetime.now() - timedelta(days=7)
            },
            {
                'customer': customers[3],
                'restaurant': restaurants[4],
                'status': 'cancelled',
                'items': [
                    {'dish': burger_dishes[0], 'quantity': 1, 'price': 4000},  # Double Smash Burger
                    {'dish': burger_dishes[2], 'quantity': 1, 'price': 1100},  # Loaded Fries
                ],
                'date': datetime.now() - timedelta(days=10)
            }
        ]
        
        for order_info in order_data:
            total_amount = sum(item['price'] * item['quantity'] for item in order_info['items'])
            
            order = Order(
                customer_id=order_info['customer'].id,
                restaurant_id=order_info['restaurant'].id,
                total_amount=total_amount,
                status=order_info['status'],
                delivery_address=order_info['customer'].address,
                payment_method=random.choice(['cash', 'card']),
                order_date=order_info['date']
            )
            orders.append(order)
            db.session.add(order)
            db.session.flush()  # Get the order ID
            
            # Add order items
            for item_info in order_info['items']:
                order_item = OrderItem(
                    order_id=order.id,
                    dish_id=item_info['dish'].id,
                    quantity=item_info['quantity'],
                    price=item_info['price']
                )
                db.session.add(order_item)
        
        db.session.commit()
        
        # Create Reviews
        print("⭐ Creating reviews...")
        reviews = [
            Review(customer_id=customers[2].id, restaurant_id=restaurants[3].id, rating=4,
                   comment='Great ramen! Very authentic taste.'),
            Review(customer_id=customers[0].id, restaurant_id=restaurants[0].id, rating=5,
                   comment='Amazing Indian food! The biryani is fantastic.'),
            Review(customer_id=customers[1].id, restaurant_id=restaurants[1].id, rating=4,
                   comment='Traditional Nigerian dishes, just like home.'),
            Review(customer_id=customers[3].id, restaurant_id=restaurants[4].id, rating=3,
                   comment='Good burgers but a bit pricey.'),
            Review(customer_id=customers[2].id, restaurant_id=restaurants[2].id, rating=5,
                   comment='Best suya in Lagos! The spice blend is perfect.')
        ]
        db.session.add_all(reviews)
        db.session.commit()
        
        # Create Wishlists
        print("💝 Creating wishlists...")
        wishlists = [
            Wishlist(user_id=customers[0].id, dish_id=garden_dishes[1].id),  # Adaeze -> Hyderabadi Biryani
            Wishlist(user_id=customers[0].id, dish_id=garden_dishes[5].id),  # Adaeze -> Butter Chicken
            Wishlist(user_id=customers[1].id, dish_id=mama_dishes[0].id),  # Chidi -> Egusi Soup
            Wishlist(user_id=customers[2].id, dish_id=tokyo_dishes[0].id),  # Funke -> Tonkotsu Ramen
            Wishlist(user_id=customers[3].id, dish_id=burger_dishes[0].id),  # Tunde -> Double Smash Burger
        ]
        db.session.add_all(wishlists)
        db.session.commit()
        
        print("✅ Database seeding completed successfully!")
        print(f"📊 Summary:")
        print(f"   - Users: {User.query.count()} ({len(owners)} owners, {len(customers)} customers)")
        print(f"   - Restaurants: {Restaurant.query.count()}")
        print(f"   - Dishes: {Dish.query.count()}")
        print(f"   - Orders: {Order.query.count()}")
        print(f"   - Reviews: {Review.query.count()}")
        print(f"   - Coupons: {Coupon.query.count()}")
        print(f"   - Wishlists: {Wishlist.query.count()}")
        
        print("\n🔑 Login Credentials:")
        print("   Customer: adaeze@example.com / customer123")
        print("   Owner: ada@gardenofspice.com / owner123")

if __name__ == '__main__':
    seed_database()
