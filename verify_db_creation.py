import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))
from pythia.core.config import settings
from pythia.db.database import engine, Base
from pythia.db.models import User
print(f'DEBUG: settings.DATABASE_URL = {settings.DATABASE_URL}')
try:
    print('Attempting to create tables...')
    Base.metadata.create_all(bind=engine)
    print('Tables created.')
    expected_path = 'backend/app.db'
    if os.path.exists(expected_path):
        print(f'SUCCESS: File found at {expected_path}')
    elif os.path.exists('app.db'):
        print(f'SUCCESS: File found at app.db (Root)')
    else:
        print('FAILURE: File NOT found at expected paths.')
        print('Backend Dir Content:', os.listdir('backend'))
except Exception as e:
    print(f'ERROR: {e}')