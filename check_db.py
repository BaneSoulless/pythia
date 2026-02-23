import sqlite3
import pandas as pd
import os
import sys

# Windows Unicode Console Fix
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')

def audit_ledger():
    db_path = "backend/app.db" # Verified from .env
    
    if not os.path.exists(db_path):
         print(f"❌ CRITICAL: Database file '{db_path}' not found.")
         return

    print(f"📂 Auditing Database: {db_path}")

    try:
        conn = sqlite3.connect(db_path)
        
        # 1. Check Users (Table: users)
        try:
            users = pd.read_sql_query("SELECT id, username, email, is_superuser FROM users", conn)
            print(f"\n👤 [USER AUDIT] Count: {len(users)}")
            print(users.to_string(index=False))
        except Exception as e:
            print(f"⚠️ User Table Error: {e}")

        # 2. Check Trades (Table: trades)
        try:
            trades = pd.read_sql_query("SELECT id, symbol, side, quantity, price, strategy_used, executed_at FROM trades ORDER BY id DESC LIMIT 5", conn)
            print(f"\n📉 [TRADE LEDGER] Recent Transactions:")
            if not trades.empty:
                print(trades.to_string(index=False))
            else:
                print("   (No trades recorded yet - Waiting for Strategy...)")
        except Exception as e:
            print(f"⚠️ Trade Table Error: {e}")

        conn.close()
    except Exception as e:
        print(f"❌ AUDIT FAILURE: {e}")

if __name__ == "__main__":
    audit_ledger()
