#!/usr/bin/env python3
"""
Debug script to check database values before migration
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

def check_data():
    """Check the current data values that might cause migration issues."""
    
    # Load environment variables
    load_dotenv()
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ Error: DATABASE_URL environment variable is not set!")
        return
    
    print("🔍 Checking current database values...")
    
    engine = create_engine(database_url)
    
    try:
        with engine.connect() as conn:
            # Check win_rate values
            print("\n📊 Win Rate Values:")
            result = conn.execute(text("""
                SELECT 
                    MIN(win_rate) as min_val,
                    MAX(win_rate) as max_val,
                    AVG(win_rate) as avg_val,
                    COUNT(*) as total_count,
                    COUNT(CASE WHEN win_rate > 10 THEN 1 END) as over_10_count
                FROM backtest_histories 
                WHERE win_rate IS NOT NULL
            """))
            
            for row in result:
                print(f"   Min: {row[0]}")
                print(f"   Max: {row[1]}")
                print(f"   Avg: {row[2]}")
                print(f"   Total records: {row[3]}")
                print(f"   Values > 10: {row[4]}")
            
            # Check some sample values
            print("\n📋 Sample Win Rate Values:")
            result = conn.execute(text("""
                SELECT win_rate, COUNT(*) as count 
                FROM backtest_histories 
                WHERE win_rate IS NOT NULL 
                GROUP BY win_rate 
                ORDER BY win_rate DESC 
                LIMIT 10
            """))
            
            for row in result:
                print(f"   {row[0]} (appears {row[1]} times)")
            
            # Check other numeric fields
            print("\n📊 Other Numeric Fields:")
            
            # Check strategies table
            result = conn.execute(text("""
                SELECT 
                    COUNT(*) as total_strategies,
                    COUNT(buy_condition_threshold) as buy_thresh_count,
                    COUNT(sell_condition_threshold) as sell_thresh_count,
                    COUNT(position_size) as pos_size_count,
                    COUNT(max_position_value) as max_pos_count
                FROM strategies
            """))
            
            for row in result:
                print(f"   Total strategies: {row[0]}")
                print(f"   Buy thresholds: {row[1]}")
                print(f"   Sell thresholds: {row[2]}")
                print(f"   Position sizes: {row[3]}")
                print(f"   Max position values: {row[4]}")
            
            # Check for any non-numeric string values
            print("\n🔍 Checking for non-numeric string values:")
            result = conn.execute(text("""
                SELECT 
                    buy_condition_threshold,
                    sell_condition_threshold,
                    position_size,
                    max_position_value
                FROM strategies 
                WHERE buy_condition_threshold IS NOT NULL 
                   OR sell_condition_threshold IS NOT NULL 
                   OR position_size IS NOT NULL 
                   OR max_position_value IS NOT NULL
                LIMIT 5
            """))
            
            for row in result:
                print(f"   Buy: {row[0]} | Sell: {row[1]} | Size: {row[2]} | Max: {row[3]}")
                
    except Exception as e:
        print(f"❌ Error checking data: {str(e)}")

if __name__ == "__main__":
    check_data()