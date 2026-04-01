from app import create_app, db
from app.models import Restaurant

app = create_app()
with app.app_context():
    restaurants = Restaurant.query.all()
    print("--- Restaurants in DB ---")
    for r in restaurants:
        print(f"ID: {r.id} | Name: {r.name} | Owner ID: {r.owner_id}")
    print("------------------------")
