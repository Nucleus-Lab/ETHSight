from backend.database import engine, Base, get_db
from backend.database.user import get_user
from backend.constants import AI_USER_ID, AI_WALLET_ADDRESS
from sqlalchemy import text

def create_ai_user(db):
    """Create the AI user if it doesn't exist"""
    # Check if AI user exists
    ai_user = get_user(db, AI_WALLET_ADDRESS)
    if not ai_user:
        print("Creating AI user...")
        # Set the specific ID for AI user
        with engine.connect() as connection:
            # Temporarily disable the foreign key constraint
            # connection.execute(text("SET FOREIGN_KEY_CHECKS=0"))  # For MySQL
            connection.execute(text("SET CONSTRAINTS ALL DEFERRED")) # PostgreSQL
            
            # Create AI user with specific ID
            connection.execute(
                text(f"""
                INSERT INTO users (user_id, wallet_address, created_at) 
                VALUES ({AI_USER_ID}, '{AI_WALLET_ADDRESS}', CURRENT_TIMESTAMP)
                """)
            )
            
            # Re-enable the foreign key constraint
            # connection.execute(text("SET FOREIGN_KEY_CHECKS=1"))  # For MySQL
            connection.execute(text("SET CONSTRAINTS ALL IMMEDIATE")) # PostgreSQL
            
            connection.commit()
        print("AI user created successfully")
    else:
        print("AI user already exists")

def init_db():
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create AI user
    db = next(get_db())
    try:
        create_ai_user(db)
    finally:
        db.close()

if __name__ == "__main__":
    init_db() 