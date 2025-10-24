#!/usr/bin/env python3
"""
Database setup script for Real-Jobs platform.
Run this script to initialize the database schema.
"""

import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from app.database import initialize_database

if __name__ == "__main__":
    print("🚀 Setting up Real-Jobs database...")
    
    success = initialize_database()
    
    if success:
        print("✅ Database setup completed successfully!")
        print("\nNext steps:")
        print("1. Start the services: docker-compose up -d")
        print("2. Run a test crawl: python -m scrapper.workflow")
    else:
        print("❌ Database setup failed!")
        print("Check your database connection and try again.")
        sys.exit(1)