#!/usr/bin/env python3
"""
Database Migration Runner
Safely converts string columns to numeric types for exact precision in financial calculations.
"""

import os
import sys
from dotenv import load_dotenv
from alembic.config import Config
from alembic import command

def run_migration():
    """Run the database migration with proper error handling."""
    
    # Load environment variables
    load_dotenv()
    
    # Check if DATABASE_URL is set
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ Error: DATABASE_URL environment variable is not set!")
        print("Please set your DATABASE_URL in your .env file")
        return False
    
    print("🚀 Starting database migration...")
    print(f"📊 Database URL: {database_url[:20]}...")  # Show partial URL for verification
    
    try:
        # Create Alembic configuration
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        
        # Check current database state
        print("📋 Checking current migration state...")
        command.current(alembic_cfg)
        
        # Run the migration
        print("⬆️  Running migration: convert_string_to_numeric_fields")
        command.upgrade(alembic_cfg, "head")
        
        print("✅ Migration completed successfully!")
        print("\n📊 Changes made:")
        print("   • strategies.buy_condition_threshold: STRING → NUMERIC(20,8)")
        print("   • strategies.sell_condition_threshold: STRING → NUMERIC(20,8)")
        print("   • strategies.position_size: STRING → NUMERIC(20,8)")
        print("   • strategies.max_position_value: STRING → NUMERIC(20,2)")
        print("   • backtest_histories.total_return: FLOAT → NUMERIC(15,8)")
        print("   • backtest_histories.avg_return: FLOAT → NUMERIC(15,8)")
        print("   • backtest_histories.win_rate: FLOAT → NUMERIC(5,4)")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        print("\n🔧 Troubleshooting:")
        print("   1. Check your DATABASE_URL is correct")
        print("   2. Ensure the database is accessible")
        print("   3. Verify you have necessary permissions")
        print("   4. Check that existing data can be converted to numeric")
        return False

def rollback_migration():
    """Rollback the migration if needed."""
    
    # Load environment variables
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ Error: DATABASE_URL environment variable is not set!")
        return False
    
    try:
        print("⬇️  Rolling back migration...")
        
        # Create Alembic configuration
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", database_url)
        
        # Rollback one step
        command.downgrade(alembic_cfg, "-1")
        
        print("✅ Rollback completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Rollback failed: {str(e)}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        success = rollback_migration()
    else:
        success = run_migration()
    
    sys.exit(0 if success else 1) 