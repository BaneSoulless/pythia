"""
Capital Reset Script - Seeds 1000 EUR Paper Trading Balance
"""
import sys
import os
import json

# Inject backend path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.db.database import SessionLocal, engine, Base
from app.db.models import User, Portfolio, Trade
from app.core.auth import create_user
from decimal import Decimal

# Load config
with open("config.json", "r") as f:
    config = json.load(f)

INITIAL_BALANCE = Decimal(str(config.get("paper_trading", {}).get("initial_balance", 1000.0)))
CURRENCY = config.get("paper_trading", {}).get("currency", "EUR")

def reset_capital():
    print(f">>> INITIATING CAPITAL RESET TO {INITIAL_BALANCE} {CURRENCY} <<<")
    
    # 1. Drop and recreate all tables (FLUSH)
    print("    [FLUSH] Dropping existing tables...")
    Base.metadata.drop_all(bind=engine)
    print("    [CREATE] Recreating schema...")
    Base.metadata.create_all(bind=engine)
    
    # 2. Seed Admin User
    db = SessionLocal()
    try:
        print("    [SEED] Creating admin user...")
        create_user(db, "admin", "admin@nexus.com", "admin")
        
        # 3. Seed Portfolio with calibrated balance
        user = db.query(User).filter(User.username == "admin").first()
        if user:
            portfolio = Portfolio(
                user_id=user.id,
                name="Paper Trading Portfolio",
                balance=INITIAL_BALANCE,
                total_value=INITIAL_BALANCE
            )
            db.add(portfolio)
            db.commit()
            print(f"    [PORTFOLIO] Seeded with {INITIAL_BALANCE} {CURRENCY}")
            print(f">>> ✅ CAPITAL RESET COMPLETE <<<")
        else:
            print(">>> ❌ FAILED: User not created")
            
    except Exception as e:
        print(f">>> ❌ ERROR: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    reset_capital()
