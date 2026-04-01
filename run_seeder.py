#!/usr/bin/env python3
"""
TasteFlow Database Seeder
Quick runner script for seeding the database
"""

import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from seed_data import seed_database

if __name__ == '__main__':
    print("🚀 TasteFlow Database Seeder")
    print("=" * 40)
    try:
        seed_database()
        print("\n🎉 Seeding completed successfully!")
        print("You can now run the application and enjoy the sample data!")
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        sys.exit(1)
