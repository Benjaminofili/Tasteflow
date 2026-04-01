# TasteFlow Database Seeding

This directory contains scripts to populate your TasteFlow database with realistic sample data based on the original templates.

## 📁 Files

- `seed_data.py` - Main seeding script with comprehensive sample data
- `run_seeder.py` - Simple runner script for easy execution
- `README.md` - This documentation file

## 🚀 Quick Start

### Method 1: Using the Runner Script (Recommended)
```bash
python run_seeder.py
```

### Method 2: Direct Execution
```bash
python seed_data.py
```

### Method 3: From Flask Shell
```bash
flask shell
>>> from seed_data import seed_database
>>> seed_database()
```

## 📊 What Gets Created

### 👥 Users
- **5 Restaurant Owners** with different restaurants
- **4 Customers** with realistic profiles and addresses
- All users have secure password hashes

### 🏪 Restaurants (5 total)
1. **Garden of Spice** - Indian cuisine (Victoria Island)
2. **Mama Tolu's Kitchen** - Nigerian cuisine (Yaba)
3. **The Suya Spot** - Suya specialties (Lekki Phase 1)
4. **Tokyo Noodle House** - Japanese cuisine (Ikeja GRA)
5. **Lagos Burger Co.** - American comfort food (Surulere)

### 🍲 Dishes (25+ total)
- **Appetizers**: Paneer Tikka, Gyoza, etc.
- **Main Courses**: Biryani, Suya, Ramen, Burgers, etc.
- **Beverages**: Lassi, Zobo, Green Tea, Milkshakes
- **Breads**: Naan, etc.
- **Soups**: Egusi Soup, etc.
- Each dish includes realistic descriptions, prices, and images

### 🎟️ Coupons (5 total)
- Percentage-based discounts (10%, 15%, 20%)
- Fixed amount discounts (₦250, ₦500)
- Different validity periods for each restaurant

### 📦 Orders (5 total)
- **Different statuses**: Delivered, Preparing, Pending, Cancelled
- **Realistic order histories** spanning the last 10 days
- **Multiple items per order** with proper pricing
- **Various payment methods**: Cash, Card

### ⭐ Reviews (5 total)
- **4-5 star ratings** for different restaurants
- **Realistic customer feedback**
- Connected to actual customers and restaurants

### 💝 Wishlists (5 total)
- Customers have saved their favorite dishes
- Mix of different cuisines and price ranges

## 🔑 Test Login Credentials

### Customer Account
- **Email**: `adaeze@example.com`
- **Password**: `customer123`
- **Profile**: Adaeze Okonkwo, Victoria Island Lagos

### Restaurant Owner Account
- **Email**: `ada@gardenofspice.com`
- **Password**: `owner123`
- **Restaurant**: Garden of Spice

## 🎯 Sample User Journey

With the seeded data, you can experience:

1. **Browse Restaurants** - See 5 different restaurants with ratings
2. **View Menus** - Each restaurant has 5+ dishes with real data
3. **Add to Cart** - Add items and see real-time cart updates
4. **Place Orders** - Complete checkout process
5. **Track Orders** - View order history and tracking
6. **Manage Profile** - See order statistics and recent orders
7. **Leave Reviews** - Rate restaurants you've ordered from

## 🛠️ Customization

### Adding More Data
Edit `seed_data.py` to:
- Add more restaurants/dishes
- Modify prices and descriptions
- Create different user profiles
- Add more order scenarios

### Preserving Existing Data
Comment out this line in `seed_data.py` if you want to preserve existing data:
```python
# Clear existing data (optional - comment out if you want to preserve data)
# print("🗑️  Clearing existing data...")
# OrderItem.query.delete()
# ... (other delete statements)
```

## 🔒 Security Notes

- All passwords are properly hashed using Werkzeug
- No sensitive data is exposed
- Sample emails use example.com domain
- Phone numbers follow Nigerian format

## 📈 Performance

The seeding script is optimized to:
- Use bulk operations where possible
- Commit transactions in batches
- Provide progress feedback
- Handle foreign key relationships correctly

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Ensure your Flask app is properly configured
   - Check database connection string in config

2. **Foreign Key Constraints**
   - The script handles dependencies correctly
   - Data is added in the right order

3. **Duplicate Data**
   - Script clears existing data by default
   - Comment out clear section to preserve data

### Reset Everything
```bash
python run_seeder.py
```
This will completely reset and reseed your database.

## 🎉 Ready to Go!

After running the seeder, your TasteFlow application will have:
- **Rich, realistic data** for testing
- **Complete user journeys** to explore
- **Various scenarios** for development
- **Professional appearance** for demos

Enjoy your fully populated TasteFlow application! 🚀
