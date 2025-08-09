#!/usr/bin/env python3
"""
Setup script for creating a test SQLite database with sample data.
This allows you to test the Analyst Agent without needing a full database setup.
"""

import sqlite3
import os
from pathlib import Path

def create_test_database():
    """Create a test SQLite database with sample e-commerce data."""
    
    # Create data directory if it doesn't exist
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)
    
    # Database file path
    db_path = data_dir / "test_ecommerce.db"
    
    print(f"🗄️  Creating test database: {db_path}")
    
    # Read the SQL file
    sql_file = Path("examples/sample_data.sql")
    if not sql_file.exists():
        print(f"❌ SQL file not found: {sql_file}")
        return False
    
    with open(sql_file, 'r') as f:
        sql_commands = f.read()
    
    # Connect to database and execute SQL
    try:
        with sqlite3.connect(db_path) as conn:
            # Enable foreign keys
            conn.execute("PRAGMA foreign_keys = ON")
            
            # Execute all SQL commands
            conn.executescript(sql_commands)
            
            # Verify the data was created
            cursor = conn.cursor()
            
            # Get table counts
            tables = ['customers', 'products', 'orders', 'order_items']
            print("\n📊 Database Summary:")
            print("=" * 40)
            
            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"• {table.capitalize()}: {count} records")
            
            # Get revenue summary
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT customer_id) as customers,
                    COUNT(*) as orders,
                    printf('$%.2f', SUM(total_amount)) as revenue
                FROM orders 
                WHERE status = 'completed'
            """)
            
            customers, orders, revenue = cursor.fetchone()
            print(f"• Active customers: {customers}")
            print(f"• Completed orders: {orders}")
            print(f"• Total revenue: {revenue}")
            
            # Sample queries for testing
            print("\n💡 Sample queries to try:")
            print("=" * 40)
            sample_queries = [
                "Show me total sales by month for the last 6 months",
                "What are the top 5 products by revenue?",
                "How many orders do we have by customer segment?",
                "What is the average order value by country?",
                "Which product categories are performing best?",
                "Show me monthly revenue trends",
                "What is our customer retention rate?"
            ]
            
            for i, query in enumerate(sample_queries, 1):
                print(f"{i}. {query}")
            
            print(f"\n✅ Test database created successfully!")
            print(f"📍 Location: {db_path.absolute()}")
            print(f"🔗 Connection string for frontend:")
            print(f"   Database: sqlite:///{db_path.absolute()}")
            print(f"   (Or just use: {db_path.name})")
            
            return True
            
    except Exception as e:
        print(f"❌ Error creating database: {e}")
        return False

def test_database_connection():
    """Test the database connection and show sample data."""
    db_path = Path("data/test_ecommerce.db")
    
    if not db_path.exists():
        print("❌ Test database not found. Run create_test_database() first.")
        return False
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            
            # Test a simple query
            cursor.execute("""
                SELECT 
                    strftime('%Y-%m', order_date) as month,
                    COUNT(*) as orders,
                    printf('$%.2f', SUM(total_amount)) as revenue
                FROM orders 
                WHERE status = 'completed'
                GROUP BY month
                ORDER BY month
            """)
            
            results = cursor.fetchall()
            
            print("🧪 Test Query - Monthly Sales:")
            print("=" * 40)
            for month, orders, revenue in results:
                print(f"{month}: {orders} orders, {revenue}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error testing database: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Setting up test database for Analyst Agent...")
    print()
    
    success = create_test_database()
    
    if success:
        print()
        print("🧪 Testing database connection...")
        test_database_connection()
        
        print()
        print("🎉 Setup complete! You can now:")
        print("1. Start the frontend: cd frontend && npm run dev")
        print("2. Start the API: python run.py")
        print("3. Open http://localhost:3000 in your browser")
        print("4. Select 'SQLite' as the database dialect")
        print("5. Use 'test_ecommerce.db' as the database name")
        print("6. Try any of the sample questions!")
    else:
        print("❌ Setup failed. Please check the error messages above.") 