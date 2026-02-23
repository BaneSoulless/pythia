import sys
import os

# Inject backend path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.db.database import SessionLocal, engine, Base
from app.core.auth import create_user
from app.db.models import User

# Add verify tables exists
Base.metadata.create_all(bind=engine)

db = SessionLocal()
try:
    print("Checking for admin user...")
    user = db.query(User).filter(User.username == "admin").first()
    if not user:
        print("Admin user not found. Creating...")
        create_user(db, "admin", "admin@nexus.com", "admin")
        print("✅ SUCCESS: Admin user seeded (admin/admin).")
    else:
        print("ℹ️ Admin user already exists.")
except Exception as e:
    print(f"❌ ERROR Seeding Admin: {e}")
finally:
    db.close()
