#!/usr/bin/env python3
"""
Check the current state of the database migration
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def check_migration_state():
    """Check if migration was partially applied."""
    
    load_dotenv()
    engine = create_engine(os.getenv("DATABASE_URL"))
    
    try:
        with engine.connect() as conn:
            print("🔍 Checking current database state...")
            
            # Check strategies table columns
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'strategies' 
                AND column_name IN ('buy_condition_threshold', 'sell_condition_threshold', 
                                   'position_size', 'max_position_value')
                ORDER BY column_name;
            """))
            
            print("\n📊 Strategies table columns:")
            for row in result:
                print(f"   {row[0]}: {row[1]}")
            
            # Check for any temp columns (signs of partial migration)
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'strategies' 
                AND column_name LIKE '%_new'
                ORDER BY column_name;
            """))
            
            temp_cols = [row[0] for row in result]
            if temp_cols:
                print(f"\n⚠️  Found temporary columns: {temp_cols}")
                print("   Migration was partially applied and needs rollback first")
                return "partial"
            
            # Check backtest_histories table
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'backtest_histories' 
                AND column_name IN ('total_return', 'avg_return', 'win_rate')
                ORDER BY column_name;
            """))
            
            print("\n📊 Backtest_histories table columns:")
            for row in result:
                print(f"   {row[0]}: {row[1]}")
            
            # Check migration history
            try:
                result = conn.execute(text("SELECT version_num FROM alembic_version;"))
                version = result.scalar()
                print(f"\n📋 Current migration version: {version}")
                if version:
                    return "migrated"
                else:
                    return "clean"
            except:
                print("\n📋 No alembic_version table found - clean state")
                return "clean"
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return "error"

if __name__ == "__main__":
    state = check_migration_state()
    
    if state == "partial":
        print("\n🔄 Next step: Run rollback first")
        print("   python run_migration.py rollback")
    elif state == "migrated":
        print("\n✅ Migration already applied")
    elif state == "clean":
        print("\n🔄 Ready for migration")
        print("   python run_migration.py")
    else:
        print("\n❌ Please check database connection")

