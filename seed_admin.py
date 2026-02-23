import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from pythia.db.database import SessionLocal, engine, Base
from pythia.core.auth import create_user
from pythia.db.models import User
Base.metadata.create_all(bind=engine)
db = SessionLocal()
try:
    print('Checking for admin user...')
    user = db.query(User).filter(User.username == 'admin').first()
    if not user:
        print('Admin user not found. Creating...')
        create_user(db, 'admin', 'admin@nexus.com', 'admin')
        print('✅ SUCCESS: Admin user seeded (admin/admin).')
    else:
        print('ℹ️ Admin user already exists.')
except Exception as e:
    print(f'❌ ERROR Seeding Admin: {e}')
finally:
    db.close()